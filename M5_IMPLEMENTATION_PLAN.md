# Milestone M5 implementation and final evaluation plan

Status: **LOCAL/OFFLINE IMPLEMENTATION COMPLETE - REAL EVALUATION PENDING**

## Local implementation checkpoint - 2026-10-16

The project owner authorized the local/offline implementation stage. The
evaluation guards, bounded baseline infrastructure, explicit publication
contract, Evaluation tab, and fixture-only regression tests are implemented.
The complete offline suite has 84 passing tests.

No scenario in the held-out split was opened or evaluated during this work. No
real Decider inference, Bedrock call, AWS API call, or paid resource was used.
The next step remains a separately approved local real-Decider tuning run; the
configuration freeze, deployment, Bedrock judge, and held-out unlock remain
pending.

## Objective

Complete the original build specification's full evaluation milestone without
leaking or tuning on the held-out set. M5 will compare real Strands Decider
performance at context k = 0, 3, and 5; tune thresholds using tuning-only
evidence; freeze the selected configuration before unlocking held-out data; run
one controlled held-out evaluation; compare both required baselines; exercise
the real end-to-end pipeline; and render the saved results in the Evaluation
tab.

M5 produces final evaluation evidence, not production-readiness approval. M6
still owns formal timeout, Bedrock-error, and WebSocket-reconnect drills plus
three consecutive clean deployed demo replays. M7 still owns the final article
notes, video script, and submission package.

## Fixed inputs and human-owned decisions

- Human-approved criteria remain:
  - accuracy >= 70%;
  - unnecessary-interruption rate <= 20%;
  - missed-help rate <= 25%.
- Current provisional baseline remains context k = 3, reply threshold 0.20,
  and REACT threshold 0.04.
- The real Decider model and architecture remain unchanged.
- The original split remains 30 tuning scenarios and 15 held-out scenarios.
- Ambiguous cases are listed with predictions but excluded from scored rates.
- The held-out set must not influence context, threshold, wording, code, or
  configuration choices. If it fails, record the failure; do not retune on it.
- Before any paid or held-out run, the project owner must approve:
  1. the completed offline M5 implementation;
  2. the tuning-only recommendation and frozen configuration;
  3. the Bedrock baseline model ID and maximum call budget;
  4. the controlled AWS duration and spending cap;
  5. the single held-out unlock/run.

## Specification traceability

This plan implements sections 8, 9, 11, 12 (M5), 13, 14, and the relevant
human decisions in section 15 of the original build specification:

- real Decider context comparison at k = 0, 3, and 5;
- threshold tuning that can read tuning predictions only;
- one held-out run through shared `build_state` and `apply_policy` code;
- exact metrics with raw counts, calibration, latency, low-confidence behavior,
  and separately listed ambiguous predictions;
- `always_reply_to_questions` and Bedrock judge baselines;
- final latency reported from the deployed environment with hardware recorded;
- a populated Evaluation tab driven only by `/api/eval/latest`;
- real, timestamped artifacts under `results/` with no fabricated numbers.

## Safety boundary before held-out unlock

All implementation and automated testing will use synthetic fixtures. No test,
preview, schema validation, UI work, or dry run may open the held-out rows.

Before the one approved held-out run:

1. Run the complete offline suite and dependency checks.
2. Run a fresh real-Decider tuning evaluation at k = 0, 3, and 5.
3. Tune thresholds only from tuning predictions and compare the output with the
   provisional M1 baseline.
4. Have the project owner choose and approve one context value and one threshold
   pair.
5. Freeze a configuration snapshot, decision wording, source manifest, model
   revision, and local environment/hardware record. Record the complete
   scenario-file checksum as the first operation inside the later approved
   held-out access window, before making any held-out prediction.
6. Verify that all M5 output paths are empty/new and the held-out guard refuses
   execution without an explicit one-time approval flag.
7. Obtain explicit approval for the cost cap and held-out unlock.

After unlock, held-out results are evaluation evidence only. They may not be
used to change the frozen configuration or rerun the held-out set. A rerun is
allowed only for a documented infrastructure failure that produced no usable
predictions and only after new owner approval.

## Deliverables

| Deliverable | Purpose |
|---|---|
| `scripts/run_eval.py` hardening | One auditable real-Decider runner, explicit held-out guard, deterministic output bundle, frozen-config provenance |
| `scripts/run_m5.py` or equivalent orchestrator | Sequence tuning, freeze verification, held-out run, baselines, summary generation, and refusal conditions without duplicating decision logic |
| `eval/baselines.py` completion | Batch deterministic baseline and bounded Bedrock judge with normalized output, latency, tokens, and error records |
| `eval/metrics_def.py` and `eval/reporting.py` extensions | Baseline comparison, per-action counts, all required rates, calibration, context latency, and acceptance summary |
| `web/index.html`, `web/styles.css`, `web/app.js` | Enabled Evaluation tab rendering the latest published real result only, with loading/empty/error states and raw counts beside percentages |
| `tests/test_m5_*.py` | Offline fixture-only tests for guards, metrics, baselines, publishing, UI contracts, and result provenance |
| `results/<timestamp>/` | Immutable M5 run bundle containing real outputs and frozen provenance |
| `M5_ACCEPTANCE.md` | Checklist, exact commands, observed results, cost, cleanup, limitations, and owner decision |
| `NOTES.md`, `README.md`, `GO_NOGO.md` updates | Final evidence summary and honest go/no-go status copied only from saved artifacts |

The final run bundle should contain at least:

- `results.json` - stable API/UI summary;
- `report.md` - human-readable report with raw counts;
- `decider_per_case.csv` - raw and final Decider actions for each k;
- `always_questions_per_case.csv` - deterministic weak baseline;
- `bedrock_judge_per_case.csv` - choice, latency, input/output tokens, and errors;
- `threshold_sweep.csv` and `threshold_recommendation.json` - tuning-only;
- `run_manifest.json` - timestamps, hashes, model/config, hardware, commands,
  expected/actual call counts, and mock=false;
- `config_snapshot.yaml` - frozen pre-held-out configuration;
- `end_to_end_transcript.json` - controlled real-pipeline acceptance messages;
- Evaluation-tab screenshot and browser verification summary.

## Work packages

### 1. Offline harness hardening

- Preserve the single adapter boundary: only `src/lurker/decider_adapter.py`
  imports or calls the Decider library.
- Keep `run_eval.py` on the same `build_state`, typed question/options, and
  `apply_policy` path used by the application.
- Add strict validation for duplicate IDs, missing labels, invalid consensus,
  unexpected split membership, missing thresholds, non-finite confidence or
  latency, mock adapters, partial prediction counts, and output collisions.
- Record an error row and fail the run on any Decider error; do not silently
  convert a broken evaluation into a successful report.
- Keep threshold tuning physically unable to accept held-out rows. Add tests
  proving mixed or held-out input is rejected.
- Generate a run manifest before results are published. The manifest must make
  every displayed number traceable to a saved artifact.

### 2. Tuning-only context and threshold review

- Run the real Decider locally on the Mac over the 30 tuning scenarios at
  k = 0, 3, and 5 (90 expected predictions), with no AWS resource or Bedrock
  call. This creates the recommendation before any paid deployment or held-out
  access.
- Report accuracy, unnecessary interruptions, missed help, calibration,
  low-confidence before/after behavior, error count, and p50/p95 latency for
  each k, always with raw counts.
- Reapply candidate reply/REACT thresholds to saved predictions rather than
  making extra Decider calls.
- Compare the fresh result with the M1 provisional baseline and preserve both.
- Recommend a frozen context/threshold configuration, but do not apply it until
  the project owner approves it.

### 3. Configuration freeze and held-out run

- Copy the approved configuration into the timestamped result bundle and record
  hashes for the relevant code, configuration, and model revision. At the start
  of the separately approved unlock window, record the scenario-file checksum
  without printing its contents, then proceed directly to evaluation.
- On the deployed instance, rerun the 30 tuning scenarios at k = 0, 3, and 5 to
  capture the specification-required final-environment latency and confirm the
  frozen policy. This deployment run cannot change the approved configuration.
- Run the 15 held-out scenarios once at k = 0, 3, and 5 (45 expected real
  Decider predictions), using the same frozen thresholds for every context.
- Treat the pre-registered context as the primary pass/fail result. Report the
  other two contexts for the required comparison, never as a reason to change
  the selected configuration after seeing held-out outcomes.
- List ambiguous predictions separately and exclude them from every scored
  percentage exactly as specified.
- If any primary success criterion fails, M5 is a NO-GO pending a new plan; the
  held-out evidence remains immutable.

### 4. Required baselines

- Run `always_reply_to_questions` locally on the held-out messages. It makes no
  model or AWS call and intentionally remains the punctuation-based weak
  baseline required by the specification.
- Run the Bedrock judge with the same question, options, frozen context, and
  held-out cases at the pre-registered context only. This limits the planned
  judge budget to 15 calls while providing a fair selected-configuration
  comparison.
- Use an owner-approved `BASELINE_MODEL_ID` in `us-east-2`, temperature 0, and a
  very small output-token cap. Normalize exactly one of SILENT/REACT/REPLY;
  retain invalid responses and errors as failures rather than retrying without
  authorization.
- Record per-call latency and input/output tokens. Report currency cost only if
  the owner supplies verified entries in `config/pricing.yaml`; otherwise
  report tokens and calls only.
- Compare accuracy and latency for Decider, Bedrock judge, and the weak baseline
  without claiming causation or statistical significance from the small set.

### 5. Evaluation API and frontend

- Publish one explicit final M5 `results.json`; do not let file modification
  time accidentally select an old tuning/calibration run as "latest."
- Enable the Evaluation tab and fetch `/api/eval/latest` only when opened.
- Render accuracy, unnecessary interruptions, missed help, context comparison,
  latency by k, calibration, low-confidence behavior, and baseline comparison.
- Show numerator/denominator beside every percentage, model/environment labels,
  thresholds, generated timestamp, and clear PASS/FAIL/PENDING status.
- Provide honest loading, 404/empty, malformed-result, and network-error states.
  Never embed sample metrics or calculate substitute numbers in JavaScript.
- Verify safe DOM rendering, keyboard navigation, 1280px recording layout, and
  no horizontal overflow.

### 6. Real end-to-end acceptance

- Use a short synthetic script independent of the held-out set to verify one
  SILENT, one REACT, and one REPLY through the deployed WebSocket pipeline.
- Confirm SILENT and REACT make no Bedrock call and REPLY makes exactly one
  Bedrock generation call.
- Record Decider actions/confidence/latency, Bedrock text/tokens/latency, API
  counters, WebSocket transcript, errors, and container memory.
- Open the deployed frontend, confirm the Evaluation tab exactly matches the
  published result bundle, and capture a readable screenshot.
- Do not start M6's formal failure drills or three-replay sequence during M5.

## Testing strategy

### Offline tests - zero AWS/model calls

1. Metric tests with hand-computed fixtures, including missing SILENT/REPLY
   classes, ambiguous rows, confidence-bin boundaries, downgraded cases, and
   baseline comparisons.
2. Guard tests proving MockDecider, held-out input to tuning, missing owner
   unlock, incomplete runs, duplicate IDs, and output overwrite attempts fail.
3. Baseline tests for punctuation behavior, exact option normalization, invalid
   Bedrock output, token accounting, call cap, and modeled service errors using
   injected fake clients.
4. API tests proving only the explicitly published M5 summary is returned and
   malformed/unpublished artifacts are rejected.
5. Frontend tests for raw-count rendering, all context/calibration rows,
   baseline comparison, empty/error states, accessibility, and safe text.
6. Full regression suite plus dependency and JavaScript syntax checks.

### Controlled real tests - separately approved

1. AWS identity, Region, quota, model-access, network, IAM, cost-cap, and
   automatic-termination preflight; stop immediately on any failure.
2. One real Decider warmup before timed evaluation; exclude warmup from metrics.
3. Deployed tuning confirmation for final-environment latency, using the
   already frozen configuration.
4. Single held-out Decider run.
5. Maximum 15 Bedrock judge calls plus one end-to-end generated reply; no other
   Bedrock invocations.
6. Browser verification and artifact reconciliation.
7. Immediate instance termination and read-only zero-leftover inventory check.

## Cost controls and expected cost

No cost is incurred while implementing and testing M5 offline. The real run
requires separate approval and will reuse the proven single `m7i.2xlarge` in
`us-east-2`, with the M3 controls:

- one On-Demand instance only;
- 60-minute hard maximum and automatic termination, with a target runtime of
  15 minutes or less;
- proposed EC2 compute cap: $0.50, plus explicitly approved small encrypted
  EBS and public-IPv4 charges;
- no load balancer, NAT gateway, Elastic IP, database, GPU, ECR, or persistent
  infrastructure;
- least-privilege instance role restricted to the approved Bedrock inference
  profile/model ARNs;
- maximum 15 Bedrock judge calls and one end-to-end reply call;
- stop on authentication, quota, model-access, health, memory, or manifest
  mismatch before unlocking held-out data.

Using the M3 verified planning rate of $0.4032/hour, a 15-minute EC2 window
would be about $0.10 and the full one-hour cap about $0.40, before small EBS and
IPv4 charges. This is a planning estimate, not a bill. Bedrock currency cost
will not be claimed until current human-supplied pricing is recorded; calls and
tokens will always be reported.

## Acceptance criteria

M5 is complete only when all of the following are true:

- [x] All new and existing offline tests pass without AWS/model calls (84 passed).
- [ ] Tuning-only k = 0/3/5 evidence is complete and the owner freezes one
      configuration before held-out access.
- [ ] The held-out set is run once with the real Decider, with 45 complete
      predictions, zero mock rows, and immutable evidence.
- [ ] The pre-registered context meets all three owner-approved criteria, or a
      truthful M5 NO-GO is recorded without retuning on held-out data.
- [ ] Both required baselines are complete; Bedrock calls/tokens/latency and
      errors are preserved.
- [ ] The report includes raw counts, ambiguous cases, calibration,
      low-confidence behavior, k comparison, latency, and baseline comparison.
- [ ] Final reported Decider latency names the deployed hardware/environment.
- [ ] The Evaluation tab renders the published saved result exactly and passes
      browser accessibility/layout checks.
- [ ] One real end-to-end SILENT/REACT/REPLY sequence passes, with Bedrock used
      only once for REPLY.
- [ ] All paid infrastructure is terminated and the cleanup inventory is zero.
- [ ] `M5_ACCEPTANCE.md`, `NOTES.md`, `README.md`, and `GO_NOGO.md` contain only
      numbers traceable to the timestamped run bundle.
- [ ] The project owner reviews the evidence and records the final M5 GO/NO-GO.

## Remaining risks

- Fifteen held-out scenarios are a small sample; one error can materially move
  a percentage, and some classes may have very small or zero scored counts.
- M1's unnecessary-interruption result had limited headroom, and the unanimous
  REACT sample was small.
- Human ambiguity reduces the held-out scoring denominator.
- Decider latency and memory may vary with context and cold-start state on the
  CPU instance.
- Bedrock access, quotas, or malformed one-word outputs can block the judge
  baseline; failure must be recorded rather than hidden by unapproved retries.
- The "latest result" API needs explicit publication semantics to avoid serving
  an older calibration or tuning artifact.
- A passing synthetic evaluation does not establish production reliability,
  safety, privacy, load capacity, or statistical generalization.

## Hackathon submission readiness

M5 must preserve the evidence M7 will need, but it will not submit an entry:

- Deadline from the build specification: 2026-10-23 at 11:59 p.m. PT.
- Required topic tags recorded by the specification: `#strands-decider-2b` and
  `#policy`.
- Reusable asset: `decision_pattern/`, including typed question/options,
  confidence policy, Strands hook, under-25-line example, tuning guidance, and
  experimental/synthetic-data limitations.
- README evidence: setup commands, text architecture diagram, exact results
  copied from the final run bundle, costs/tokens, limitations, and MIT license.
- `ARTICLE_NOTES.md`: concise claims and real numbers for the Builder Center
  article, each traceable to M5 evidence.
- `DEMO_SCRIPT.md`: a shot list for a video under three minutes using only real
  outputs; M6 supplies three clean deployed replays.
- Visual proof: readable chat/Live/Evaluation views, deployed health, and saved
  result provenance without AWS identity details or private data.
- Human follow-up still required: confirm who submits the entry and whether the
  official rules allow the intended team arrangement.

## Recommended execution order

1. Approve M5 implementation only (local/offline).
2. Implement harness, baseline, report, API publication, Evaluation tab, and
   fixture-only tests without opening held-out data.
3. Authorize one local real-Decider tuning run, then review its evidence and
   approve the frozen context/thresholds.
4. Approve the one-hour/$0.50 controlled deployment, maximum Bedrock calls, and
   one-time held-out unlock.
5. Run the deployed tuning confirmation, held-out evaluation, baselines,
   end-to-end check, and browser acceptance; terminate immediately.
6. Verify zero AWS leftovers, reconcile every displayed number to artifacts,
   and request the project owner's final M5 GO/NO-GO.
