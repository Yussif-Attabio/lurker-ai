# Verified implementation notes

Verified on 2026-10-15 against the official `strands-labs/strands-decider` main branch.

## Decider API facts

- Install the current official source with `pip install "strands-decider @ git+https://github.com/strands-labs/strands-decider.git"`. The published package also supports `pip install strands-decider`; the source install is used here so the project follows the current model and API documentation.
- Load once with `strands_decider.infer.load_engine(checkpoint, device="cpu" | "mps" | "mlx" | "cuda")`.
- Call `engine.ask(state, {"action": ChoiceQuestion(...)})`. A structured state is supported. A choice question is structured as `{"type": "choice", "instructions": ..., "criteria": {option: description_or_null}}`.
- The response is a `SystemOneResponse`; `response.answers["action"]` is a `ChoiceAnswer` containing `choice`, `probabilities`, and `confidence`. Choice confidence is derived as `(N * p_max - 1) / (N - 1)`.
- The official local-server alternative is `strands-decider serve <checkpoint> --port 8000`, then `POST /v1/systemone` with the same structured request.

## Strands integration fact

The official example uses `strands.interventions.InterventionHandler.before_tool_call`. The handler returns `Guide(feedback=...)` to send the agent back for correction or `Proceed()` to allow the tool call. `decision_pattern/strands_hook.py` will use that documented seam in its milestone.

## Hardware fact and preliminary deployment choice

- The reference 2B model has about 1.9 billion parameters and serves on Apple silicon or CPU. The official docs record 115 ms median per question on an RTX 3090 for an earlier same-size reference model and warn that CPU is much slower.
- The current Qwen3.5 2B model downloads about 4.5 GB of base weights in addition to its checkpoint artifacts. Activations require additional memory.
- Preliminary AWS choice: a single GPU EC2 instance with at least 24 GiB GPU memory (for example, a compatible G6-family instance) provides safe headroom for the 2B checkpoint and app. This is not a measured project result; the exact instance and region must be confirmed against current AWS availability and pricing before deployment.

## Sources

- https://github.com/strands-labs/strands-decider
- https://github.com/strands-labs/strands-decider/blob/main/docs/inference.md
- https://github.com/strands-labs/strands-decider/tree/main/examples/strands
- https://huggingface.co/StrandsAgents/strands-decider-2B-qwen3.5-v1-2610

## M0 real outputs

### Local Decider attempt - 2026-10-15

Environment: Apple silicon Mac with 16 GB unified memory, Python 3.12.14. The official source was installed at commit `6039cf8b64c6074e75804000c07ac3d4cce795f7`; the current checkpoint and base files were downloaded from Hugging Face.

- `--device mps`: the process was terminated during model initialization before a decision or Python exception was produced.
- `--device mlx`: after installing the documented MLX dependencies, the process was again terminated during base-model initialization before a decision was produced.

These two initialization failures are environment/backend results, not Decider
quality results. A GPU instance was not launched.

### Five real Decider smoke tests - PASS - 2026-10-15

Command: `PYTHONUNBUFFERED=1 PYTHONPATH=. .venv/bin/python scripts/smoke_decider.py --device cpu`

Checkpoint: `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610`

| Case | Choice | Confidence | Latency (ms) | Error |
|---|---:|---:|---:|---:|
| question | REPLY | 0.5192 | 2096.64 | none |
| joke | SILENT | 0.2084 | 483.81 | none |
| plan | SILENT | 0.3592 | 463.40 | none |
| already_answered | SILENT | 0.3771 | 587.17 | none |
| ambiguous | SILENT | 0.4356 | 458.94 | none |

The official model loaded once and returned a real structured choice for all five
cases. This establishes that M0 does not require a GPU instance; the CPU backend
is sufficient for development smoke testing on this Mac. These smoke results do
not establish evaluation quality or production latency.

### Real Amazon Bedrock smoke test - PASS

- AWS Region: `us-east-2`
- Model ID: `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- Response: "Hi! The Bedrock smoke test worked."
- Latency: approximately 0.93 seconds
- Input tokens: 36
- Output tokens: 11
- Status: PASS

This was one verified real Converse invocation. The values above are the observed
result supplied from that run, not placeholders or fabricated metrics.

### Offline preparation and AWS identity preflight - 2026-10-15

- `14 passed` from the offline pytest suite after the login-session preflight update.
- The suite does not call the real Decider or Bedrock.
- The read-only AWS preflight is restricted to STS `GetCallerIdentity`; the
  response was captured without writing the account ID, ARN, or user ID.
- AWS CLI result: `aws-cli/2.38.1` installed and linked by Homebrew.
- AWS configuration result: default credential chain, Region `us-east-2`.
- STS verification result: `OK` on 2026-10-15. Identity fields were intentionally
  suppressed. Both the AWS CLI and the boto3 application credential path passed;
  `botocore[crt]` supplies login-session support. These preflight checks created
  no AWS resources and did not invoke Bedrock.
- Prepared 45 synthetic, unlabeled scenario candidates for human review. They are not evaluation ground truth and `eval/scenarios.jsonl` remains empty.

## M0 acceptance review - PASS - 2026-10-15

- Repository: initialized Git working tree.
- License: MIT license present.
- Requirements: Python dependencies declared and internally consistent.
- Decider smoke: five required real cases completed with choice, confidence, and
  latency recorded above.
- Bedrock smoke: one real Converse call completed with response, latency, and
  token usage recorded above.
- Verified API facts: official Decider install, loading, question, response, and
  Strands integration APIs recorded in this file.
- Safety boundary: offline tests do not call Decider or Bedrock; no account or
  credential identifiers are recorded.

Milestone M0 is complete. Work may proceed to M1, whose acceptance gate requires
the real tuning-split report and a human-completed `GO_NOGO.md`.

## M1 infrastructure status - 2026-10-15

- Human-approved initial criteria are recorded in `eval/criteria.yaml` and
  `GO_NOGO.md`: accuracy at least 70%, unnecessary interruption at most 20%,
  and missed help at most 25%.
- The 45 synthetic candidates have a locked, stratified 30 tuning / 15 held-out
  split. The local labeling interface hides split, category, other evaluators'
  answers, and every model prediction.
- The workflow requires three separate, complete human CSV exports before
  `eval/scenarios.jsonl` is populated. Default consensus requires unanimous
  agreement; disagreements become `AMBIGUOUS`.
- The real evaluation runner compares context k = 0, 3, and 5, refuses
  MockDecider, and locks the held-out split until an explicit M5 override.
- Exact rate metrics include raw counts, ambiguous cases are excluded from
  scored rates, and threshold selection reads tuning predictions only.
- Offline verification: `33 passed`; dependency check clean; local labeling
  page and redacted 45-scenario API responded successfully.
- This infrastructure-only stage created no human labels, Decider evaluation
  outputs, Bedrock calls, or paid AWS resources.

### M1 human labels and real tuning run - 2026-10-16

- Three complete, distinct evaluator exports were validated and merged using
  the unanimous-consensus rule.
- Agreement: 29/45 unanimous (64.44%); 16/45 ambiguous.
- Canonical split: 30 tuning and 15 held-out. No held-out prediction was made.
- Tuning consensus: 10 `REPLY`, 10 `SILENT`, 10 `AMBIGUOUS`, and no unanimous
  `REACT` cases.
- Real Decider run: 90 predictions across k = 0, 3, and 5, with zero errors.
- Evidence directory: `results/20261016T054927Z/`.
- k = 3 candidate policy: reply threshold 0.40 and react threshold 1.00.
  The react value is a conservative fallback because current scored data cannot
  identify that threshold.
- Candidate k = 3 metrics: accuracy 17/20 (85%), unnecessary interruption
  2/10 (20%), missed help 1/10 (10%), latency p50 521.69 ms, latency p95
  583.05 ms. All approved numeric criteria pass.
- k = 0 fails the interruption criterion at 3/10 (30%). k = 5 has the same
  candidate classification metrics as k = 3 but a higher measured p95 latency
  of 1369.31 ms.

At this stage, M1 remained incomplete pending owner approval of the candidate
thresholds and the final go/no-go decision. The later provisional acceptance
section records the superseding decision. The held-out split remains untouched
until M5.

### M1 REACT calibration run - 2026-10-16

- Three complete calibration evaluator exports were validated and merged with
  unanimous consensus into `eval/react_calibration_scenarios.jsonl`.
- Agreement: 11/15 unanimous (73.33%); 4/15 ambiguous.
- Unanimous calibration labels: 4 `REACT`, 7 `SILENT`, and no `REPLY`.
- The real local CPU Decider produced 45 calibration predictions across
  k = 0, 3, and 5 with zero errors. AWS and Bedrock were not invoked.
- Calibration evidence directory:
  `results/react_calibration/20261016T062854Z/`.
- Combined k = 3 evidence contains 45 scenarios, of which 31 are scored:
  17 `SILENT`, 4 `REACT`, and 10 `REPLY`; 14 are ambiguous.
- Updated candidate thresholds are reply 0.40 and react 0.05. Candidate metrics
  are accuracy 25/31 (80.6%), unnecessary interruption 2/17 (11.8%), and
  missed help 1/10 (10.0%).
- The candidate identifies only 1/4 unanimous `REACT` cases, or 25% REACT
  recall. Three human-consensus REACT cases were raw `SILENT`, which threshold
  tuning cannot change.
- Production thresholds remain `null`, the original held-out scenarios were
  not evaluated, and the original result directory was not modified.

At this stage, M1 remained pending the project owner's explicit go/no-go
decision; the later provisional acceptance section records the superseding
decision.

### M1 REACT wording improvement - 2026-10-16

- Baseline diagnosis: the phrase `SILENT if no input is needed` overlapped with
  socially valuable acknowledgment. The model therefore treated positive but
  self-contained updates as requiring no action. Of the four unanimous REACT
  examples, only `r001` was raw REACT; `r004`, `r006`, and `r007` were raw
  SILENT. Their baseline SILENT probabilities were 0.5003, 0.4136, and 0.5715.
- The shared question now uses a decision hierarchy: needed unanswered help is
  REPLY; otherwise a noteworthy social moment that benefits from a lightweight
  acknowledgment is REACT; otherwise routine, handled, or noisy cases are
  SILENT. The wording contains no scenario IDs or evaluation text.
- The model, device, action set, policy code, architecture, and production
  configuration are unchanged.
- Clean real local-Decider evidence:
  `results/react_wording/anchored_final/`. It contains 90 original-tuning and
  45 calibration predictions across k = 0, 3, and 5, with zero AWS calls.
- Combined k = 3 candidate thresholds from the fine-grained tuning-only sweep:
  reply 0.20 and react 0.04. These values are recommendations only; production
  thresholds remain `null` pending owner approval.
- Before versus after at each run's candidate thresholds: accuracy 25/31
  (80.6%) to 26/31 (83.9%); REACT precision 100% to 100%; REACT recall 1/4
  (25%) to 3/4 (75%); unnecessary interruption 2/17 (11.8%) to 3/17 (17.6%);
  missed help remains 1/10 (10%).
- Ordinary-conversation safety: false REACT choices among 17 unanimous SILENT
  cases remain 0. The additional interruption is one false REPLY, increasing
  false replies from 2 to 3. The candidate remains below the approved 20%
  interruption ceiling but has only one-case headroom.
- `r007` remains raw SILENT: its factual approval update scores SILENT 0.5411,
  REACT 0.2385, and REPLY 0.2205 despite unanimous human REACT consensus.
- Full comparison: `results/react_wording/anchored_final/comparison/`.
- Offline verification: 38 tests passed. The held-out split was not sent to the
  Decider, original baseline artifacts remain unchanged, and no paid AWS
  resources were used.

The recommendation was provisional GO for final owner review because REACT
coverage improved materially and all approved metrics passed. The project owner
subsequently approved that provisional baseline, as recorded below.

### M1 provisional acceptance - 2026-10-16

The project owner approved M1 as a **PROVISIONAL GO** for continuation to M2.
This is not production-readiness approval.

- Provisional baseline: context k = 3, reply threshold 0.20, REACT threshold
  0.04.
- `config/default.yaml` now records the approved provisional baseline.
- The prior null-threshold configuration is preserved at
  `config/default.pre_m1_provisional.yaml` for rollback.
- Original evaluation outputs, the first calibration run, rejected wording
  experiments, and the final anchored-wording evidence remain separate under
  `results/`; none were overwritten.
- Accepted limitations: 31 scored cases and 14 ambiguous cases; only four
  unanimous REACT examples; REACT recall 75%; unnecessary interruption 17.6%
  with one-case headroom; a narrow REACT-threshold separation; synthetic local
  evaluation only; no production reliability, security, or scale claim.
- The held-out dataset remains locked until M5.
- No AWS resources were launched and no Bedrock invocation was made while
  recording this acceptance.

M1 provisional acceptance is complete. Work may proceed to M2 under the
constraints above.

## M2 backend implementation - 2026-10-16

Implemented the backend specified for M2 without calling AWS or loading the real
Decider during verification:

- `src/lurker/config.py`: YAML plus environment configuration, typed validation,
  provisional thresholds, and safe non-mock startup checks.
- `src/lurker/schemas.py`: live chat, WebSocket, and decision-event contracts.
- `src/lurker/mock_decider.py`: deterministic mock-only decisions with an
  explicit `mock=True` marker.
- `src/lurker/context.py` and `src/lurker/reactor.py`: bounded one-room context
  and local deterministic emoji selection.
- `src/lurker/bedrock_replier.py`: Bedrock Runtime Converse wrapper using
  `BEDROCK_MODEL_ID` and `AWS_REGION`, with measured latency, token extraction,
  and normalized errors.
- `src/lurker/metrics.py`: append-only JSONL, in-memory events, exact counters,
  Decider p50/p95 latency, and non-destructive reset rotation.
- `src/lurker/pipeline.py`: background decide-policy-act flow. SILENT and REACT
  make no Bedrock call; REPLY calls the injected replier exactly once; errors
  fail closed or post no agent reply as appropriate.
- `src/lurker/api.py`: `/health`, `/api/metrics`, `/api/decisions`, `/api/reset`,
  `/api/eval/latest`, and `/ws`.
- `scripts/smoke_websocket.py`: guarded real-service acceptance client. It
  refuses to run without `--allow-real-bedrock`.

Verification results:

- Offline pytest: 49 passed after the final one-call safety guards.
- Dependency check: no broken requirements.
- Real uvicorn process in MOCK mode: startup PASS.
- `GET /health`: `status=ok`, `decider_mode=mock`, `model_ready=true`.
- Local WebSocket exercise: observed `SILENT`, `REACT`, and `REPLY` in order.
- Acceptance-client safety check: refused execution without explicit
  `--allow-real-bedrock` acknowledgment.
- AWS calls: 0. Paid AWS resources launched: 0. Held-out evaluation runs: 0.

At this stage, M2 remained incomplete pending the explicitly approved
real-service check. The successful acceptance evidence is recorded below.

### M2 controlled real-service acceptance - PASS - 2026-10-16

The project owner approved one controlled local acceptance run. Read-only
preflights passed before the model call:

- AWS STS identity: OK; all identity fields suppressed.
- Region: `us-east-2`.
- Inference profile:
  `us.anthropic.claude-haiku-4-5-20251001-v1:0` (`ACTIVE`).
- `/health`: `status=ok`, `decider_mode=real`, `model_ready=true`.
- Bedrock guard: maximum one call plus an exact approved-message check.

The real local CPU Decider-only preflight produced the required sequence before
Bedrock was enabled. The final WebSocket run then produced:

| Expected | Raw choice | Confidence | Final action | Decider latency (ms) | Bedrock called | Error |
|---|---|---:|---|---:|---|---|
| SILENT | SILENT | 0.4553 | SILENT | 1068.28 | no | none |
| REACT | REACT | 0.2398 | REACT | 599.78 | no | none |
| REPLY | REPLY | 0.3842 | REPLY | 688.56 | yes | none |

Real Claude Haiku 4.5 response:

> I'm not sure—I haven't seen the API error logs or recent code changes. Have
> you checked if the authentication token might be expired?

- Bedrock calls made: 1 exactly.
- Bedrock latency: 1072.45 ms.
- Bedrock input tokens: 159.
- Bedrock output tokens: 32.
- Bedrock calls avoided versus every message: 2.
- Runtime counters: messages read 3, SILENT 1, REACT 1, REPLY 1, downgraded 0,
  errors 0.
- Decider latency p50: 688.56 ms; p95: 1030.31 ms.
- SILENT and REACT events both record `bedrock_called=false`; REPLY records
  `bedrock_called=true`.
- Evidence: `data/archive/websocket_acceptance/20261016T071233Z/`.
- Paid infrastructure launched: none. EC2/GPU launched: none.
- Held-out evaluation dataset accessed or evaluated: no.

Every M2 acceptance requirement passed. M2 is complete. This is a local
milestone result, not production-readiness or deployment approval.

## M3 local deployment preparation - 2026-10-16

Reviewed the current official Strands Decider serving documentation before
selecting deployment compute. Verified facts:

- Linux CPU inference is officially supported; a GPU is not required to serve
  the Decider.
- The guide reports an approximately 1.6-second v21 ask on a Xeon CPU using
  eight threads. This is upstream planning evidence only, not a Lurker latency
  measurement.
- The Qwen3.5 2B base download is approximately 4.5 GB.
- The reference model used by this project remains
  `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610`.

Selected one `m7i.2xlarge` (8 vCPUs, 32 GiB RAM) in `us-east-2` as the
CPU-first M3 candidate. The previous `g6.2xlarge` GPU choice is retained only as
a fallback if real CPU measurements are unacceptable. The planning price is
$0.4032 per running hour for Linux On-Demand compute in Ohio and must be
rechecked before launch.

Local implementation:

- Added a Python 3.12 CPU Dockerfile with the official CPU PyTorch install,
  non-root runtime user, and a real `/health` health check.
- Pinned Strands Decider to commit
  `6039cf8b64c6074e75804000c07ac3d4cce795f7`, the revision exercised during
  M0-M2.
- Added `.dockerignore`, deployment constraints, static deployment contract
  tests, `scripts/smoke_deployed.py`, and `M3_ACCEPTANCE.md`.
- The deployed smoke script uses one stable SILENT case, makes no Bedrock call,
  and never reads the held-out evaluation data.

Limitations and gates:

- At initial preparation time Docker was unavailable and the AWS login session
  had expired. Both were subsequently resolved; the verified results below
  supersede those initial blockers.
- AWS resources created: 0. Paid infrastructure cost incurred: $0.
- M3 remains pending explicit owner approval of the capped deployment spend,
  successful AWS preflight, external `/health`, one deployed real decision, and
  immediate instance shutdown or termination.

### M3 local amd64 verification - PASS - 2026-10-16

- Docker image: `lurker-ai:m3-amd64`.
- Image ID:
  `sha256:7eecb45d2e3878d28f17c68395f078a9a9521ba5c0744e5de8ba631efe1dddb0`.
- Target/runtime architecture: Linux `amd64` / `x86_64`.
- Fully materialized image size: 1,908,564,122 bytes (Docker displays 1.91 GB).
- Runtime user: non-root UID 999 (`lurker`).
- Safe container limit: 1 GiB and 2 CPUs; observed MOCK RSS: 66.67 MiB.
- `/health`: `status=ok`, `decider_mode=mock`, `model_ready=true`.
- WebSocket actions: SILENT, REACT, and REPLY all PASS.
- Counters: 3 messages, 0 errors, 0 Bedrock calls.
- Full offline suite inside the amd64 image: 56 passed.
- Container dependency check: no broken requirements.

Read-only AWS verification passed with identity fields suppressed:

- Configured region: `us-east-2`.
- Standard On-Demand EC2 quota: 16 vCPUs; deployment needs 8.
- `m7i.2xlarge`: offered in `us-east-2`, x86-64, 8 vCPUs, 32 GiB.
- AWS Price List API: Linux On-Demand compute is $0.4032 per hour in Ohio.
- Claude Haiku 4.5 inference profile: ACTIVE.

Memory evidence:

- Docker Desktop Linux VM capacity: 7.75 GiB.
- Real pinned Decider CPU warmup on the host: PASS, peak RSS 8.46 GiB.
- Planned instance memory: 32 GiB, approximately 23.54 GiB headroom and
  3.78 times the measured peak.
- A real cross-architecture container load was intentionally not forced because
  Docker Desktop's VM memory is below the measured loader peak. Native Linux
  amd64 peak memory remains an M3 deployed-acceptance measurement.
- Evidence: `data/archive/container_verification/20261016T190727Z/summary.json`.

No AWS resources were created, no Bedrock invocation occurred, and the held-out
evaluation dataset was not accessed. M3 remains pending paid deployment approval
and the external deployed acceptance checks.

### M3 controlled AWS deployment acceptance - PASS - 2026-10-16

The project owner approved one capped deployment: one hour maximum, $0.50 EC2
compute maximum plus small ancillary charges, one `m7i.2xlarge` in `us-east-2`,
and no M4 or held-out-dataset access.

Pre-run controls passed:

- EC2 shutdown behavior: terminate.
- Independent systemd automatic shutdown timer: active, 50 minutes.
- Inbound network: TCP 22 and 8000 from the controlling Mac's current IPv4 `/32`
  only.
- Outbound network: HTTPS, VPC DNS, and Amazon Time Sync only.
- IAM: temporary instance role restricted to `bedrock:InvokeModel` for the
  approved inference profile and its destination models, constrained by the
  profile ARN; no static AWS credentials copied.
- Encrypted 40 GiB gp3 root volume with delete-on-termination.
- Container limits: 8 CPUs, 24 GiB memory/swap, all capabilities dropped, and
  no privilege escalation.

Real external acceptance result:

- `/health`: `status=ok`, `decider_mode=real`, `model_ready=true`.
- Message: `Let's meet at four tomorrow.`
- Raw/final action: `SILENT` / `SILENT`.
- Confidence: 0.4553.
- Decider latency: 1,279.03 ms.
- Bedrock calls: 0; errors: 0; OOM killed: no.
- Memory current/peak: 13,243,207,680 / 13,260,681,216 bytes (12.33 / 12.35
  GiB).
- Main-process high-water RSS: 11,881,908 KiB (11.33 GiB).
- Peak memory headroom: 11.65 GiB under the container limit and 19.65 GiB
  against instance memory.

The paid window was `2026-10-16T19:38:23Z` through
`2026-10-16T19:46:19Z` (7 minutes 56 seconds). At $0.4032/hour, estimated EC2
compute is approximately $0.0533; ancillary storage and IPv4 charges should be
well under one cent, subject to the final AWS bill. The acceptance made no
Bedrock invocation.

The instance was terminated immediately after measurement. The exact temporary
security group, key pair, IAM role/policy/profile, and local private key were
deleted. Final verification returned zero active run-scoped instances, volumes,
security groups, key pairs, Elastic IPs, NAT gateways, snapshots, IAM roles, or
instance profiles.

Evidence: `data/archive/cloud_deployment_acceptance/20261016T194448Z/`. This single-decision result is
not production-readiness, load, concurrency, high-availability, durable-storage,
or production-cost approval. The held-out dataset remains untouched and M4 has
not begun. Technical M3 acceptance passed; final M3 approval remains with the
project owner.

### M3 final owner approval - GO - 2026-10-16

The project owner approved M3 as a final GO based on the successful controlled
AWS deployment acceptance. All deployment evidence remains preserved under
`data/archive/cloud_deployment_acceptance/20261016T194448Z/` and the local amd64 verification evidence
remains under `data/archive/container_verification/20261016T190727Z/`.

The accepted limitation remains explicit: M3 proves controlled deployment
viability, not production readiness, high availability, concurrency,
autoscaling, durable storage, or sustained-load performance.

A post-approval read-only AWS check reconfirmed:

- M3 run-scoped active instances, volumes, security groups, key pairs, Elastic
  IPs, NAT gateways, IAM roles, and instance profiles: all 0.
- Account-level `us-east-2` active EC2 instances and volumes, Elastic IPs, NAT
  gateways, v2/classic load balancers, and RDS instances: all 0.
- New AWS resources launched during confirmation: 0.
- Held-out dataset access: 0.
- M4 implementation started: no.

M3 is complete. Only M4 planning is authorized at this point.

## M4 frontend implementation and acceptance - TECHNICAL PASS - 2026-10-16

The project owner authorized implementation of the approved M4 plan. Work was
completed locally in MOCK mode with no AWS resource, Bedrock call, held-out data
access, or M5 work.

Implemented:

- One-page, two-column `web/` frontend with no build step or external assets.
- Alex, Lea, and an editable third participant in one browser.
- Live chat, visually distinct Lurker replies, and reactions attached by message
  ID.
- Last decision, confidence, raw choice, latency, policy reason, exact counters,
  and newest-first decision log.
- Visible MOCK DECIDER banner driven by `/health`.
- Backend-sourced About view through `/api/about`, using the shared question,
  options, policy descriptions, thresholds, and context.
- Evaluation placeholder only; no evaluation API call or sample metrics.
- Same-origin WebSocket, bounded reconnect, connection/error states, keyboard
  sending, safe text rendering, and responsive/accessibility behavior.

Real local browser checkpoint at 1280x900:

| Sender | Input | Action | Visible effect |
|---|---|---|---|
| Alex | `Let's meet at four tomorrow.` | SILENT | decision card/log only |
| Lea | `Great news, we passed!` | REACT | 🎉 under Lea's message |
| Sam | `Can someone explain this API error?` | REPLY | distinct mock Lurker reply |

Checkpoint counters: 3 messages, SILENT 1, REACT 1, REPLY 1, Bedrock calls 0,
avoided versus every message 3. A fourth message sent with Enter verified
keyboard-only operation at the 640px zoom-equivalent layout; horizontal overflow
was false at both widths. Browser console errors: 0.

Verification at the initial M4 checkpoint:

- Initial pre-fix offline suite: 61 passed.
- Dependency check: no broken requirements.
- JavaScript syntax and unsafe/external-pattern scan: PASS.
- Linux amd64 image: `lurker-ai:m4-amd64`, image ID
  `sha256:7a139786fa86601577d340d1e8467c068b3cc843fab905199f3ec0dd049f672f`.
- Safe local mock-container frontend check: PASS; container removed.
- Required M4 cost: $0.
- Evidence: `data/archive/frontend_acceptance/20261016T213850Z/`.

M4 proves interactive local frontend viability, not production readiness,
authentication, multi-room isolation, durable history, sustained concurrency,
high availability, or failure-reconnect reliability. At this checkpoint M4 was
pending owner review; the later 76-test regression result and FINAL GO are
recorded below. The held-out split remained untouched and M5 had not begun.

## Mock question/reaction regression fix - 2026-10-16

Investigated differing mock decisions for `is 401 safe` and `is 401 safe?`.
Root cause: `MockDecider` used the literal presence of `?` as its only question
test. It also lacked shipping and celebration signals, so `We finally shipped
the project! 🎉` fell through to SILENT.

The local-only mock now detects common interrogative openings and explicit help
requests even without punctuation. It also recognizes general gratitude,
humor, achievement, and celebration signals for lightweight reactions. REPLY
still takes priority when a message is both a question and celebratory.

Regression coverage confirms punctuated and unpunctuated questions, positive
REACT cases, declarative SILENT counterexamples, and action-priority behavior.
Focused suite: 31 passed. Full offline suite: 76 passed. The pytest cache warning
was caused only by sandbox write restrictions and did not affect results.

No real Decider thresholds, model, architecture, or production policy changed.
AWS resources launched: 0. Bedrock calls: 0. Held-out dataset access: 0.

## M4 final owner approval - GO - 2026-10-16

After the mock question/reaction regression correction, the project owner
manually retested the updated frontend, confirmed that everything was working
correctly, and approved M4 as a FINAL GO.

Preserved acceptance facts:

- Original browser acceptance: SILENT, REACT, and REPLY all displayed correctly;
  the REACT emoji attached to its source message and the mock Lurker reply was
  visually distinct.
- Post-fix behavior: punctuated and unpunctuated questions are covered by the
  same mock decision rule, while the shipping celebration is recognized as a
  lightweight REACT case.
- Complete offline suite: 76 passed.
- M4 AWS resources launched: 0; Bedrock calls: 0; required cost: $0.
- Held-out dataset access during M4: 0.

M4 is complete. Its limitations remain: this is frontend/local-demo evidence,
not production readiness, authentication, durable storage, multi-room support,
high availability, sustained-load performance, or formal failure recovery.
Planning for M5 is authorized; M5 implementation and held-out execution are not
yet authorized.

## M5 local/offline implementation checkpoint - PASS - 2026-10-16

The project owner authorized M5 local/offline implementation. Work completed:

- Added strict scenario/result completeness checks and real-run manifests with
  configuration/scenario hashes and error counts.
- Added both required baseline paths. The punctuation baseline makes no model
  call. The Bedrock judge is injectable for tests, limited to at most 15 calls,
  uses temperature 0 and at most eight output tokens, records latency/tokens and
  errors, and never retries automatically.
- Added an explicit, atomic publication contract. `/api/eval/latest` now exposes
  only `results/published.json` after it validates as a complete, real,
  error-free M5 held-out artifact with k=0/3/5 and both baselines. Legacy or
  provisional result files are not exposed accidentally.
- Enabled the Evaluation tab with lazy same-origin loading, honest
  unpublished/loading/error states, primary raw-count metrics, context and
  latency comparison, baseline comparison, calibration, provenance, and clear
  synthetic-evidence limitations.
- Added guarded baseline and publication CLIs plus offline M5 contract tests.

Verification: focused suite 32 passed; complete offline suite 84 passed;
JavaScript syntax PASS. A real local-browser check confirmed the Evaluation tab
is selectable, its unpublished state is visible and contains no sample or
provisional numbers, and the browser console has zero warnings/errors. The
pytest cache warning was caused only by the sandbox write restriction and did
not affect test execution.

This checkpoint used only synthetic fixtures and temporary directories. It made
zero real Decider calls, Bedrock calls, AWS API calls, or paid-resource changes;
it did not open or evaluate held-out scenarios and did not change context k=3,
reply threshold 0.20, REACT threshold 0.04, the model, or the architecture.

M5 remains incomplete. Local real-Decider tuning, owner configuration freeze,
controlled AWS approval, deployed timing, the one-time held-out run, real
baselines, real end-to-end acceptance, browser review of published evidence,
cleanup verification, and final owner GO/NO-GO are still required.

## M5 local real-Decider tuning - 2026-10-16

The owner authorized one local tuning-only real-Decider run. It completed all
90 predictions (30 scenarios x k=0/3/5) with the model loaded once from local
cache, offline model flags enabled, and AWS metadata disabled. There were zero
initialization failures, inference errors, AWS API calls, or Bedrock calls.

At provisional reply 0.20 / REACT 0.04, every context scored 16/20 accuracy
(80.0%), 3/10 unnecessary interruptions (30.0%), and 1/10 missed help (10.0%).
Latency p50/p95 was 619.21/2,007.27 ms at k=0, 612.01/790.95 ms at k=3, and
615.78/1,068.60 ms at k=5. k=0 contains first-inference warm-up, so its p95 is
not a steady-state comparison.

The original 30 have no unanimous REACT case, so REACT precision and recall are
N/A on this subset. Ten ambiguous cases were excluded from label-dependent
rates. The preserved M1 raw predictions showed zero drift across all 90
scenario/context pairs; six policy outputs changed due only to applying the
provisional thresholds.

Process initialization took 11.67 seconds. Maximum RSS was 5.58 GiB and macOS
reported a 7.85 GiB peak memory footprint on the 16 GB Mac; no OOM or swap event
was reported by the timed process.

An offline sweep also reused the preserved, tuning-only REACT calibration
predictions. k=0/reply 0.40/REACT 0.13 reached 87.1% accuracy and 5.9%
interruption but reduced REACT recall from 75% to 50%. k=3 and k=5 at the M1
thresholds retained 83.9% accuracy, 17.6% interruption, 10.0% missed help,
100% REACT precision, and 75% recall. k=5 had no quality gain and worse tail
latency.

Recommendation pending owner review: keep k=3, reply threshold 0.20, and REACT
threshold 0.04. Production configuration was not changed or frozen. Evidence:
`results/m5_tuning/20261016T223019Z/`.

Strict lock caveat: during the approved run, the loader parsed the shared
45-row JSONL before it selected the tuning split. Zero held-out rows were sent to the model, scored,
written to results, or used for tuning, but the approved run's loader opened the
shared source. This historical limitation is preserved in the acceptance
record.

The issue was corrected without repeating the model run. The new
`eval/tuning_scenarios.jsonl` exactly matches the 30 tuning rows, ordinary
tuning runs now default to that physically separate path, and a regression test
checks the separation and content. The complete post-correction suite has 85
passing tests.

M5 is not complete. The next gate is the owner's configuration-freeze decision;
deployed work, AWS/Bedrock authorization, held-out evaluation, publication, and
final M5 GO/NO-GO remain pending.

## M5 final evaluation freeze and preflight - PASS - 2026-10-16

The owner froze k=3, REPLY 0.20, and REACT 0.04 for final M5 evaluation. The
model revision, exact decision wording, context builder, action policy, metric
definitions, ambiguous-label treatment, success gates, and source/config hashes
are preserved in `config/m5_frozen_evaluation.yaml`.

The original tuning subset remains 80.0% accurate with 30.0% unnecessary
interruptions and 10.0% missed help. The combined tuning/calibration evidence
remains 83.9% accurate with 17.6% unnecessary interruptions, 10.0% missed help,
100% REACT precision, and 75% REACT recall. The 17.6% combined value does not
supersede the original 30.0% interruption result.

Freeze preflight passed: separate tuning file 30/30 tuning rows, no shared file
open by the audited loader, four dataset-isolation tests passed, ten focused
freeze/unlock tests passed, and all 89 offline regression tests passed. The
20-file tuning tree and 14-file calibration tree matched their frozen digests;
the cached model revision and all code/config hashes also matched.

No held-out data was opened, no model was loaded, and no AWS or Bedrock call was
made during the freeze. The one-time procedure and guarded unlock utility are
prepared but unexecuted. Evidence: `M5_PREFLIGHT.md` and
`data/archive/evaluation_freeze/20261017T002835Z/preflight.json`.

M5 remains incomplete. A separate, explicit owner authorization is required
before the one-time held-out unlock/evaluation, controlled deployment, or
Bedrock baseline.

## M5 one-time held-out Decider evaluation - NO-GO - 2026-10-17

The owner authorized one local-only held-out run under authorization
`chat-20261017-one-time-m5-heldout`. Freeze preflight passed all 16 checks, the
15-row held-out input was materialized once without printing scenario text, and
the frozen real Decider produced exactly 45 predictions across k=0/3/5.

At the primary k=3 context, accuracy was 6/9 (66.7%), unnecessary interruption
was 2/3 (66.7%), and missed help was 1/6 (16.7%). Accuracy failed the >=70%
gate and unnecessary interruption failed the <=20% gate; missed help passed the
<=25% gate. REACT precision was 0/1; REACT recall is unavailable because the
held-out split has zero unanimous REACT cases. Latency p50/p95 was
598.81/682.34 ms.

k=0 scored 66.7% accuracy, 33.3% interruption, 33.3% missed help, and
583.63/1,239.53 ms p50/p95. k=5 scored 66.7%, 66.7%, 16.7%, and
612.08/1,733.60 ms respectively. The comparison contexts do not override the
frozen primary result.

Completeness and safety checks passed: 45/45 unique predictions, 15 per
context, zero errors, zero mock rows, one run only, unchanged frozen config,
no AWS infrastructure, zero Bedrock calls, no baselines, no retuning, and no
configuration changes. The process initialized in 11.54 seconds, completed in
46.03 seconds, and used a maximum external RSS of 5.53 GiB.

The pre-registered contract therefore yields a held-out NO-GO. No result was
published to the Evaluation tab, no rerun is authorized, and the raw evidence
is preserved at `results/m5_heldout/20261017T053719Z/`. A new owner-approved
plan is required before any further held-out, tuning, deployment, or Bedrock
work.

## M5 recovery candidate and labeling preparation - PASS - 2026-10-17

The project owner approved new-dataset preparation, three blind labeling
workflows, family-grouped split tooling, and development-only evaluation tools.
This approval did not authorize a new held-out evaluation, production changes,
AWS, or Bedrock.

- Created 195 new synthetic candidates in 39 five-item scenario families.
- Owner-only authoring coverage is balanced at 65 SILENT-oriented, 65
  REACT-oriented, and 65 REPLY-oriented candidates. These targets are design
  hypotheses, not human labels, and are excluded from the evaluator API/files.
- Coverage includes direct and indirect requests, answered questions, routine
  updates, conversational closure, meaningful reactions, context-dependent
  boundaries, and five semantic questions without final question marks.
- Prepared three complete blank CSVs with 195 rows each and distinct
  deterministic orders. The local UI uses separate browser storage per
  evaluator and never shows another evaluator's answers or model information.
- Implemented unanimous merging, a separate ambiguity audit, Fleiss' kappa,
  family-grouped deterministic 90-development/60-held-out splitting, an
  isolated real-local development runner, threshold review, and development
  comparison tooling. These post-label tools have not been run on project data.
- Quality audit passed: 195 unique IDs, 39 families, five cases per family,
  zero exact duplicates, zero flagged cross-family near-duplicates, blind
  public payload, three distinct blank evaluator orders, and reproducible
  generation.
- The original M5 NO-GO bundle matched every existing SHA-256 entry. No
  original held-out scenario was parsed, copied, relabeled, scored, or used in
  a regression assertion; the audit only verified raw file hashes.
- Browser verification confirmed 195 scenarios, the revised decision guide,
  separate evaluator order/progress, and disabled export before completion.
  No answer was selected during verification.
- Full offline regression suite: 96 passed.
- Real Decider predictions: 0. AWS/Bedrock calls: 0. Production configuration
  changes: 0. New held-out evaluation: 0.

The current gate is genuine independent labeling by three people. M5 remains a
NO-GO and incomplete. The existing k=3 / REPLY 0.20 / REACT 0.04 configuration
is preserved only as the recovery starting baseline.

## M5 single-evaluator recovery development - 2026-10-17

The owner authorized using the completed evaluator `a1` export alone. The file
contains 195/195 valid labels: 95 SILENT, 36 REACT, and 64 REPLY, with no blank,
duplicate, invalid, missing, or extra IDs. Its preserved SHA-256 is
`9c6cd7cad64beabb5ba6bb91d9cf0293dc534eccb7dae7059b6f3edb9bca4dfd`.

The separate single-rater workflow preserved the original three-rater guards.
Before any model prediction, it selected 18 complete families that produce an
exact 90-row development set with 30 labels per action. The other 21 families,
105 rows, remain in a locked reserve that the evaluation runner cannot open.
Family leakage is zero. No new held-out set was created, and neither the
original held-out set nor the reserve was evaluated.

The real local Decider completed 270/270 predictions at k=0/3/5 with zero
errors and no mocks. Results at the unchanged REPLY 0.20 / REACT 0.04 baseline:

| Context | Accuracy | Unnecessary interruption | Missed help | REACT precision | REACT recall | p50 / p95 |
|---|---:|---:|---:|---:|---:|---:|
| k=0 | 72.2% | 26.7% | 10.0% | 69.6% | 53.3% | 542.71 / 937.74 ms |
| k=3 | 71.1% | 30.0% | 3.3% | 70.0% | 46.7% | 581.54 / 1,100.80 ms |
| k=5 | 71.1% | 30.0% | 3.3% | 70.0% | 46.7% | 586.22 / 1,292.17 ms |

Initialization took 11.73 seconds and peak RSS was approximately 5.59 GiB.
An offline k=3 sweep checked 2,601 threshold pairs with no additional model
calls. None met all proposed recovery gates. REPLY 0.24 / REACT 0.06 improved
accuracy to 74.4% and interruption to 16.7%, but REACT recall stayed at 46.7%,
so thresholds alone do not fix the development failure. Production settings
remain unchanged.

All 98 offline tests pass. AWS/Bedrock calls: 0. Production configuration
changes: 0. Evidence:
`results/m5_recovery/single_rater/development/20261017T221429Z/`.

These results are exploratory agreement with one evaluator, not human
consensus, ambiguity analysis, held-out evidence, or final M5 acceptance. The
original M5 NO-GO remains unchanged.

## M5 development wording candidate - REJECT - 2026-10-17

The owner approved a wording-only development experiment. Baseline error review
found two opposing patterns: meaningful achievements, human-impact news,
support/adversity moments, gratitude, belonging, personal news, and shared
humor were often missed as REACT; routine positive results, self-contained
answers, reciprocal jokes, and social closure sometimes caused unnecessary
REACT or REPLY decisions.

Candidate `m5-recovery-social-value-v1` introduced an explicit priority order:
unresolved need → REPLY; meaningful social acknowledgment with no answer needed
→ REACT; otherwise → SILENT. It preserved the model ID and revision, k values,
context builder, action options, thresholds, and policy. Production wording and
`config/default.yaml` were not changed.

The real local candidate run completed 270/270 predictions with zero errors and
zero AWS/Bedrock calls. Primary k=3 results:

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Accuracy | 71.1% | 71.1% | 0.0 pp |
| Unnecessary interruption | 30.0% | 16.7% | -13.3 pp |
| Missed help | 3.3% | 3.3% | 0.0 pp |
| REACT precision | 70.0% | 66.7% | -3.3 pp |
| REACT recall | 46.7% | 33.3% | -13.3 pp |
| Latency p50 | 581.54 ms | 848.25 ms | +266.71 ms |
| Latency p95 | 1,100.80 ms | 1,605.11 ms | +504.31 ms |

The candidate repaired five unnecessary reactions and introduced no new missed
requests, but it gained two correct reactions while losing six. It also shifted
four reference-SILENT cases into REACT relative to their baseline action. The
candidate is rejected because it is quieter but materially worse at recognizing
REACT and slower. Production wording, REPLY 0.20, REACT 0.04, and policy remain
unchanged. Evidence:
`results/m5_recovery/single_rater/wording_candidates/m5-recovery-social-value-v1/20261017T223302Z/`.

Audit caveat: during this task, preservation checks performed read-only hashing
of the original held-out JSONL, including through the existing recovery audit
test. No scenario text was displayed or parsed, the file was not modified, and
the data was not used for analysis, wording, prediction, or comparison. This
still breached the requested no-access boundary. Subsequent checks excluded
that audit and the candidate runner/comparison did not open either held-out or
the 105-case reserve.

M5 remains NO-GO and incomplete.

## M5 combined three-contributor reference and concise v2 - REJECT - 2026-10-17

The owner clarified that three people contributed to the 195-scenario labeling
document, but only one final label per scenario was saved. Provenance is now
recorded accurately as `combined_three_contributor_reference`: the individual
decisions, independence, aggregation method, unanimity, group consensus, and
inter-rater agreement cannot be verified or reconstructed. Historical
single-rater artifacts were not overwritten.

The corrected workflow retained the existing 90/105 family-separated split.
The migration and runner read only the 90 development cases; the 105 reserved
cases and original M5 held-out dataset were not opened. The original M5 NO-GO
record remains unchanged.

At k=3, the original wording had 71.1% accuracy, 30.0% unnecessary
interruptions, 3.3% missed help, 70.0% REACT precision, and 46.7% REACT recall.
Its 16 missed REACT cases were 12 raw SILENT and four raw REPLY classifications;
its nine SILENT interruptions were six raw REACT and three raw REPLY choices.

Short candidate `m5-recovery-concise-boundaries-v2` completed 90/90 real local
predictions with zero errors. It reduced interruptions to 0%, but predicted no
REACT cases, reduced accuracy to 54.4%, reduced REACT recall to 0%, and raised
missed help to 36.7%. REACT precision is undefined at 0/0. p50/p95 latency was
578.22/1,519.69 ms. The candidate is rejected and was not applied.

Model architecture/revision, production wording, k=3, REPLY 0.20, REACT 0.04,
and action policy remain unchanged. AWS/Bedrock calls: 0. Full details:
`M5_RECOVERY_COMBINED_REFERENCE.md`.

Post-run safe regression suite: 101 passed, one held-out-hashing legacy audit
deselected. Frozen production/evaluation checksums matched.

## M5 finalization candidate - 2026-10-18

Further wording and threshold experiments are stopped. The original k=3 / 0.20
/ 0.04 configuration, wording, model revision, architecture, and policy remain
frozen. The original held-out result remains NO-GO at 6/9 (66.7%) accuracy,
2/3 (66.7%) unnecessary interruption, and 1/6 (16.7%) missed help. Held-out
REACT recall remains unavailable because there were zero unanimous REACT cases.

The free question-mark baseline ran locally on the same 15 held-out cases:
6/9 (66.7%) accuracy, 1/3 (33.3%) interruption, 2/6 (33.3%) missed help, zero
REACT predictions, and zero Decider/AWS/Bedrock calls. It did not alter or
rerun the original frozen Decider evaluation.

The Evaluation tab now publishes a real-evidence `PUBLISHED NO-GO` closure
candidate. It renders the original held-out metrics, marks the question-mark
baseline as complete on held-out, and shows the Bedrock judge as `Not run`.
Browser acceptance at 1280x900 passed with zero console errors. The safe
regression suite passed 104 tests; the single legacy test that hashes the
original held-out file was deselected.

Existing M2 evidence continues to prove SILENT, REACT, and REPLY through the
real WebSocket pipeline, with zero Bedrock calls for SILENT/REACT and exactly
one for REPLY. No new pipeline call is required.

Strict build-spec completion now requires only the Bedrock judge baseline. The
prepared run is capped at 15 calls, 1,000 prompt bytes
and 8 output tokens per call, with a conservative maximum inference charge of
$0.01716 at documented regional pricing. No Bedrock call was made.

M5 technical closure was approved by the project owner on 2026-10-18 as
**TECHNICALLY COMPLETE WITH DOCUMENTED PERFORMANCE NO-GO AND
BEDROCK-BASELINE DEVIATION**. The original held-out evidence remains unchanged;
model performance remains NO-GO, the strict checklist still lacks the Bedrock
judge baseline, and production readiness is not approved. No AWS resources or
Bedrock calls were used for closure. Full report: `M5_FINAL_ACCEPTANCE.md`.

## M6 local/offline implementation - PASS - 2026-10-18

The owner approved only M6's free local/offline implementation phase. The
deterministic Decider-timeout, injected Bedrock-error, and WebSocket-reconnect
drills all passed. The timeout failed closed to SILENT with zero Bedrock calls;
the Bedrock failure emitted no fabricated reply; and the socket recovered with
post-reconnect events delivered exactly once. The real-browser drill also
passed Live → Connection lost → Live recovery, restored its controls, retained
three reconciled decisions, and added one new REACT/message/reaction without a
duplicate or console error.

The protected-data-safe native suite passed 76 tests. The rebuilt Linux
`amd64` image passed the same 76 tests, plus 9/9 M6 tests and all failure drills
with networking disabled. It runs as non-root UID/GID 999, has no broken
Python dependencies, and has image ID
`sha256:42959b6d50640568dae94bc7ce98e37ee8589444a78f7e4260a7b0f557f74266`.
A realistic-delay MOCK replay passed SILENT/REACT/REPLY accounting with zero
duplicates or runtime errors, but is explicitly not M6 acceptance evidence.

AWS resources, Bedrock calls, real Decider calls, and AWS cost were all zero.
The frozen k=3 / REPLY 0.20 / REACT 0.04 configuration and all M5 evidence and
limitations remain unchanged. M6 is not complete: the required three
consecutive deployed real replays remain unapproved and unrun. Full local
record: `M6_ACCEPTANCE.md`.

## M6 controlled deployed acceptance - NO-GO - 2026-10-18

The one authorized deployment passed price/quota/model preflight and launched
one `m7i.2xlarge` under the $0.55/50-minute controls. The injected timeout,
Bedrock-error, and reconnect drills passed with networking disabled and zero
real calls. The disposable container was restarted/destroyed after the timeout
sequence. A fresh real container passed the external two-socket reconnect drill
with SILENT → REACT, zero duplicates, and zero Bedrock calls.

The exactly-three replay sequence stopped on replay 1. SILENT (0.4553,
1,364.26 ms) and REACT (0.2398, 1,543.16 ms) passed without Bedrock. REPLY
(0.3842, 1,672.11 ms) attempted Bedrock once, but the temporary IAM policy was
denied at runtime after 69.74 ms. No reply or token counts were returned. No
retry or retuning occurred; replays 2-3 were not started.

Peak cgroup memory was 13,295,747,072 bytes with OOM false. The 878-second paid
window is estimated at $0.10064 gross. The instance was terminated immediately,
and post-run inventory confirmed zero unexpected billable resources. M6 remains
NO-GO/incomplete. M5's performance NO-GO, frozen configuration, and protected
data boundary remain unchanged. Evidence: `data/deployment_failure/20261018T192248Z/`.

## M6 offline IAM recovery investigation - 2026-10-18

The preserved redacted error and read-only CloudTrail history confirmed an
identity-policy implicit denial on `bedrock:InvokeModel` for the account-scoped
Ohio inference profile. The deleted role's one Allow statement incorrectly
applied `bedrock:InferenceProfileArn` to both the profile and model resources.
AWS does not populate that condition key when it authorizes the profile
resource, so the only Allow could not match. The original policy reproduced
this result in IAM simulation as `implicitDeny` with the condition key missing.

The original role listed all three current destinations (`us-east-1`,
`us-east-2`, and `us-west-2`), had no explicit Deny or permissions boundary,
and had no observed managed-policy attachment. The account is in AWS
Organizations, but the current identity cannot inspect its parent or SCPs. The
runtime error named an identity-policy implicit denial rather than an SCP deny;
nevertheless, an Organizations administrator clearance is mandatory before a
recovery launch.

The versioned candidate policy splits the unconditional exact profile Allow
from the exact, profile-conditioned foundation-model Allow. Access Analyzer
returned zero findings; IAM simulation returned `allowed` for the profile and
all three models; and 4/4 offline least-privilege tests passed. It grants only
`bedrock:InvokeModel`, with no wildcard, streaming, model-management, or admin
access. No IAM change, EC2 launch, model invocation, protected-data access, or
charge occurred. M6 remains NO-GO. Plan: `M6_IAM_RECOVERY_PLAN.md`; evidence:
`data/iam_recovery/20261018T195306Z/`.

## M6 recovery pre-deployment preflight - NO-GO - 2026-10-18

The remaining pre-deployment checks were completed without launching EC2,
changing IAM, invoking Bedrock, or running a deployed replay. The instance is
offered in `us-east-2`; the Standard On-Demand quota is 16 vCPUs for the
8-vCPU `m7i.2xlarge`; the Haiku 4.5 profile is ACTIVE with destinations in
`us-east-1`, `us-east-2`, and `us-west-2`; and current quotas are 10 requests
and 5,000,000 tokens per minute.

Current rates remain `$0.4032/hour` for EC2, `$0.08/GB-month` for gp3,
`$0.005/hour` for public IPv4, and `$1.10/$5.50` per million Haiku input/output
tokens. The guarded 50-minute estimate remains `$0.44976`, below the `$0.55`
ceiling. The termination script passed syntax/static checks and contains one
independent 50-minute shutdown timer. Timer activation and terminate-on-
shutdown remain mandatory launch-time checks.

The corrected policy again produced zero Access Analyzer findings and simulated
`allowed` for the exact inference profile and all three exact model resources;
five targeted offline tests passed. Effective permission is not yet cleared:
this is a member account, and the current identity cannot inspect account,
parent-OU, or root SCPs. M6 therefore remains NO-GO until an Organizations
management-account administrator supplies the requested dated clearance (or a
separately approved real canary is authorized). Full report:
`M6_RECOVERY_PREFLIGHT.md`; administrator request:
`M6_SCP_CLEARANCE_REQUEST.md`; evidence:
`data/iam_recovery/20261018T200310Z/preflight.json`.

## M6 controlled recovery deployment - PASS, final owner GO pending - 2026-10-18

After the disclosed SCP-inspection uncertainty, the owner authorized one
bounded recovery deployment. One temporary `m7i.2xlarge` ran in `us-east-2`
for 507 seconds with the 50-minute auto-termination timer, terminate-on-
shutdown, controller `/32` ingress, encrypted delete-on-termination storage,
IMDSv2, a three-call Bedrock cap, and the `$0.55` ceiling confirmed.

The corrected least-privilege policy succeeded at runtime. Network-disabled
timeout, Bedrock-error, and injected reconnect drills passed with zero real
calls; the disposable container was destroyed. A fresh real container passed
the two-connection SILENT → REACT drill with zero duplicates, errors, or
Bedrock calls. Exactly three no-retry real-service replays then passed, each
producing SILENT, REACT, and REPLY. Totals: nine messages, three successful
Bedrock calls, 477 input tokens, 90 output tokens, zero runtime errors, and zero
duplicate events. Decider p50/p95 was 1,406.05/1,516.44 ms; average Bedrock
latency was 961.29 ms.

Peak cgroup memory was 13,320,359,936 bytes under the 24-GiB limit with no OOM.
Estimated gross cost was `$0.05913`, below the authorized `$0.55`. The instance
was terminated immediately and every temporary key, security group, volume,
role, policy, and instance profile was deleted. Regional inventory found zero
unexpected billable resources. Together with the preserved first deployment,
the cumulative M6 controlled-deployment estimate is approximately `$0.15976`.

The failed first deployment remains permanently preserved under
`data/deployment_failure/20261018T192248Z/`; it was not overwritten. Recovery
evidence is under `data/deployment_recovery/20261018T201525Z/`. Frozen M5
configuration and evidence were unchanged, protected evaluation data was not
accessed, and M5's model-performance NO-GO remains. M6 deployed requirements
now pass, but owner final GO, production readiness, and M7 authorization remain
pending.

## M6 final owner approval - FINAL GO - 2026-10-18

The project owner approved Milestone M6 as a **FINAL GO** based on the
successful controlled recovery deployment. M6 is technically closed. The
three successful real-service replay transcripts, raw decisions, latency and
token measurements, cost estimate, corrected least-privilege IAM evidence,
and zero-resource cleanup verification remain preserved under
`data/deployment_recovery/20261018T201525Z/` with a SHA-256 evidence
manifest.

The earlier failed deployment and its NO-GO record remain separately preserved
under `data/deployment_failure/20261018T192248Z/`; no artifact was overwritten or
reclassified. M5's model-performance NO-GO and Bedrock-judge deviation remain
unchanged. M6 FINAL GO is not production-readiness, high-availability,
sustained-load, or model-quality approval. M7 implementation, new AWS
resources, and additional Bedrock calls require separate owner approval.

## M7 local submission packaging started - 2026-10-18

The owner authorized starting M7. This is interpreted as local/offline
submission packaging only; it does not authorize AWS resources, Bedrock calls,
or external publication. The original build specification defines M7 as a
submission-facing README, article fact notes, and a sub-three-minute demo shot
list using real outputs.

The official hackathon rules were rechecked on AWS Builder Center. Qualification
requires all three external parts: a Builder Center article, a public
OSI-licensed repository with source and a reusable Strands Decider pattern, and
a public demo video under three minutes. Required tags are
`#strands-decider-2b` and `#policy`; the published deadline is October 23, 2026
at 11:59 p.m. PT.

The reusable-folder audit found the frozen typed question and policy but no
standalone guide, wrapper, minimal example, or Strands hook. The current
official Strands Decider example confirms `InterventionHandler` as the seam.
M7 adds `ChimeInGate` beside the frozen contract and a fail-closed
`before_invocation` intervention: only REPLY returns `Proceed`; SILENT and
REACT stop text generation so the host can remain quiet or render an emoji.
The frozen wording and policy file was not edited.

The local M7 package then passed 28 targeted offline tests in 2.72 seconds.
Python compilation, frontend JavaScript syntax, required-file checks, the
11-line minimal example, frozen checksum checks, and a credential/identifier
scan passed. AWS resources, real Decider calls, and Bedrock calls were all zero.
M7 is locally ready but remains open pending human publication and verification
of the Builder Center article, public MIT repository, public sub-three-minute
video, required tags, eligibility, and final submission.

## M7 public repository publication - 2026-10-18

The owner authorized publication to GitHub. A sanitized public release was
prepared with explicit ignore guards for the locked M5 held-out rows, the
105-scenario recovery reserve, evaluator source sheets, the unredacted M6 AWS
denial record, and a terminated host's historical public IP. These artifacts
remain preserved locally and were not deleted or modified.

The candidate public tree passed credential, private-key, account-identifier,
personal-path, email, AWS role-session, live-resource-ID, and non-local-IP
checks. The full offline regression suite passed 126 tests in 3.92 seconds.
The MIT-licensed repository was created as Public at
`https://github.com/Yussif-Attabio/lurker-ai`. This satisfies the repository
part of M7 only; the Builder Center article, public demo video, required tags,
eligibility confirmation, final submission, and owner final M7 GO remain
pending. No AWS resource, real Decider call, or Bedrock call was used.

## M7 automated demo preview - PASS - 2026-10-18

A guarded Playwright recorder was added with two distinct modes. Preview mode
starts an isolated MOCK server and is never submission eligible. Final mode
fails closed unless it receives explicit one-call approval, exact Bedrock
region/profile restrictions, the exact allowed REPLY prompt, the real Decider,
and the frozen k=3 / reply 0.20 / react 0.04 policy.

The corrected normal-paced preview completed in 62.04 seconds at 1440×900. It
showed SILENT, REACT, and REPLY in order, the local celebration reaction, the
reusable decision-pattern scene, and the published M5 NO-GO. Counters ended at
three messages, one action of each type, zero errors, zero Bedrock calls, and
three calls avoided. The MOCK banner and `[MOCK]` reply were intentionally
visible. The preview is therefore workflow evidence only and must not be used
as final hackathon footage.

The local video and logs remain ignored under `artifacts/demo-recordings/`.
Only the sanitized validation summary is public. No AWS resource, real Decider
call, or Bedrock call was used. Final recording and video publication remain
pending separate approval. The complete offline regression suite passed 132
tests in 4.38 seconds, and the final-mode no-approval guard passed.

## M7 public demo video publication - 2026-10-22

The owner authorized one final local real-service recording with a maximum of
one Bedrock call. The guarded capture passed on its first and only attempt with
the frozen k=3 / REPLY 0.20 / REACT 0.04 policy. It showed the expected
SILENT, REACT, and REPLY actions, made exactly one Bedrock call, avoided two,
and recorded zero errors. The preserved M5 model-performance NO-GO remained
visible.

The owner supplied an edited 1:09 MOV for publication. It decoded cleanly at
1152x720 with HEVC video and AAC audio. Representative frames contained only
the synthetic interface, recorded project evidence, reusable pattern, and
honest evaluation disclosure. YouTube processing and copyright checks passed
with no issues. The video was published as Public on 2026-10-22 at
`https://youtu.be/hmZlMHcUCZc`, with the approved title, project description,
repository and decision-pattern links, `#strands-decider-2b` and `#policy`,
and an explicit non-production-ready/model-performance NO-GO disclosure.

No AWS resource or additional Bedrock call was used for editing or publication.
The Builder Center article, entrant/eligibility confirmation, final hackathon
submission, and owner final M7 GO remain pending.
