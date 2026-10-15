# Assessment 9 - Reliable portal delivery

One repository for all three questions of ISWE406P. The supplied PDF is headed Assessment VIII.

Completed assignment: [Word document](report/DA%209.docx) and [PDF](report/DA%209.pdf), with 47 reviewed pages and 40 embedded images. Each answer includes the complete index.html source, including its embedded CSS, with proper indentation and line breaks in 10 pt Consolas. The code continues across balanced pages, and its content is verified against the application source. The cover, body typography, border and bold Question/Step headings follow the supplied DA 8 reference. Stage View is presented as the original heading followed by the successful green build rows #4, #3 and #2.

| Question | Application | Replicas | NodePort | Release strategy |
|---|---|---:|---:|---|
| 1 | lms-portal | 2 | 30081 | Versioned rolling release and rollback |
| 2 | food-portal | 3 per colour | 30082 | Blue-green validation and Service promotion |
| 3 | hospital-portal | 3 | 30083 | Versioned rolling release and rollback |

Each application contains index.html, Dockerfile, nginx.conf, deployment.yaml and service.yaml. All content is academic sample data.

## Jenkins

Three Windows Jenkins jobs load the corresponding application Jenkinsfile from this one repository:

| Job | Script path |
|---|---|
| Assessment9-Q1-LMS | lms-portal/Jenkinsfile |
| Assessment9-Q2-Food | food-portal/Jenkinsfile |
| Assessment9-Q3-Hospital | hospital-portal/Jenkinsfile |

APP selects the portal; RELEASE supplies a version prefix; FAULTY=true intentionally builds an image whose /healthz endpoint returns HTTP 503. Normal builds test HTTP content against the Git source, validate Nginx, publish a unique Docker Hub image tag, deploy, wait for readiness and check the NodePort and serving Pods. The root Jenkinsfile is also available as a generic parameterised pipeline.

Credentials remain in Jenkins: dockerhub (existing Docker Hub account) and assessment9-kubeconfig (secret kubeconfig file). No credentials or kubeconfig are committed. Docker login uses standard input and an isolated per-workspace config which is removed afterward.

Each pipeline polls GitHub every two minutes and automatically builds committed changes. Its default APP selects its own portal. scripts/ci.py performs the Windows CI stages. To run a stage locally, set APP, RELEASE and BUILD_NUMBER before calling python scripts/ci.py build (then test, push, deploy and verify). Push requires DOCKER_USER and DOCKER_PASS supplied through Jenkins credentials. Kubernetes stages need a valid kubeconfig and the docker-desktop context.

## Deployment and failure handling

Q1 and Q3 use rolling updates with maxUnavailable=0 and readiness/liveness probes. A failed rollout runs kubectl rollout undo, verifies the exact prior image and confirms the restored NodePort page. Q2 deploys the inactive colour first and changes the production Service selector only after readiness passes. An unhealthy candidate leaves traffic on the active colour and restores or deletes the rejected candidate automatically.

A failed demonstration build is expected to be marked FAILURE in Jenkins: the Deploy stage rejects HTTP 503, Automatic Rollback succeeds, and Verify NodePort and Pods confirms recovery.

Docker Desktop uses a kind-backed Kubernetes node on this machine. Small Node.js TCP forwarders expose the real node ports at localhost:30081/30082/30083; they forward bytes to desktop-control-plane and do not serve application HTML. They have restart policy no.

## Application updates

The food portal update adds a thank-you message and restaurant rating summary. The hospital portal update adds a vaccination clinic and appointment slots. The Q3 prompt refers to a placement webpage despite specifying a hospital portal; the update is applied to the hospital scenario consistently.

Actual build results, image digests, Pod output and screenshots are saved in evidence/ and screenshots/. See [verified results](evidence/RESULTS.md): build #3 was triggered automatically by SCM, #4 delivered the stable release, and #5 intentionally failed readiness and recovered successfully in all three jobs. Stage metadata, SCM causes and original archived output are retained.

## Running locally

Enable Docker Desktop Kubernetes and select its docker-desktop context. Create the namespace with `kubectl apply -f k8s/namespace.yaml`. Configure the two Jenkins credentials above, then create each Pipeline from SCM job with this repository's main branch and the script path in the table. Run each job once with FAULTY=false to establish a stable release. Source changes then trigger SCM builds automatically. Run FAULTY=true with RELEASE=broken to reproduce the rejected candidate and automatic recovery. A first-ever faulty deployment cannot roll back to a stable release that does not yet exist.

The food manifest defines blue; the pipeline creates or updates green from the same template and switches only the Service slot selector. Both colours retain three Pods; production has three serving Pods.
