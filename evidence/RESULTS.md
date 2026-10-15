# Verified assessment results

All results below are real Jenkins executions on Docker Desktop Kubernetes. Captured after build #5 recovered each application.

| Question | Job | Automatic SCM build | Stable release | Deliberate faulty release | Recovery |
|---|---|---|---|---|---|
| 1 | Assessment9-Q1-LMS | #3 SUCCESS (SCM change) | #4 SUCCESS, `pdgamersg/assessment9-lms:v2-4` | #5 FAILURE, `pdgamersg/assessment9-lms:broken-5` | Rollback and Verify stages SUCCESS; HTTP 200 |
| 2 | Assessment9-Q2-Food | #3 SUCCESS (SCM change) | #4 SUCCESS, `pdgamersg/assessment9-food:v2-4` | #5 FAILURE, `pdgamersg/assessment9-food:broken-5` | Rollback and Verify stages SUCCESS; HTTP 200 |
| 3 | Assessment9-Q3-Hospital | #3 SUCCESS (SCM change) | #4 SUCCESS, `pdgamersg/assessment9-hospital:v2-4` | #5 FAILURE, `pdgamersg/assessment9-hospital:broken-5` | Rollback and Verify stages SUCCESS; HTTP 200 |

Build #5 is deliberately marked FAILURE because the candidate failed readiness. The subsequent Automatic Rollback and Verify NodePort and Pods stages succeeded in every job. The stable HTML hash equals the Git source.

- Q1: 2 serving Pods, NodePort 30081, exact stable image restored.
- Q2: 3 serving blue Pods, NodePort 30082; the failed green candidate was never promoted. Green was restored to its prior `v1-3` image with 3 healthy fallback Pods.
- Q3: 3 serving Pods, NodePort 30083, exact stable image restored.

Each build folder contains the original Jenkins console, archived stage output, state, verification JSON, stage metadata and run causes. Historical implementation failures in build #1 are retained honestly. Build #3 proves the automatic SCM trigger. Build #4 proves normal delivery. Build #5 proves fault rejection and recovery.

Jenkins URLs use localhost and require the local service. The public screenshots and text evidence remain viewable independently. Documentation-only commits after this capture may produce additional normal builds through SCM polling.
