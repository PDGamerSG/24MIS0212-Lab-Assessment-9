# Assessment 9 ? Reliable portal delivery

One repository for all three questions of ISWE406P. The supplied PDF is headed Assessment VIII.

| Question | Application | Replicas | NodePort | Release strategy |
|---|---|---:|---:|---|
| 1 | lms-portal | 2 | 30081 | Versioned rolling release and rollback |
| 2 | food-portal | 3 per colour | 30082 | Blue-green validation and Service promotion |
| 3 | hospital-portal | 3 | 30083 | Versioned rolling release and rollback |

Each application contains index.html, Dockerfile, nginx.conf, deployment.yaml and service.yaml. All content is academic sample data.

## Jenkins

The Windows Jenkins job Assessment9-Portals loads the root Jenkinsfile from this repository. APP selects the portal; RELEASE supplies a version prefix; FAULTY=true intentionally builds an image whose /healthz endpoint returns HTTP 503. Normal builds test HTTP content against the Git source, validate Nginx, publish a unique Docker Hub image tag, deploy, wait for readiness and check the NodePort and serving Pods.

Credentials remain in Jenkins: dockerhub (existing Docker Hub account) and assessment9-kubeconfig (secret kubeconfig file). No credentials or kubeconfig are committed. Docker login uses standard input and an isolated per-workspace config which is removed afterward.

The pipeline polls GitHub every two minutes. Each poll detects committed source changes; use APP to build the corresponding portal. scripts/ci.py performs the Windows CI stages. To run a stage locally, set APP, RELEASE and BUILD_NUMBER before calling python scripts/ci.py build (then test, push, deploy and verify). Push requires DOCKER_USER and DOCKER_PASS supplied through Jenkins credentials.

## Deployment and failure handling

Q1 and Q3 use rolling updates with maxUnavailable=0 and readiness/liveness probes. A failed rollout runs kubectl rollout undo, verifies the exact prior image and confirms the restored NodePort page. Q2 deploys the inactive colour first and changes the production Service selector only after readiness passes. An unhealthy candidate leaves traffic on the active colour and restores or deletes the rejected candidate automatically.

A failed demonstration build is expected to be marked FAILURE in Jenkins: the Deploy stage rejects HTTP 503, Automatic Rollback succeeds, and Verify NodePort and Pods confirms recovery.

Docker Desktop uses a kind-backed Kubernetes node on this machine. Small Node.js TCP forwarders expose the real node ports at localhost:30081/30082/30083; they forward bytes to desktop-control-plane and do not serve application HTML. They have restart policy no.

## Application updates

The food portal update adds a thank-you message and restaurant rating summary. The hospital portal update adds a vaccination clinic and appointment slots. The Q3 prompt refers to a placement webpage despite specifying a hospital portal; the update is applied to the hospital scenario consistently.

Actual build results, image digests, Pod output and screenshots are saved in evidence/ and screenshots/ after verification.
