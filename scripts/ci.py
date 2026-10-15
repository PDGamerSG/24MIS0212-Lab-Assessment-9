"""Windows Jenkins CI/CD with versioned images, blue-green promotion and rollback."""
import hashlib,json,os,re,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
default_app="food-portal" if "Q2" in os.environ.get("JOB_NAME","") else "hospital-portal" if "Q3" in os.environ.get("JOB_NAME","") else "lms-portal"
APP=os.environ.get("APP",default_app)
SHORT={"lms-portal":"lms","food-portal":"food","hospital-portal":"hospital"}[APP]
TESTPORT={"lms-portal":8191,"food-portal":8192,"hospital-portal":8193}[APP]
PORT={"lms-portal":30081,"food-portal":30082,"hospital-portal":30083}[APP]
REPLICAS=2 if APP=="lms-portal" else 3
FAULTY=os.environ.get("FAULTY","false").lower()=="true"
VERSION=os.environ.get("RELEASE","v1")+"-"+os.environ.get("BUILD_NUMBER","local")
IMAGE="pdgamersg/assessment9-"+SHORT+":"+VERSION
E=Path("evidence");E.mkdir(exist_ok=True)
stage=sys.argv[1];log=[]
def run(*args,check=True,capture=False):
    print("+ "+" ".join(args),flush=True);log.append("$ "+" ".join(args))
    r=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8",errors="replace")
    print(r.stdout,flush=True);log.append(r.stdout)
    if check and r.returncode:raise RuntimeError("Command failed: "+args[0])
    return r.stdout if capture else r.returncode
def kube(*args,**kw):return run("kubectl","--context","docker-desktop","-n","assessment9",*args,**kw)
def obj(*args):return json.loads(kube(*args,"-o","json",capture=True))
def state():return json.loads((E/"state.json").read_text())
def save(s):(E/"state.json").write_text(json.dumps(s,indent=2),encoding="utf-8")
def http(url):
    for i in range(20):
        try:
            with urllib.request.urlopen(url,timeout=5) as r:return r.read()
        except Exception:
            if i==19:raise
            time.sleep(1)
def forward():
    name="assessment9-"+SHORT+"-nodeport"
    exists=run("docker","ps","-a","--filter","name=^/"+name+"$","--format","{{.Names}}",capture=True).strip()
    if exists:run("docker","start",name)
    else:
        code="const net=require('net');const p=Number(process.env.NODE_PORT);net.createServer(c=>{const u=net.connect(p,'desktop-control-plane');c.pipe(u).pipe(c);c.on('error',()=>u.destroy());u.on('error',()=>c.destroy());c.on('close',()=>u.destroy());}).listen(p,'0.0.0.0');"
        run("docker","run","-d","--name",name,"--restart","no","--network","kind","-p",f"127.0.0.1:{PORT}:{PORT}","-e","NODE_PORT="+str(PORT),"node:22-alpine","node","-e",code)
def build():
    for old in E.glob("*"):
        if old.is_file():old.unlink()
    p=Path(APP)/"nginx.conf";original=p.read_text()
    try:
        if FAULTY:p.write_text(original.replace("return 200 'healthy'","return 503 'deliberate faulty release'"),encoding="utf-8")
        run("docker","build","-t",IMAGE,APP)
    finally:p.write_text(original,encoding="utf-8")
    save({"app":APP,"image":IMAGE,"version":VERSION,"faulty":FAULTY})
def test():
    name="assessment9-smoke-"+SHORT+"-"+os.environ.get("BUILD_NUMBER","local")
    try:
        run("docker","run","-d","--name",name,"--restart","no","-p",f"127.0.0.1:{TESTPORT}:80",IMAGE)
        run("docker","exec",name,"nginx","-t")
        actual=http(f"http://127.0.0.1:{TESTPORT}/")
        if actual!=(Path(APP)/"index.html").read_bytes():raise RuntimeError("HTML differs from Git source")
        log.append("PASS: HTTP 200, valid nginx config, source SHA-256 "+hashlib.sha256(actual).hexdigest())
        print(log[-1],flush=True)
        # Controlled fault injection preserves the root-page smoke test but makes
        # the readiness endpoint return 503; Kubernetes must reject this image.
        if not FAULTY:http(f"http://127.0.0.1:{TESTPORT}/healthz")
    finally:run("docker","rm","-f",name,check=False)
def push():
    r=subprocess.run(["docker","login","--username",os.environ["DOCKER_USER"],"--password-stdin"],input=os.environ["DOCKER_PASS"]+"\n",text=True,capture_output=True)
    print("Docker Hub login: "+("successful" if r.returncode==0 else "failed"),flush=True)
    if r.returncode:raise RuntimeError("Docker Hub authentication failed")
    run("docker","push",IMAGE)
    if not FAULTY:
        alias=IMAGE.rsplit(":",1)[0]+":"+os.environ.get("RELEASE","v2")
        run("docker","tag",IMAGE,alias)
        run("docker","push",alias)
def deploy():
    s=state();run("kubectl","--context","docker-desktop","apply","-f","k8s/namespace.yaml")
    raw_service=kube("get","service",APP,"-o","json",check=False,capture=True)
    try:svc=json.loads(raw_service)
    except Exception:
        kube("apply","-f",str(Path(APP)/"service.yaml"))
        svc=obj("get","service",APP)
    if APP=="food-portal":
        active=svc["spec"]["selector"].get("slot")
        candidate="green" if active=="blue" else "blue";name=APP+"-"+candidate
        s.update(previous_slot=active,candidate_slot=candidate,deployment=name)
        raw=kube("get","deployment",name,"-o","json",check=False,capture=True)
        try:s["candidate_previous_image"]=json.loads(raw)["spec"]["template"]["spec"]["containers"][0]["image"]
        except Exception:s["candidate_previous_image"]=None
        text=(Path(APP)/"deployment.yaml").read_text().replace("name: food-portal-blue","name: "+name).replace("slot: blue","slot: "+candidate)
    else:
        name=APP
        raw_deployment=kube("get","deployment",name,"-o","json",check=False,capture=True)
        try:previous_image=json.loads(raw_deployment)["spec"]["template"]["spec"]["containers"][0]["image"]
        except Exception:previous_image=None
        s.update(deployment=name,previous_image=previous_image)
        text=(Path(APP)/"deployment.yaml").read_text()
    text=re.sub(r"image: \S+","image: "+IMAGE,text)
    (E/"candidate.yaml").write_text(text,encoding="utf-8");save(s)
    kube("apply","-f",str(E/"candidate.yaml"))
    result=kube("rollout","status","deployment/"+name,"--timeout=75s",check=False)
    kube("get","pods","-l","app="+APP,"-o","wide")
    if result:raise RuntimeError("Candidate failed readiness; automatic rollback required")
    if APP=="food-portal":
        kube("patch","service",APP,"--type=merge","-p",json.dumps({"spec":{"selector":{"app":APP,"slot":candidate}}}))
        log.append("BLUE-GREEN PROMOTION: healthy "+candidate+" receives production traffic")
        kube("delete","deployment","food-portal","--ignore-not-found=true")
    forward()
def rollback():
    s=state();name=s["deployment"]
    if APP=="food-portal":
        active=obj("get","service",APP)["spec"]["selector"].get("slot")
        if active!=s["previous_slot"]:raise RuntimeError("Unexpected Service selector change")
        log.append("PASS: production traffic stayed on stable "+str(active))
        old=s.get("candidate_previous_image")
        if old:
            kube("set","image","deployment/"+name,APP+"="+old)
            kube("rollout","status","deployment/"+name,"--timeout=120s")
        else:kube("delete","deployment",name)
    else:
        kube("rollout","undo","deployment/"+name)
        kube("rollout","status","deployment/"+name,"--timeout=120s")
        restored=obj("get","deployment",name)["spec"]["template"]["spec"]["containers"][0]["image"]
        if restored!=s["previous_image"]:raise RuntimeError("Wrong rollback image")
        log.append("PASS: restored exact stable image "+restored)
    log.append("PASS: previous stable release restored automatically")
    print("\n".join(log[-2:]),flush=True)
def verify():
    selector=obj("get","service",APP)["spec"]["selector"]
    labels=",".join(k+"="+v for k,v in selector.items())
    pods=obj("get","pods","-l",labels)["items"]
    active=[p for p in pods if not p["metadata"].get("deletionTimestamp")]
    if len(active)!=REPLICAS:raise RuntimeError("Incorrect serving replica count")
    for p in active:
        if p["status"]["phase"]!="Running" or not all(c.get("ready") for c in p["status"]["containerStatuses"]):raise RuntimeError("Pod not Running/Ready")
    kube("get","deployments");kube("get","pods","-l",labels,"-o","wide");kube("get","service",APP,"-o","wide")
    forward();data=http("http://127.0.0.1:"+str(PORT))
    if data!=(Path(APP)/"index.html").read_bytes():raise RuntimeError("NodePort differs from stable source")
    http("http://127.0.0.1:"+str(PORT)+"/healthz")
    message=f"PASS: NodePort {PORT} HTTP 200; {REPLICAS} Running/Ready serving Pods; HTML matches Git source."
    print(message,flush=True);log.append(message)
    (E/"verification.json").write_text(json.dumps({"url":f"http://localhost:{PORT}","replicas":REPLICAS,"http_status":200,"sha256":hashlib.sha256(data).hexdigest(),"candidate_image":state()["image"],"faulty_candidate_rejected":FAULTY},indent=2))
def cleanup():
    p=os.environ.get("DOCKER_CONFIG")
    if p and Path(p).is_dir() and Path(p).name==".docker-assessment9":shutil.rmtree(p)
try:globals()[stage]()
finally:(E/(stage+".txt")).write_text("\n".join(log),encoding="utf-8")
