# Milestone M5 acceptance

Status: **HELD-OUT PRIMARY NO-GO - EVIDENCE PRESERVED; NO RERUN AUTHORIZED**

## Authorized scope completed - 2026-10-16

The project owner authorized M5 local/offline implementation only. This
checkpoint implemented the infrastructure needed for the final evaluation
without opening the held-out split or invoking any real model or AWS service.

- Held-out scenarios opened or evaluated: 0.
- Real Decider calls: 0.
- Bedrock calls: 0.
- AWS API calls and resources launched: 0.
- Required cost: $0.
- Provisional production configuration changed: no.

## Delivered

- Hardened real-evaluation validation:
  - duplicate and cross-split scenario rejection;
  - exactly one row per scenario/context pair;
  - finite confidence and latency checks;
  - explicit error counts in metrics and acceptance status;
  - immutable config snapshot, scenario/config hashes, and run manifest.
- Required baselines:
  - punctuation-based `always_reply_to_questions` with zero model calls;
  - injectable Bedrock Converse judge with exact option normalization;
  - hard maximum of 15 calls, temperature 0, eight output tokens, no retries,
    and per-case latency/token/error evidence.
- Explicit M5 publication:
  - only a complete `lurker-m5-v1` held-out summary can be published;
  - raw counts must agree with rates;
  - k=0/3/5, both baselines, frozen thresholds, error-free real-run manifest,
    and complete prediction counts are required;
  - publication is atomic and refuses to overwrite prior final evidence;
  - `/api/eval/latest` fails closed with 404 before publication and 503 for an
    invalid published artifact.
- Evaluation frontend:
  - enabled Evaluation tab;
  - honest unpublished/loading/error states with no sample numbers;
  - primary PASS/FAIL, raw-count metrics, k comparison, latency, baseline
    comparison, calibration, provenance, and evidence-boundary views;
  - same-origin lazy loading and safe `textContent` rendering only.
- M5 orchestration utilities:
  - `scripts/run_baselines.py` for one guarded baseline run;
  - `scripts/publish_m5.py` for assembling and publishing only complete saved
    artifacts;
  - final Markdown report generation without recomputing source metrics.

## Offline verification

- Focused evaluation/backend/frontend suite: 32 passed.
- Complete offline regression suite: 84 passed.
- JavaScript syntax check: PASS.
- Python modules were imported and exercised by pytest: PASS.
- Local browser empty-state check: Evaluation tab selectable, tabpanel visible,
  unpublished message accurate, sample/provisional numbers absent, console
  warnings/errors 0.
- Pytest cache warning: environmental write restriction only; test execution
  and results were unaffected.

All tests use synthetic in-memory or temporary-directory fixtures. Fake metrics
were not written to `results/`, served by the project preview, or documented as
project performance.

## Local real-Decider tuning run - 2026-10-16

The project owner authorized one local, tuning-only real-Decider run. The model
was loaded once from its local cache with Hugging Face/Transformers offline and
AWS instance metadata disabled. No AWS API or Bedrock path was invoked.

- Scenarios: 30 existing tuning scenarios.
- Context settings: k=0, k=3, and k=5.
- Predictions: 90 expected, 90 recorded.
- Human-label distribution per context: 10 SILENT, 0 REACT, 10 REPLY, and 10
  AMBIGUOUS.
- Model: `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610`, local CPU.
- Applied provisional policy: reply 0.20, REACT 0.04.
- Initialization: 11,667.93 ms; initialization failures: 0.
- Inference failures: 0; AWS calls: 0; Bedrock calls: 0.
- Process maximum RSS: 5,992,611,840 bytes (5.58 GiB).
- macOS peak memory footprint: 8,425,331,624 bytes (7.85 GiB).
- Wall time: 81.07 seconds.

| Context | Accuracy | Unnecessary interruption | Missed help | REACT P/R | Latency p50 / p95 |
|---|---:|---:|---:|---:|---:|
| k=0 | 16/20 (80.0%) | 3/10 (30.0%) | 1/10 (10.0%) | N/A / N/A | 619.21 / 2,007.27 ms |
| k=3 | 16/20 (80.0%) | 3/10 (30.0%) | 1/10 (10.0%) | N/A / N/A | 612.01 / 790.95 ms |
| k=5 | 16/20 (80.0%) | 3/10 (30.0%) | 1/10 (10.0%) | N/A / N/A | 615.78 / 1,068.60 ms |

REACT precision/recall are unavailable on the original 30 because there is no
unanimous REACT ground truth. The one REACT prediction at each context is on an
AMBIGUOUS case, which is excluded from class metrics. All 90 raw choices and
confidence values exactly matched the preserved M1 run; six final actions
changed only because the provisional thresholds are now applied.

The offline sweep of the preserved tuning-plus-REACT-calibration evidence shows:

- k=0 with reply 0.40 / REACT 0.13: 87.1% accuracy, 5.9% unnecessary
  interruption, 10.0% missed help, 100% REACT precision, 50% REACT recall.
- k=3 with reply 0.20 / REACT 0.04: 83.9% accuracy, 17.6% unnecessary
  interruption, 10.0% missed help, 100% REACT precision, 75% REACT recall.
- k=5 with reply 0.20 / REACT 0.04: the same quality metrics as k=3, with worse
  fresh-run tail latency.

Recommendation for owner review: retain k=3, reply 0.20, and REACT 0.04. The
k=0 candidate's modest accuracy/interruption gain costs 25 percentage points of
REACT recall; k=5 provides no measured quality gain. This recommendation did
not modify `config/default.yaml` and is not yet a configuration freeze.

Evidence: `results/m5_tuning/20261016T223019Z/`, including raw per-case
predictions, exact configuration, run manifest and hashes, full threshold
sweeps, resource usage, and before/after comparison. No held-out row was
predicted, scored, included in an artifact, or used for tuning.

Storage-boundary limitation: during the approved run, `scripts/run_eval.py`
parsed the shared 45-row scenario file and then filtered by split. Consequently, the approved run
did not evaluate or expose held-out rows to the Decider, metrics, threshold
sweeps, or result artifacts, but its loader did open the shared source. This is
preserved as a limitation of that run under the strictest interpretation of
"completely locked."

The storage guard was corrected immediately afterward without another model
run: `eval/tuning_scenarios.jsonl` is an exact 30-row tuning-only snapshot, and
ordinary `--split tuning` runs now default to it rather than the shared source.
A regression test verifies the physical path separation, row count, and
tuning-only content. Post-correction complete suite: 85 passed.

## Final evaluation configuration freeze - 2026-10-16

The project owner approved the final evaluation configuration: k=3, REPLY
threshold 0.20, and REACT threshold 0.04. No production setting was changed;
the existing values were recorded as the immutable M5 evaluation baseline.

The freeze preserves:

- model ID `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610` at local cache
  revision `216d1ccb46a9e9b036eb9187b248db98480f77d4`;
- exact decision wording and SILENT/REACT/REPLY options;
- last-three-message context construction;
- confidence downgrade and fail-closed action policy;
- metric formulas, ambiguous-label handling, success thresholds, code/config
  checksums, and pre-freeze evidence-tree checksums.

Only k=3 is the held-out pass/fail context. k=0 and k=5 are comparison-only.
The frozen gates are accuracy >=70%, unnecessary interruption <=20%, missed
help <=25%, 45/45 predictions, zero Decider errors, and zero mock rows. REACT
precision/recall and latency remain mandatory reports but have no post-hoc
pass threshold.

The original tuning subset's 30.0% unnecessary-interruption rate (3/10) remains
explicit beside the combined tuning/calibration result of 17.6% (3/17). The
combined number does not replace the original subset result.

Preflight results:

- physically separate tuning input: 30 rows, tuning split only;
- audited proof that the tuning loader did not open the shared source: PASS;
- named dataset-isolation tests: 4 passed;
- freeze/unlock focused tests: 10 passed;
- complete offline suite: 89 passed;
- tuning evidence tree and calibration evidence tree: unchanged;
- model revision and all frozen artifact hashes: matched;
- held-out data opened: no; model/AWS/Bedrock calls: 0.

Freeze contract: `config/m5_frozen_evaluation.yaml`, SHA-256
`52a54a7058f53886bc789d930670e6f74407603105b13c13d01238ca24658401`.
Machine-readable preflight: `data/archive/evaluation_freeze/20261017T002835Z/preflight.json`.
Human-readable preflight: `M5_PREFLIGHT.md`. The guarded procedure is prepared
in `M5_HELDOUT_PROCEDURE.md` but has not been executed.

## Remaining gates

M5 is not complete. These steps still require their approvals and real evidence:

1. Local real-Decider tuning run across 30 tuning scenarios at k=0/3/5: PASS.
2. Project-owner review and freeze of k=3, reply 0.20, REACT 0.04: PASS.
3. Owner approval of the Bedrock judge model/call cap and the controlled AWS
   duration/spending limit.
4. One deployed tuning confirmation for final-environment latency.
5. One held-out unlock and real-Decider run across 15 cases at k=0/3/5.
6. Both real held-out baselines, including at most 15 Bedrock judge calls.
7. One deployed SILENT/REACT/REPLY end-to-end check with exactly one generated
   Bedrock reply.
8. Evaluation-tab browser acceptance using only the published real bundle.
9. Immediate infrastructure cleanup and a zero-leftover AWS inventory check.
10. Project-owner final M5 GO/NO-GO.

No held-out result may be used to retune the frozen configuration. A failed
criterion produces a truthful M5 NO-GO and preserved evidence, not a hidden
rerun.

## One-time held-out Decider evaluation - NO-GO - 2026-10-17

Authorization `chat-20261017-one-time-m5-heldout` permitted one local-only
held-out run: 15 scenarios at k=0/3/5, exactly 45 real Decider predictions,
with the frozen k=3 / REPLY 0.20 / REACT 0.04 policy. AWS deployment, Bedrock,
judge baselines, mocks, retuning, configuration changes, and additional runs
were prohibited.

Pre-unlock freeze verification passed all 16 checks. The exclusive held-out
input contained 15 rows and has SHA-256
`76753bd8e2820d8c82888f78d2784cc02913ab73e4ef9c128a28cd44059ee876`.
The real model produced exactly 45 unique scenario/context predictions, 15 per
context, with zero errors and zero mock rows.

| Context | Accuracy | Unnecessary interruption | Missed help | REACT precision/recall | p50 / p95 |
|---|---:|---:|---:|---:|---:|
| k=0 | 6/9 (66.7%) | 1/3 (33.3%) | 2/6 (33.3%) | 0/1 (0%) / N/A | 583.63 / 1,239.53 ms |
| **k=3 primary** | **6/9 (66.7%)** | **2/3 (66.7%)** | **1/6 (16.7%)** | **0/1 (0%) / N/A** | **598.81 / 682.34 ms** |
| k=5 | 6/9 (66.7%) | 2/3 (66.7%) | 1/6 (16.7%) | 0/1 (0%) / N/A | 612.08 / 1,733.60 ms |

Each context has nine unanimous and six AMBIGUOUS cases. Ambiguous cases were
handled exactly as frozen. There are zero unanimous REACT cases, so recall is
N/A; the only scored REACT prediction was incorrect, so precision is 0/1.

Primary frozen gates:

- Accuracy >=70%: FAIL at 66.7%.
- Unnecessary interruption <=20%: FAIL at 66.7%.
- Missed help <=25%: PASS at 16.7%.
- 45/45 predictions, zero errors, zero mocks: PASS.
- Frozen configuration, policy, wording, model revision, and checksums: PASS.
- One run only; no AWS/Bedrock; no retuning/configuration change: PASS.

The frozen contract therefore requires a truthful held-out NO-GO. The result is
not published as a completed M5 bundle because the primary criteria failed and
the separately restricted baselines were not run. No rerun or configuration
change is authorized. Evidence:
`results/m5_heldout/20261017T053719Z/`.

## Single-evaluator recovery development - EXPLORATORY ONLY - 2026-10-17

The owner authorized using evaluator `a1` alone and ignoring the other two
exports. This changes only the development evidence path. It does not convert
one person's labels into consensus, create a new held-out set, reverse the
original NO-GO, or authorize final M5 approval.

The complete 195-row export passed ID, label, blank, and duplicate checks. A
deterministic pre-prediction family split produced:

- 90 development rows: 30 SILENT, 30 REACT, and 30 REPLY across 18 families;
- 105 locked reserve rows across 21 disjoint families;
- zero family leakage, zero held-out access, and zero model predictions before
  the split was frozen.

The real local Decider completed 270/270 development predictions at k=0/3/5
with zero errors, no mocks, no AWS or Bedrock calls, and no production
configuration change.

| Context | Accuracy | Unnecessary interruption | Missed help | REACT precision | REACT recall | p50 / p95 |
|---|---:|---:|---:|---:|---:|---:|
| k=0 | 65/90 (72.2%) | 8/30 (26.7%) | 3/30 (10.0%) | 16/23 (69.6%) | 16/30 (53.3%) | 542.71 / 937.74 ms |
| **k=3** | **64/90 (71.1%)** | **9/30 (30.0%)** | **1/30 (3.3%)** | **14/20 (70.0%)** | **14/30 (46.7%)** | **581.54 / 1,100.80 ms** |
| k=5 | 64/90 (71.1%) | 9/30 (30.0%) | 1/30 (3.3%) | 14/20 (70.0%) | 14/30 (46.7%) | 586.22 / 1,292.17 ms |

Initialization took 11.73 seconds and peak RSS was approximately 5.59 GiB. An
offline k=3 sweep evaluated 2,601 threshold pairs without another model call.
No pair met every proposed recovery gate. The best observed tradeoff was REPLY
0.24 / REACT 0.06, but REACT recall remained 46.7%, so it is not recommended.
Production thresholds remain unchanged at REPLY 0.20 / REACT 0.04.

The complete offline suite has 98 passing tests. Evidence is preserved under
`results/m5_recovery/single_rater/development/20261017T221429Z/`. M5 remains a
NO-GO and incomplete. Final recovery acceptance still requires independently
validated labels and a separately authorized held-out procedure.

## Development wording candidate - REJECT - 2026-10-17

The owner approved a development-only wording comparison on the same 90
single-evaluator cases. Candidate `m5-recovery-social-value-v1` preserved model
ID/revision, contexts, thresholds, action policy, and production configuration.
It completed 270/270 local predictions with zero errors and no AWS or Bedrock
calls.

At primary k=3, accuracy remained 71.1%, interruption improved from 30.0% to
16.7%, and missed help remained 3.3%. REACT precision fell from 70.0% to 66.7%
and recall fell from 46.7% to 33.3%. p50/p95 latency increased from
581.54/1,100.80 ms to 848.25/1,605.11 ms. The candidate gained two correct
reactions, lost six, and introduced no new missed requests.

The candidate is rejected for production because reduced interruption came at
the cost of worse REACT recognition and higher latency. Original production
wording, REPLY 0.20, REACT 0.04, and policy remain unchanged. M5 remains NO-GO.

Audit caveat: a preservation checksum and the existing recovery-audit test made
a read-only hash access to the original held-out JSONL during this task. No
scenario text was displayed or parsed, no file was changed, and it was excluded
from all analysis/model inputs. The candidate runner and comparison themselves
opened neither held-out data nor the 105-case reserve.

## Combined three-contributor provenance correction - 2026-10-17

The 195 labels previously described as evaluator `a1` were produced in one
combined document to which three people contributed. Because their individual
answers and the aggregation process were not saved, this is not verifiable
independent labeling and is not verifiable unanimous or group consensus.
Inter-rater agreement cannot be calculated. The 90 development labels may be
used only as a combined reference for development comparisons.

The corrected provenance is additive and does not overwrite previous evidence.
The 90-row development / 105-row reserve family separation remains unchanged;
the reserve remains unopened and unscored. The original M5 held-out NO-GO is
still the governing acceptance result.

Concise wording candidate `m5-recovery-concise-boundaries-v2` was evaluated
locally on exactly the 90 development cases at frozen k=3 and thresholds 0.20 /
0.04. It completed 90/90 real predictions with zero errors and zero AWS or
Bedrock calls.

| Metric | Original | Concise v2 |
|---|---:|---:|
| Accuracy | 64/90 (71.1%) | 49/90 (54.4%) |
| Unnecessary interruption | 9/30 (30.0%) | 0/30 (0.0%) |
| Missed help | 1/30 (3.3%) | 11/30 (36.7%) |
| REACT precision | 14/20 (70.0%) | N/A (0 predictions) |
| REACT recall | 14/30 (46.7%) | 0/30 (0.0%) |

The candidate is **REJECTED** because it disabled REACT behavior and introduced
ten new missed requests. Production wording, thresholds, model, and policy were
not changed. The safe regression suite passed 101 tests with the one legacy
held-out-hashing audit deselected. This development experiment does not alter
the M5 NO-GO.

## Finalization candidate - technical closure pending - 2026-10-18

All further Decider wording and threshold experiments are stopped. The original
configuration, model revision, wording, architecture, and policy remain frozen.
The original held-out result is preserved without rerun or modification:
accuracy 6/9 (66.7%), unnecessary interruption 2/3 (66.7%), missed help 1/6
(16.7%), and unavailable REACT recall because the scored set has zero unanimous
REACT cases.

The local question-mark baseline completed on the same 15 held-out cases with
6/9 (66.7%) accuracy, 1/3 (33.3%) interruption, and 2/6 (33.3%) missed help.
It made zero Decider, AWS, or Bedrock calls and did not alter or rerun the
original frozen Decider evaluation.

The Evaluation tab publishes the real NO-GO metrics, shows the held-out
question-mark baseline, and displays the held-out Bedrock judge as `Not run`. Browser
acceptance at 1280x900 passed with zero console errors. The complete safe suite
has 104 passing tests; one legacy audit remains deselected because it opens the
original held-out file solely to hash it.

Existing M2 evidence verifies SILENT, REACT, and REPLY through the real
WebSocket pipeline, with no Bedrock call for SILENT/REACT and exactly one for
REPLY. No new paid pipeline test is needed.

Acceptance distinction:

- Implementation completion: ready for owner-approved technical closure.
- Model-performance acceptance: **NO-GO**.
- Strict original M5 checklist: incomplete only because the Bedrock judge was
  not run on the held-out set.
- Production readiness: not approved.

No AWS resources or Bedrock calls were used.

## Final owner decision - 2026-10-18

The project owner approved M5 as **TECHNICALLY COMPLETE WITH DOCUMENTED
PERFORMANCE NO-GO AND BEDROCK-BASELINE DEVIATION**. This closes implementation
work for M5 while preserving the failed held-out performance decision.

- Model-performance acceptance: **NO-GO**.
- Strict original checklist: incomplete only for the Bedrock judge baseline.
- Production readiness: not approved.
- Further Decider experiments: stopped.
- AWS resources and Bedrock calls for closure: zero.
