# Lurker AI

Most AI assistants are designed to answer. This one decides whether it should answer at all.

Lurker is being built for the AWS Strands Decider Agent Hackathon. It observes a synthetic group chat and uses Strands Decider to choose `SILENT`, `REACT`, or `REPLY`. Bedrock is called only for `REPLY`.

## Current status

Milestones M0 through M4 have their recorded approvals, M5 is technically
complete with a preserved model-performance **NO-GO**, and M6 has a
project-owner-approved **FINAL GO**. M6 approval is based on a successful
controlled recovery deployment; it is not production-readiness approval and
the M7 local submission package is ready. The source repository is publicly
available at [Yussif-Attabio/lurker-ai](https://github.com/Yussif-Attabio/lurker-ai).
The Builder Center article, demo video, and final M7 approval remain pending;
new AWS resources and Bedrock calls remain unapproved.

## Architecture

```text
Browser chat
    |
    | WebSocket message
    v
FastAPI pipeline ---> bounded recent-message context (k = 3)
    |
    v
Strands Decider 2B ---> SILENT ---> log only; no Bedrock call
    |                   REACT  ---> local emoji; no Bedrock call
    |                   REPLY  ---> confidence policy ---> Bedrock Converse
    |                                                    |
    +----------------------------------------------------> short agent reply

JSONL decision log ---> REST metrics ---> Live/Evaluation dashboard
```

`src/lurker/decider_adapter.py` is the only door to the Decider API. The model
loads once. Errors, timeouts, unknown choices, and low-confidence actions fail
closed to SILENT. Bedrock errors post no fabricated reply.

## Quick start

Python 3.11 or newer is required. After cloning the repository, safe MOCK mode
requires no AWS account and cannot create evaluation evidence:

```bash
cd lurker-ai
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
MOCK_DECIDER=true PYTHONPATH=. \
  uvicorn src.lurker.api:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Real mode downloads several gigabytes and may
make a paid Bedrock call on REPLY; configure it only after explicit approval.

## Reusable policy pattern

[`decision_pattern/`](decision_pattern/) is the reusable hackathon asset. It
contains the shared typed question and SILENT/REACT/REPLY options, pure
confidence policy, `ChimeInGate`, a minimal example, and
`ChimeInIntervention` wired through the official Strands
`InterventionHandler.before_invocation` seam.

The intervention returns `Proceed` only for REPLY. SILENT and REACT prevent
text generation before the model call; the host does nothing or renders a local
emoji. Installation, tuning guidance, and limitations are in the
[`decision pattern guide`](decision_pattern/README.md).

## Submission results snapshot

Every number here traces to a preserved JSON artifact.

| Evidence | Recorded result |
|---|---|
| Frozen held-out accuracy | 6/9 = 66.7% (NO-GO; gate was at least 70%) |
| Unnecessary interruption | 2/3 = 66.7% (NO-GO; gate was at most 20%) |
| Missed help | 1/6 = 16.7% (PASS; gate was at most 25%) |
| Held-out REACT recall | unavailable; zero unanimous REACT cases |
| Final deployed replay | 3/3 consecutive runs passed |
| Deployed actions | 3 SILENT / 3 REACT / 3 REPLY |
| Bedrock calls | exactly 3 for 9 messages; 6 avoided vs. every message |
| Runtime errors / duplicates | 0 / 0 |
| Deployed Decider p50/p95 | 1,406.05 / 1,516.44 ms |
| Average Bedrock latency | 961.29 ms |
| Bedrock tokens | 477 input / 90 output |
| Peak container memory | 12.41 GiB; no OOM |
| Recovery run estimate | $0.05913 gross |

The model-quality result remains an honest NO-GO even though the controlled M6
reliability recovery earned owner FINAL GO. See
[`results/published.json`](results/published.json),
[`M5_FINAL_ACCEPTANCE.md`](M5_FINAL_ACCEPTANCE.md), and
[`M6_ACCEPTANCE.md`](M6_ACCEPTANCE.md). The original failed M6 deployment is
preserved separately; it was never overwritten by the successful recovery.

## Submission limitations

- Strands Decider 2B is experimental; all chats are synthetic.
- Only nine held-out cases were unanimous, with three SILENT and no REACT cases.
- Held-out accuracy and unnecessary interruption missed their gates.
- The held-out Bedrock judge baseline was not run.
- There is no authentication, database, multi-room support, or third-party chat
  integration.
- One temporary instance does not prove high availability, concurrency, or
  sustained-load performance.
- M6 FINAL GO proves controlled deployment viability, not production readiness
  or model quality.

## Hackathon submission package

The public MIT-licensed repository requirement is now satisfied at
[Yussif-Attabio/lurker-ai](https://github.com/Yussif-Attabio/lurker-ai), and
the latest full offline regression suite has **132 passing tests**. Qualification
still requires the AWS Builder Center article and a public demo video under
three minutes. The final entry requires `#strands-decider-2b` and `#policy`.

- Article facts: [`ARTICLE_NOTES.md`](ARTICLE_NOTES.md)
- Recording plan: [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md)
- Automated recorder: [`DEMO_RECORDING.md`](DEMO_RECORDING.md)
- M7 gate: [`M7_ACCEPTANCE.md`](M7_ACCEPTANCE.md)

## License

Released under the OSI-approved [MIT License](LICENSE).

## Milestone M1 status

M1 has a project-owner-approved **PROVISIONAL GO**. The provisional baseline is
context k = 3, reply threshold 0.20, and REACT threshold 0.04. This is approval
to continue to M2, not production-readiness approval. The prior null-threshold
configuration is preserved in `config/default.pre_m1_provisional.yaml`, and all
historical evaluation outputs remain under `results/`.

The evidence, limitations, and owner decision are recorded in `GO_NOGO.md`.
The held-out dataset remains locked until M5.

## Milestone M2 status

The local backend is implemented: validated configuration, real and mock
Decider boundaries, bounded context, local reactions, Bedrock Converse wrapper,
append-only metrics, background pipeline, REST API, and WebSocket API. The
expanded offline suite passes, and a real uvicorn process in MOCK mode produced
`SILENT`, `REACT`, and `REPLY` over WebSocket without AWS calls.

M2 is **complete**. The owner-approved controlled local acceptance run produced
real `SILENT`, `REACT`, and `REPLY` decisions and exactly one Claude Haiku 4.5
reply. Evidence and scope limitations are recorded in `M2_ACCEPTANCE.md`.
This is not production-readiness or deployment approval.

## Milestone M3 status

M3 has a project-owner-approved **FINAL GO**. The controlled `m7i.2xlarge`
deployment ran for 7 minutes 56 seconds, exposed a healthy real Decider, and
returned `SILENT` through the real external WebSocket pipeline in 1,279.03 ms
with zero Bedrock calls and zero errors. Peak container memory was 12.35 GiB on
the 32 GiB host.

The instance was immediately terminated, all temporary run-scoped resources
were deleted, and a final AWS inventory check returned zero leftovers. Evidence,
cost estimates, safeguards, and limitations are recorded in `M3_ACCEPTANCE.md`.
This is not production-readiness approval, the held-out dataset remains locked,
and the final M3 GO authorized planning only. M4 was subsequently approved and
implemented locally under its separate boundaries.

## Milestone M4 status

M4 has a project-owner-approved **FINAL GO**. The local one-page frontend
provides the three-participant chat, live decision card, exact counters,
decision log, emoji reactions, editable third participant, backend-sourced
About view, explicit MOCK banner, and an M5 Evaluation placeholder with no
sample data.

The browser acceptance produced SILENT, REACT, and REPLY in order, with a 🎉
reaction and a distinct mock Lurker reply. After the mock punctuation and
celebration regression fix, the owner manually retested the frontend and
confirmed it was working correctly. The full offline suite has 76 passing tests,
the Linux amd64 container smoke passed, and required M4 cost was $0. Evidence,
approval, and limitations are recorded in `M4_ACCEPTANCE.md`.

## Milestone M5 status

M5 is **TECHNICALLY COMPLETE WITH A DOCUMENTED HELD-OUT PERFORMANCE NO-GO AND
BEDROCK-BASELINE DEVIATION**. The evidence is preserved and no rerun is
authorized. This is not model-performance or production-readiness approval.
The hardened evaluation guards, bounded baseline runner, explicit final-result
publication, report assembly, and Evaluation tab are implemented. The tab shows
an honest empty state until a complete real M5 bundle is explicitly published.
The complete post-freeze suite has 89 passing tests.

The approved local tuning run completed 90/90 real Decider predictions over the
30 tuning scenarios at k=0/3/5, with zero model failures and no AWS or Bedrock
calls. The original subset scored 80.0% accuracy, 30.0% unnecessary
interruption, and 10.0% missed help at every context. It has no unanimous REACT
label, so REACT precision/recall are not measurable on that subset. Preserved
tuning-only calibration evidence supports retaining k=3, reply 0.20, and REACT
0.04 for owner review; the production configuration has not been changed or
frozen. Evidence is under `results/m5_tuning/20261016T223019Z/`.

No held-out row was predicted, scored, included in tuning evidence, or used to
select thresholds. No Bedrock or AWS call was made. `M5_IMPLEMENTATION_PLAN.md`
defines the remaining configuration freeze, controlled deployed evaluation,
held-out run, end-to-end check, costs, and submission-readiness work.

Audit caveat: the approved run's loader opened the shared scenario source before
filtering it, although no held-out row reached inference, scoring, output, or
threshold selection. This was corrected without a second model run: ordinary
tuning now defaults to the physically separate 30-row
`eval/tuning_scenarios.jsonl`, with regression coverage.
`M5_ACCEPTANCE.md` records this checkpoint and its pending approval gates.

The owner-approved evaluation freeze is k=3, REPLY 0.20, and REACT 0.04. The
model revision, decision contract, metrics, ambiguous-label treatment, success
gates, and checksums are locked in `config/m5_frozen_evaluation.yaml`. The
offline preflight passed without opening held-out data or invoking the model,
AWS, or Bedrock. See `M5_PREFLIGHT.md`; the unexecuted one-time process is in
`M5_HELDOUT_PROCEDURE.md`.

The single authorized held-out Decider run completed 45/45 real predictions
with zero errors or mocks. At primary k=3, accuracy was 66.7% (gate >=70%),
unnecessary interruption was 66.7% (gate <=20%), and missed help was 16.7%
(gate <=25%). The first two gates failed, so the frozen contract yields a
truthful NO-GO. AWS and Bedrock were not used, baselines were not run, and the
configuration was not changed. No held-out rerun or retuning is authorized.
Evidence is under `results/m5_heldout/20261017T053719Z/`.

Recovery preparation is ready for human labeling: 195 new candidates are
grouped into 39 five-item families, with three private evaluator orders and an
expanded decision rubric. Authoring coverage is 65 candidates per intended
action, but those targets are not human labels and are hidden from evaluators.
Exact and cross-family near-duplicate checks passed, all three CSV templates
are blank and complete, the original NO-GO evidence still matches its checksum
manifest, and the full offline suite now has 96 passing tests. Start the local
recovery interface with `PYTHONPATH=. python scripts/labeling_server.py --dataset recovery`;
instructions and safeguards are in
`eval/recovery/LABELING_INSTRUCTIONS.md` and `eval/recovery/PREFLIGHT.md`.

The existing k=3 / REPLY 0.20 / REACT 0.04 settings remain the recovery
starting baseline. The new held-out split does not exist yet and is not
authorized for evaluation. The original NO-GO is unchanged.

Evaluator `a1` completed all 195 rows. Under the owner's single-rater
authorization, an isolated pre-prediction split created 90 balanced development
cases (30 per action) across 18 complete families and a locked 105-case reserve
across 21 disjoint families. The real local Decider completed 270/270
predictions at k=0/3/5 with zero errors. At primary k=3, single-rater agreement
was 71.1%, unnecessary interruption was 30.0%, missed help was 3.3%, REACT
precision was 70.0%, and REACT recall was 46.7%.

An offline sweep of 2,601 threshold pairs found no pair meeting all proposed
recovery gates. Production settings remain k=3 / REPLY 0.20 / REACT 0.04. The
reserve, original held-out set, and any new held-out evaluation remain locked.
Evidence is under
`results/m5_recovery/single_rater/development/20261017T221429Z/`. The complete
offline regression suite now has 98 passing tests.

Development candidate `m5-recovery-social-value-v1` was tested on the same 90
cases and rejected. At k=3 it reduced interruptions from 30.0% to 16.7%, but
REACT precision fell from 70.0% to 66.7%, REACT recall fell from 46.7% to
33.3%, and latency increased. Production wording, thresholds, and policy remain
unchanged. Candidate evidence is under
`results/m5_recovery/single_rater/wording_candidates/m5-recovery-social-value-v1/20261017T223302Z/`.

Label-provenance correction: three people contributed to the completed 195-row
document, but only one final answer per scenario was retained. The labels are
therefore a combined three-contributor reference—not verifiable independent
ratings or verified consensus—and inter-rater agreement cannot be recovered.
The 90 development / 105 locked-reserve split remains unchanged.

Short candidate `m5-recovery-concise-boundaries-v2` was also rejected. Its 90
real local k=3 predictions reduced interruption to 0%, but collapsed REACT
recall to 0%, increased missed help to 36.7%, and reduced accuracy to 54.4%.
Production wording, thresholds, model, and policy remain unchanged. See
`M5_RECOVERY_COMBINED_REFERENCE.md`; 101 safe offline tests pass and M5 remains
NO-GO.

M5 now has a published technical closure using recorded evidence
only. The Evaluation tab truthfully displays the original held-out NO-GO
(66.7% accuracy, 66.7% interruption, unavailable REACT recall), the free
held-out question-mark baseline, and `Bedrock judge: Not run`. The
complete safe suite has 104 passing tests and the 1280px browser acceptance
check passed. The project owner approved technical closure on 2026-10-18;
strict build-spec completion still lacks the held-out Bedrock judge baseline,
and production readiness is not approved.

## Milestone M6 status

M6 has a project-owner-approved **FINAL GO**. Deterministic Decider-timeout,
injected Bedrock-error, browser and WebSocket reconnect, duplicate-prevention,
and Linux `amd64` checks pass. The protected-data-safe suite passed 76 tests
natively and in the container; nine M6-specific network-isolated tests and the
post-recovery 13-test targeted suite also passed.

The original controlled deployment stopped without retry when its first
Bedrock REPLY received `AccessDeniedException`. That deployment remains a
preserved **NO-GO** under `data/m6_acceptance/20261018T192248Z/`. Its evidence
was not overwritten or reclassified.

After offline diagnosis, the corrected least-privilege IAM policy was validated
and used in a separately authorized recovery deployment. Exactly three
consecutive no-retry replays passed, producing three SILENT, three REACT, and
three REPLY actions with exactly three successful Bedrock calls, 477 input
tokens, 90 output tokens, zero runtime errors, and zero duplicate events.
Decider p50/p95 latency was 1,406.05/1,516.44 ms; average Bedrock latency was
961.29 ms. Peak container memory was 12.41 GiB with no OOM.

Recovery cost was estimated at $0.05913, and cumulative controlled M6
deployment cost at approximately $0.15976. The temporary instance and every
run-scoped key, volume, network, and IAM resource were deleted; cleanup checks
found zero unexpected billable resources. Recovery evidence and its SHA-256
manifest are under `data/m6_recovery_acceptance/20261018T201525Z/`.

M5's documented performance NO-GO and Bedrock-baseline deviation remain
unchanged. M6 FINAL GO does not establish production readiness, high
availability, sustained-load performance, or model quality, and it does not
authorize M7, another AWS deployment, or additional Bedrock calls. M7 local
packaging and this repository publication were authorized separately; no new
AWS resource or Bedrock call was used. See `M6_ACCEPTANCE.md`.

Useful offline verification commands:

```bash
PYTHONPATH=. python -m pytest -q
PYTHONPATH=. python scripts/run_baselines.py --help
PYTHONPATH=. python scripts/publish_m5.py --help
node --check web/app.js
```

These commands do not authorize or initiate a real evaluation. Do not pass
`--allow-heldout` or configure the Bedrock baseline until the corresponding
project-owner approvals are recorded.

Run the backend safely in local MOCK mode:

```bash
source .venv/bin/activate
MOCK_DECIDER=true PYTHONPATH=. uvicorn src.lurker.api:app --host 127.0.0.1 --port 8000
```

The MOCK banner is exposed through `/health` as `decider_mode: "mock"`. Mock
events may be written to `data/`, but never to evaluation `results/`.

Start the local, private labeling interface:

```bash
source .venv/bin/activate
PYTHONPATH=. python scripts/labeling_server.py
```

Then open `http://127.0.0.1:8765`. Full evaluator and merge instructions are in
`eval/README.md`. The interface and all M1 scripts run locally; they do not
create AWS resources or call Bedrock.

## M0 setup

Python 3.11 or newer is required.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the real Decider smoke test (the first run downloads several gigabytes):

```bash
PYTHONPATH=. python scripts/smoke_decider.py --device cpu
```

On a supported Apple-silicon setup with the official MLX extra installed, use `--device mlx`. For Bedrock:

```bash
export AWS_REGION="your-region"
export BEDROCK_MODEL_ID="your-enabled-model-id"
PYTHONPATH=. python scripts/smoke_bedrock.py
```

Never commit credentials, private chat data, or fabricated metrics.

## Local verification while AWS access is pending

Run the offline suite; it never invokes Decider or Bedrock:

```bash
PYTHONPATH=. python -m pytest -q
```

Run the read-only AWS credential preflight; it calls only STS
`GetCallerIdentity` and suppresses all identity fields:

```bash
PYTHONPATH=. python scripts/aws_preflight.py --region us-east-2
```

AWS CLI v2 is installed and authenticated locally through the default login
session, with Region `us-east-2`. Never paste access keys or identity output into
this repository or a chat.

Synthetic, unlabeled candidates for human review are in `eval/scenario_candidates.jsonl`. They must not be used for evaluation until humans assign the split and three independent labels described in `eval/README.md`.
