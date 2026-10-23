# Milestone M6 acceptance

Status: **FINAL GO - OWNER APPROVED**

Executed: 2026-10-18  
Latest controlled deployment: 2026-10-18

## Decision

The approved local M6 phase and the controlled recovery deployment both pass.
The deterministic failure drills, reconnect reconciliation, guarded replay
tooling, automated regressions, browser recovery check, Linux `amd64`
verification, and three consecutive real-service replays are complete.

The original failed deployment remains preserved as a **NO-GO** record. The
separately authorized recovery used the corrected least-privilege IAM policy
and passed all deployed acceptance requirements. On 2026-10-18, the project
owner approved Milestone M6 as a **FINAL GO** based on the successful recovery
deployment. This approval does not make a production-readiness,
high-availability, sustained-load, or model-quality claim.

## Controlled recovery deployed acceptance - PASS

The recovery run used one temporary `m7i.2xlarge` in `us-east-2` for 507
seconds. The same 50-minute automatic termination, terminate-on-shutdown,
restricted `/32` ingress, encrypted delete-on-termination storage, IMDSv2,
three-call Bedrock cap, and `$0.55` operational ceiling were active. Direct SCP
inspection remained unavailable; the owner explicitly authorized this bounded
runtime verification after that uncertainty was disclosed.

The corrected IAM policy granted only `bedrock:InvokeModel` for the exact
Haiku 4.5 inference profile and its three exact destination model resources.
It succeeded at runtime. Network-disabled injected timeout, Bedrock-error, and
reconnect drills passed with zero real provider calls, and their disposable
container was destroyed. A fresh real-Decider container then passed the
external two-connection SILENT → REACT reconnect drill with zero duplicates,
errors, or Bedrock calls.

Exactly three no-retry real-service replays completed. Each produced SILENT,
REACT, and REPLY in order, for nine messages and three successful Bedrock calls:

| Replay | SILENT latency | REACT latency | REPLY Decider latency | Bedrock latency | Tokens in/out | Result |
|---|---:|---:|---:|---:|---:|---|
| 1 | 1,229.31 ms | 1,379.21 ms | 1,500.06 ms | 978.12 ms | 159 / 32 | PASS |
| 2 | 1,235.76 ms | 1,489.97 ms | 1,512.15 ms | 999.26 ms | 159 / 29 | PASS |
| 3 | 1,243.17 ms | 1,406.05 ms | 1,516.44 ms | 906.50 ms | 159 / 29 | PASS |

Aggregate Decider p50/p95 latency was 1,406.05/1,516.44 ms. Average Bedrock
latency was 961.29 ms. There were zero runtime errors, duplicate events, silent
retries, or configuration changes. The three recorded replies were:

1. “I'm not sure—I haven't seen the API error logs or recent code changes. Have
   you checked if the authentication token might be expired?”
2. “I'm not sure—I haven't seen the API error logs. Have you checked if the
   authentication token is expired or missing?”
3. The same response as replay 2.

Peak container cgroup memory was 13,320,359,936 bytes (12.41 GiB) under the
24-GiB limit; OOM was false. Gross estimated cost is `$0.05913`: `$0.056784`
EC2, `$0.000617` gp3, `$0.000704` public IPv4, and `$0.001020` Bedrock. The AWS
bill remains authoritative after usage settles. Including the preserved first
deployment estimate, cumulative M6 controlled-deployment cost is approximately
`$0.15976`.

The instance was terminated immediately after measurement. Its volume,
security group, key pair, role, inline policy, and instance profile were
deleted. Regional checks found zero active instances, volumes, network
interfaces, Elastic IPs, NAT gateways, load balancers, RDS instances, or
account-owned snapshots. Recovery evidence root:
`data/deployment_recovery/20261018T201525Z/`.

## Controlled deployed acceptance - NO-GO

Preflight passed at full gross pricing without assuming credits. The Ohio
`m7i.2xlarge` price was $0.4032/hour, the account had a 16-vCPU quota for the
8-vCPU instance, and the Claude Haiku 4.5 inference profile was ACTIVE. The
50-minute gross estimate with contingency was $0.44976, below the approved
$0.55 ceiling.

The deployed injected timeout, Bedrock-error, and reconnect drills passed with
networking disabled and zero real provider calls. The disposable drill
container was restarted and destroyed; the real acceptance used a fresh
container. An external two-connection real-Decider reconnect drill then passed
SILENT → REACT with zero duplicates, errors, or Bedrock calls.

Replay 1 observed the intended raw/final actions:

| Action | Confidence | Decider latency | Bedrock |
|---|---:|---:|---|
| SILENT | 0.4553 | 1,364.26 ms | Not called |
| REACT | 0.2398 | 1,543.16 ms | Not called |
| REPLY | 0.3842 | 1,672.11 ms | Attempted; access denied in 69.74 ms |

The REPLY produced `AccessDeniedException`: the temporary least-privilege IAM
policy did not match the runtime inference-profile authorization. No assistant
reply, input-token count, or output-token count was returned. The application
recorded one attempted Bedrock call and one runtime error. Replays 2 and 3 were
not started, no silent retry occurred, and no thresholds, wording, model, or
policy behavior was retuned.

Peak container cgroup memory was 13,295,747,072 bytes (12.38 GiB) under the
24-GiB limit; OOM was false. The paid window was 878 seconds. Estimated gross
cost is $0.10064: $0.09834 EC2, $0.00108 gp3, $0.00122 public IPv4, and $0
estimated Bedrock because the attempt was denied before inference. The AWS bill
is authoritative after usage settles.

The instance was terminated immediately after evidence collection. The root
volume, security group, key pair, role, instance profile, and local private key
were deleted. Tagged and regional post-run inventory found zero unexpected
billable resources. Evidence root:
`data/deployment_failure/20261018T192248Z/`.

## Preserved boundaries

- Frozen configuration remains context `k=3`, REPLY `0.20`, REACT `0.04`.
- Original Decider wording, model revision, action policy, and architecture were
  not changed.
- M5 remains technically closed with model-performance **NO-GO**: 66.7%
  held-out accuracy, 66.7% unnecessary-interruption rate, unavailable held-out
  REACT recall, and the documented Bedrock-judge deviation.
- No original held-out or 105-case protected-reserve scenario was opened by
  this phase.
- The local phase used no AWS. The later controlled deployment is fully
  recorded above and has been terminated and cleaned up.
- M6 evidence is separate from evaluation `results/`.

## Implemented deliverables

- `scripts/run_m6_failure_drills.py`: deterministic timeout, Bedrock-error, and
  reconnect drills using injected test doubles.
- `web/app.js`: reconnect-time REST reconciliation plus duplicate-decision and
  duplicate-reaction protection.
- `data/demo/three_action_conversation_v1.json`: versioned public three-message replay
  fixture, separate from evaluation data.
- `scripts/demo_replay.py`: guarded WebSocket replay, transcript validation,
  realistic delays, duplicate/error checks, and credential-safe evidence.
- `scripts/run_m6_acceptance.py`: guarded, exactly-three-run deployed
  orchestrator with no silent retries and a three-call cap contract.
- `tests/test_m6_reliability.py`: failure, guardrail, duplicate, timeout,
  orchestrator, privacy, reconnect, and frozen-checksum coverage.

## Acceptance evidence

| Check | Result | Evidence |
|---|---|---|
| Deterministic local failure drills | PASS: timeout fails closed, Bedrock error creates no reply, reconnect events occur once | `scripts/run_m6_failure_drills.py`, `tests/test_m6_reliability.py` |
| Browser reconnect behavior | PASS: REST reconciliation and duplicate suppression are covered | `web/app.js`, `tests/test_m6_reliability.py` |
| Linux `amd64` verification | PASS: recorded during M6 local acceptance | Historical snapshot at commit `56f319f` |
| Deployed injected drills | PASS; zero real calls | `data/deployment_failure/20261018T192248Z/failure_drills/summary.json` |
| External real reconnect | PASS; SILENT → REACT, zero duplicates/Bedrock | `data/deployment_failure/20261018T192248Z/deployed_reconnect/summary.json` |
| Three-replay sequence | NO-GO on replay 1; replays 2-3 not started | `data/deployment_failure/20261018T192248Z/summary.json` |
| Cleanup | PASS; zero unexpected billable resources | `data/deployment_failure/20261018T192248Z/cleanup_inventory.json` |
| Recovery injected drills | PASS; network disabled, zero real calls | `data/deployment_recovery/20261018T201525Z/injected_drills/20261018T202248982675Z/summary.json` |
| Recovery external reconnect | PASS; two connections, zero duplicates/Bedrock | `data/deployment_recovery/20261018T201525Z/deployed_reconnect/summary.json` |
| Recovery three-replay sequence | PASS; 3/3 replays, exactly 3 successful Bedrock calls | `data/deployment_recovery/20261018T201525Z/real_replays/20261018T202359164678Z/summary.json` |
| Recovery cleanup | PASS; zero unexpected billable resources | `data/deployment_recovery/20261018T201525Z/cleanup_inventory.json` |

The main branch retains the complete redacted failed-deployment and successful
recovery bundles, including all three successful replay transcripts. Superseded
local-only drill output remains available in the pre-cleanup Git snapshot.

The locally verified image is Linux `amd64`, runs as non-root UID/GID 999, has no broken
Python requirements, and is identified by
`sha256:42959b6d50640568dae94bc7ce98e37ee8589444a78f7e4260a7b0f557f74266`.
Its local size is 1,910,193,780 bytes. All M6-specific tests and deterministic
drills passed with container networking disabled.

The mock replay observed SILENT, REACT, and REPLY in order with delays of
approximately 1.001, 2.002, and 2.501 seconds. It recorded three decisions,
three metrics events, one reaction, zero duplicates, zero runtime errors, and
zero real Bedrock calls. Because it used MOCK mode, it cannot satisfy the
deployed acceptance requirement.

## Safety and observability results

- Decider timeout fails closed to SILENT.
- SILENT/error paths do not call Bedrock.
- A Bedrock exception never fabricates an assistant response.
- Errors and latencies are retained in decision evidence and runtime metrics.
- Reconnect refreshes metrics and recent decisions before normal live use
  resumes.
- Decision, reaction, message, and call accounting checks reject duplicates.
- Published summaries and the redacted decision artifact omit endpoint URLs,
  credentials, account identifiers, and tokens. The original raw AWS error is
  preserved for audit and must not be shared publicly.
- Guarded real replay requires explicit real-Bedrock authorization; the
  three-run orchestrator also requires an explicit three-call cap and rejects
  localhost.

## Limitations and remaining blockers

1. The original deployed run failed and remains preserved as NO-GO evidence;
   the separately authorized recovery passed and is the basis for the owner's
   final M6 approval.
2. Direct SCP inspection was unavailable. The successful three-call runtime
   result establishes permission for this bounded run, not a permanent
   organization-policy guarantee.
3. A timed-out CPU inference thread may continue underneath the application
   timeout. Local tests prove fail-closed behavior, not cancellation. The
   disposable container must be restarted after the deployed timeout drill.
4. Reconnect reconciliation restores counters and recent decisions; it is not
   durable chat delivery and cannot recover every chat event emitted while a
   browser was offline.
5. The local replay is MOCK-only and not evidence of model quality or
   production readiness.
6. M5's model-performance NO-GO remains unchanged and must accompany any M6
   demo claim.

## Local-phase cost and resource state

- AWS/Bedrock cost for this phase: **$0**.
- AWS resources launched: **0**.
- Bedrock calls: **0**.
- Local verification containers left running: **0**.

## Final owner decision and next gate

The project owner approved M6 as a **FINAL GO** on 2026-10-18 based on the
successful controlled recovery deployment. M6 is closed. The original failed
deployment, recovery evidence, measurements, costs, IAM investigation, and
cleanup records remain preserved.

This decision authorizes no M7 implementation, production deployment, new AWS
resource, or Bedrock invocation. Each requires separate owner approval.

Owner M6 GO/NO-GO: **FINAL GO - APPROVED 2026-10-18**
