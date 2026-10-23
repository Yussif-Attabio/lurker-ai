# Milestone M6 implementation plan

Status: **DEPLOYED ACCEPTANCE RUN NO-GO - NO RETRY AUTHORIZED**

Prepared: 2026-10-18

## 1. Objective and source requirement

M6 is the reliability-and-demo milestone. The original build specification
requires:

1. failure drills for a Decider timeout, a Bedrock error, and WebSocket
   reconnect;
2. `demo_replay.py`, which sends a scripted conversation through the real
   pipeline with realistic delays; and
3. three consecutive clean replays on the deployed instance for acceptance.

M6 is not a second model evaluation and is not a production-readiness exercise.
It demonstrates that the existing application fails safely, reconnects, and can
reproduce a short real demo on the already proven single-instance architecture.

## 2. Preserved M5 boundary

M5 remains technically complete with a documented model-performance NO-GO and
Bedrock-baseline deviation. M6 must preserve all of the following:

- context `k=3`;
- REPLY threshold `0.20`;
- REACT threshold `0.04`;
- model `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610` at revision
  `216d1ccb46a9e9b036eb9187b248db98480f77d4`;
- original decision wording, action policy, and architecture;
- the original held-out predictions, metrics, NO-GO decision, and published
  closure artifact;
- the 105 protected reserve scenarios and original held-out scenarios remain
  unopened and unused;
- no M6 artifact is written under `results/`; M6 runtime evidence goes under
  `data/deployment_failure/`;
- no accuracy, production-readiness, availability, or generalization claim is
  inferred from a successful demo replay.

The M6 acceptance report must repeat the M5 limitations: 66.7% held-out
accuracy, 66.7% unnecessary-interruption rate, unavailable held-out REACT
recall, and the missing Bedrock judge baseline.

## 3. Required deliverables

### D1. Reliability drill runner

Add `scripts/run_m6_failure_drills.py` with three explicit, independently
reportable drills:

- **Decider timeout:** inject a deterministic timeout result at the adapter
  boundary; verify the final action is SILENT, no Bedrock call occurs, the error
  is persisted, and the service remains responsive.
- **Bedrock error:** force a REPLY decision and inject a deterministic failing
  Bedrock client/replier; verify no fabricated Lurker reply is emitted, the
  failure and measured latency are persisted, and subsequent requests still
  work.
- **WebSocket reconnect:** connect, exchange an event, close the socket,
  reconnect, reconcile counters/recent decisions, send another message, and
  verify the new live events arrive exactly once.

Faults must be injected through the existing dependency-injection seams in
`create_app`; no public fault endpoint, production backdoor, hidden query
parameter, or AWS failure is permitted. The drill output must state that the
fault was injected and that it is not evidence of an actual AWS outage.

### D2. Reconnect reconciliation

Retain the existing bounded exponential WebSocket reconnect behavior. On a
successful reconnect, refresh `/api/metrics` and `/api/decisions` so the UI can
recover state that may have been emitted while disconnected. Do not change the
one-room architecture or add durable infrastructure.

### D3. Real demo replay client

Add `scripts/demo_replay.py` as a non-interactive WebSocket client that:

- verifies `/health` reports `decider_mode=real` and `model_ready=true`;
- optionally calls the existing reset endpoint before each full replay;
- replays a versioned JSON conversation with delays recorded in the script;
- defaults to realistic delays between 1 and 3 seconds;
- records every outbound message and inbound chat, reaction, decision, metrics,
  connection, and error event with timestamps;
- checks one decision and one metrics update per user message;
- verifies that only final REPLY actions can produce Bedrock calls;
- rejects MOCK events and incomplete transcripts;
- saves a transcript and machine-readable summary without credentials, AWS
  account identifiers, or access tokens; and
- exits nonzero on any missing event, unexpected action, runtime error, duplicate
  event, timeout, or accounting mismatch.

The initial replay conversation should reuse the three non-held-out messages
already proven in M2:

1. routine plan update intended to exercise SILENT;
2. noteworthy celebration intended to exercise REACT; and
3. direct unresolved API question intended to exercise REPLY.

The exact expected actions are assertions, not labels used to tune the model.
If the frozen model produces a different action, preserve the failure and do
not adjust thresholds or wording.

### D4. Versioned replay fixture

Add `data/demo/three_action_conversation_v1.json` containing only the public demo messages,
sender names, stable step IDs, expected actions, and delay values. It must not
contain any M5 held-out or protected-reserve content.

### D5. M6 acceptance orchestrator

Add `scripts/run_m6_acceptance.py` to run exactly three sequential replays and
create a single manifest. Once the acceptance sequence begins, there are no
silent retries. Any failed replay makes the run NO-GO; another sequence requires
new owner authorization.

The orchestrator must enforce:

- exactly three complete replays;
- exactly three user messages per replay;
- SILENT, REACT, and REPLY each observed once per replay;
- exactly one Bedrock call per replay and three total;
- zero errors and zero mock decisions;
- recorded Decider and Bedrock latency/token usage;
- realistic message delays actually observed;
- full action/accounting consistency; and
- a bounded call budget of three Bedrock invocations.

### D6. Evidence bundle

Write new evidence only to:

```text
data/deployment_failure/<timestamp>/
  run_manifest.json
  failure_drills/
    decider_timeout.json
    bedrock_error.json
    websocket_reconnect.json
  replay_01/
    transcript.json
    summary.json
  replay_02/
    transcript.json
    summary.json
  replay_03/
    transcript.json
    summary.json
  deployment_measurements.json
  cost_summary.json
  cleanup_inventory.json
  summary.json
```

Every displayed number must trace to one of these artifacts. Preserve failed
runs in a separate timestamped directory; never overwrite them.

### D7. Documentation

Prepare, but do not approve in advance:

- `RELIABILITY_ACCEPTANCE.md` with checklist, evidence links, costs, limitations, and
  final owner-decision placeholder;
- an additive `NOTES.md` entry after real execution;
- concise run instructions in `README.md` only after the commands have passed
  from a clean environment.

M7 submission documents are out of scope for M6 implementation.

## 4. Implementation phases

### Phase A - local reliability implementation (free)

1. Add deterministic fault doubles and the failure-drill runner.
2. Add reconnect reconciliation and browser tests.
3. Add the versioned demo fixture and replay client.
4. Add strict transcript and summary validation.
5. Add the three-run acceptance orchestrator with no-retry behavior.
6. Confirm the M5 published artifact and frozen configuration are unchanged.

Estimated effort: 4-6 engineering hours.

### Phase B - local and container verification (free)

1. Run focused reliability tests.
2. Run the complete offline suite; pytest must never call the real Decider or
   Bedrock.
3. Run the drills against a local injected FastAPI instance.
4. Run a safe MOCK replay only to validate the client protocol, while clearly
   marking it non-acceptance evidence.
5. Rebuild `linux/amd64` and run the same checks inside the image.
6. Verify the container still runs as non-root and respects its memory limit.

Estimated effort: 2-3 engineering hours.

### Phase C - deployment preflight (read-only until approval)

After separate owner authorization:

1. verify AWS identity without recording account identifiers;
2. verify region `us-east-2`, the `m7i.2xlarge` offering, and at least eight
   available On-Demand vCPUs;
3. verify the Claude Haiku 4.5 inference profile is active;
4. recheck current EC2, EBS, public IPv4, and Bedrock pricing;
5. confirm a 50-minute automatic termination timer and terminate-on-shutdown;
6. confirm the `/32` network restriction and least-privilege instance role;
7. set `BEDROCK_MAX_CALLS=3` and restrict Bedrock to the one known REPLY prompt;
8. stop before launch if any authentication, quota, model-access, security, or
   spending check fails.

Estimated effort: 30-45 minutes.

### Phase D - controlled deployed acceptance (paid, separately authorized)

Reuse the proven M3 shape only:

- one On-Demand `m7i.2xlarge` in `us-east-2`;
- one encrypted 40 GiB gp3 root volume, delete on termination;
- one temporary security group restricted to the tester's current IPv4 `/32`;
- one temporary least-privilege role/instance profile;
- no load balancer, NAT gateway, Elastic IP, database, ECR repository, GPU, or
  permanent storage.

Run order:

1. launch the container and verify external `/health`;
2. run all three injected failure drills inside the deployed image, with zero
   real Bedrock calls;
3. run the external WebSocket reconnect drill;
4. reset runtime state;
5. run exactly three clean real replays consecutively;
6. collect latency, token, memory, transcript, and cost evidence;
7. terminate immediately;
8. remove temporary security, IAM, key, volume, and instance resources; and
9. perform a read-only zero-resource inventory check.

Estimated paid window: 20-40 minutes; hard stop at 50 minutes.

### Phase E - acceptance review (free)

1. Validate the evidence bundle and raw-count consistency.
2. Confirm frozen M5 checksums/status were not changed.
3. Update `RELIABILITY_ACCEPTANCE.md` and `NOTES.md` with real outputs only.
4. Present the pass/fail result and limitations for owner GO/NO-GO.
5. Do not mark M6 complete until the owner approves the evidence.

Estimated effort: 1-2 engineering hours.

## 5. Acceptance criteria

M6 is a GO only if every item below passes.

### Failure drills

- Decider timeout returns final SILENT, records `timeout`, invokes Bedrock zero
  times, and does not crash the API.
- Bedrock failure emits no fabricated agent chat, records `bedrock_error`,
  preserves the attempted-call accounting, and does not crash the API.
- WebSocket reconnect succeeds within the bounded retry window, reconciles REST
  state, and receives the next live message/decision/metrics events exactly once.
- Drill artifacts clearly distinguish injected faults from real service faults.

### Replay client

- The replay uses the real deployed Decider and real WebSocket pipeline.
- All delays fall within the versioned fixture's permitted range.
- Every outbound message has one corresponding decision and metrics update.
- Each replay observes one SILENT, one REACT, and one REPLY.
- SILENT and REACT make no Bedrock calls; REPLY makes exactly one.
- The Bedrock response is nonempty and its tokens/latency are recorded.
- No errors, mock decisions, duplicate events, or missing events occur.

### Deployed acceptance

- `/health` is externally reachable and reports real/model-ready.
- Three and only three consecutive acceptance replays pass.
- Total replay counts are nine user messages, three SILENT, three REACT, three
  REPLY, and three Bedrock calls.
- Decider p50/p95, Bedrock latency/tokens, peak container memory, instance type,
  image identifier, and total runtime are recorded from the deployed host.
- The application remains responsive after the failure drills and all replays.
- The instance terminates and the cleanup inventory shows zero unexpected
  billable resources.
- The complete offline regression suite and browser reconnect acceptance pass.
- M5 evidence/configuration remains unchanged and no protected data was opened.

Passing M6 proves controlled replay and fail-safe behavior on one temporary
instance. It does not prove high availability, production security, sustained
load, concurrency, disaster recovery, or model quality.

## 6. Testing strategy

### Unit tests

- adapter timeout normalization;
- error-to-SILENT policy and zero-Bedrock invariant;
- Bedrock exception normalization and invocation accounting;
- transcript completeness, ordering, duplicate detection, and timeout handling;
- three-run orchestrator count/call-budget enforcement;
- M5 path/config guardrails.

### Integration tests

- FastAPI/WebSocket with injected timeout adapter;
- FastAPI/WebSocket with forced REPLY and failing replier;
- socket close/reconnect plus REST reconciliation;
- full replay protocol in MOCK mode with evidence explicitly barred from final
  acceptance;
- reset rotation without deletion of earlier logs.

### Browser acceptance

- connection indicator moves online -> offline -> reconnecting -> online;
- composer is disabled while offline and restored on reconnect;
- counters and recent decisions reconcile after reconnect;
- no duplicate chat, decision, or reaction appears;
- zero console errors at the supported desktop viewport.

### Container and deployed tests

- `linux/amd64` build and health check;
- full offline tests inside the image;
- deterministic failure drills inside the deployed image;
- external reconnect drill;
- exactly three real acceptance replays.

Pytest remains entirely offline. Real Decider and Bedrock work is performed only
by separately authorized acceptance scripts, never by the test suite.

## 7. Dependencies

### Existing software

- Python 3.12 and the current pinned requirements;
- FastAPI/uvicorn, `websockets`, `httpx`, boto3, pytest;
- the existing Decider adapter, policy, pipeline, metrics store, and API;
- Docker Desktop/buildx for `linux/amd64` verification;
- AWS CLI for read-only preflight and controlled resource cleanup.

No new third-party package is expected.

### AWS and runtime

- Region: `us-east-2`;
- EC2: one temporary `m7i.2xlarge`, 8 vCPUs and 32 GiB;
- storage: 40 GiB encrypted gp3;
- Bedrock inference profile:
  `us.anthropic.claude-haiku-4-5-20251001-v1:0`;
- instance IAM permission scoped to the approved inference profile/model ARNs;
- current IP allowlisted temporarily for port 8000 and administrative access;
- the previously measured 12.35 GiB container peak fits the 32 GiB instance.

### Human approvals

Separate explicit approvals are required for:

1. M6 implementation;
2. the maximum deployment duration and spend;
3. up to three real Bedrock reply calls; and
4. final M6 GO/NO-GO after evidence review.

The owner approved and completed item 1 for local/offline work only. Items 2-4
remain unapproved.

## 8. Expected costs

Local implementation, tests, container checks, and injected failure drills cost
**$0** in AWS charges.

The controlled acceptance estimate reuses the verified M3 rates and must be
rechecked immediately before launch:

| Item | Planning estimate |
|---|---:|
| `m7i.2xlarge` On-Demand | $0.4032/hour; about $0.134-$0.269 for 20-40 minutes |
| 40 GiB gp3 | about $0.0044 for one hour at $0.08/GiB-month |
| One public IPv4 | $0.005/hour |
| Three Claude Haiku 4.5 replies | expected about $0.0011 from prior 159-input/32-output-token usage; budget below $0.01 |
| Data transfer | expected negligible for control traffic; record actual billing later |
| Expected 20-40 minute total | approximately $0.14-$0.28 plus tax/rounding |
| Proposed hard authorization cap | **$0.55 total and 50 minutes** |

No free-tier credit is assumed. The AWS bill is authoritative. Official pricing
references to recheck are:

- `https://aws.amazon.com/ec2/pricing/on-demand/`
- `https://aws.amazon.com/ebs/pricing/`
- `https://aws.amazon.com/vpc/pricing/`
- `https://aws.amazon.com/bedrock/pricing/`

## 9. Risks and mitigations

| Risk | Impact | Mitigation / stop rule |
|---|---|---|
| Frozen model chooses a different demo action | Replay fails | Use only the previously proven M2 conversation; do not retune or edit thresholds after a failure; preserve NO-GO evidence. |
| Decider timeout leaves underlying CPU inference running | Later work may queue or memory may remain occupied | Demonstrate fail-closed behavior only; record this limitation, keep a hard process timeout, and restart the disposable container after the timeout drill before clean replays. Do not claim cancellation guarantees. |
| Bedrock quota/authentication failure | REPLY replay cannot pass | Preflight once; stop immediately without retries or architecture changes. |
| Bedrock error accounting could be misunderstood | Metrics may count an attempted call without a reply | Record `bedrock_called`, emitted-chat count, error, latency, and token fields separately. |
| Reconnect misses events emitted while offline | UI state becomes stale | Reconcile `/api/metrics` and `/api/decisions` after reconnect; do not claim durable delivery. |
| Three successful replays could be presented as model-quality evidence | Misleading submission | Keep M5 NO-GO beside M6 results and describe M6 as reliability/demo evidence only. |
| Public test endpoint exposure | Security/cost risk | `/32` allowlist, no public fault controls, least-privilege IAM, 50-minute auto-termination. |
| Instance or volume survives the run | Unexpected charges | Terminate immediately, delete temporary resources, run zero-resource inventory, and retain cleanup evidence. |
| Acceptance retries become cherry-picking | Unreliable evidence | Exactly one three-replay sequence per authorization; any failure is preserved and reported. |
| Deadline pressure | Incomplete evidence or rushed claims | Keep M6 limited to the spec; defer submission prose and video work to M7. |

## 10. Contribution to the hackathon submission

M6 supplies the reproducible technical proof needed by M7:

- a real deployed demo sequence that can become the under-three-minute video
  shot order;
- real transcript, latency, token, call-avoidance, and cost numbers for the
  Builder Center article and README;
- visible proof that SILENT and REACT avoid Bedrock while REPLY uses it;
- evidence that timeout and provider failures fail safely and are observable;
- evidence that the live UI reconnects without inventing state; and
- an honest narrative: the reusable gate and deployment work, while the M5
  model-quality evaluation remains NO-GO and production readiness is not
  claimed.

M6 does not itself create `BUILDER_CENTER_ARTICLE.md`, `DEMO_SCRIPT.md`, or the
final submission README changes; those are explicit M7 deliverables.

## 11. Decision gate before deployed acceptance

The local/offline implementation and checks are complete; see
`RELIABILITY_ACCEPTANCE.md`. No deployed work begins until the project owner separately
approves the duration, spend, real Decider use, and three Bedrock calls. That
preflight must show the exact image identifier, test results, replay fixture,
security controls, current prices, call budget, and cleanup procedure before
requesting deployment authorization.
