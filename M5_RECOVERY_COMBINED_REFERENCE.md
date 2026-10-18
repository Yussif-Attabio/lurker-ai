# M5 recovery: combined three-contributor reference

Status: **DEVELOPMENT-ONLY; M5 REMAINS NO-GO**

## Human-label provenance correction

Three people contributed to the completed 195-scenario evaluation, but their
answers were saved as one final label per scenario in a single combined
document. The individual response sets and the combination process were not
retained. Therefore:

- the document is a **combined three-contributor reference**, not a
  single-evaluator export;
- the project cannot verify that the contributors decided independently;
- the project cannot verify unanimity, majority voting, or group consensus;
- inter-rater agreement and an ambiguity pool cannot be reconstructed.

Earlier single-rater artifacts are preserved unchanged as historical evidence.
The corrected provenance is versioned separately in
`eval/recovery/combined_reference/provenance_manifest.json`.

The same pre-existing family split is retained: 90 development scenarios (30
SILENT, 30 REACT, 30 REPLY) across 18 complete families, and 105 reserved
scenarios across 21 disjoint families. The migration read only the existing
90-row development file and prior split manifest. It did not open or evaluate
the reserve. It did not open the original M5 held-out dataset.

## Original-wording development errors at k=3

The original configuration produced 64/90 correct decisions. The confusion
pattern was:

| Reference | SILENT prediction | REACT prediction | REPLY prediction |
|---|---:|---:|---:|
| SILENT | 21 | 6 | 3 |
| REACT | 15 | 14 | 1 |
| REPLY | 1 | 0 | 29 |

The 16 missed REACT cases were mostly classification mistakes: 12 were raw
SILENT and four were raw REPLY. Three of those raw REPLY choices were then
correctly downgraded to SILENT by the unchanged 0.20 threshold; the threshold
did not create the underlying REACT misclassification. These cases cluster
around achievements stated matter-of-factly, impact on other people, gratitude
or belonging, mixed-emotion setbacks, personal good news, and shared humor.

The nine unnecessary interruptions were six raw REACT choices and three raw
REPLY choices. Seven occurred in casual conversation, one in a technical
update, and one in shared humor. They cluster around routine positive results,
answers to earlier questions, gratitude/closure, and moments that are
semantically close to examples labeled REACT.

Several neighboring examples have hard-to-reconcile boundaries—for example,
a first-time test success is labeled REACT while another green test update is
labeled SILENT; a reported accessibility impact is labeled REACT while a
reported time-saving impact is labeled SILENT. This may reflect a legitimate
fine-grained preference, but without individual labels or notes it is also
possible label noise. The development scores must therefore be treated as
agreement with one combined reference document, not an objective ground truth.

## Concise wording candidate v2

Candidate `m5-recovery-concise-boundaries-v2` is shorter than the production
wording and adds three general boundaries:

1. an answer to an earlier question is not a new request;
2. meaningful social value can exist without expressive punctuation;
3. routine positivity, politeness, closure, and already-handled points should
   stay SILENT.

It preserves the model ID and revision, model architecture, k=3 context,
SILENT/REACT/REPLY options, REPLY 0.20 and REACT 0.04 thresholds, context
builder, and action policy.

The real local Decider completed exactly 90/90 development predictions with
zero errors, no mocks, no AWS or Bedrock calls, and no reserve or held-out
access.

Post-run verification passed 101 offline tests with the one legacy audit that
hashes the original held-out file deliberately deselected. Production
configuration, decision wording, and evaluation runner checksums remain equal
to their frozen values.

| Metric | Original wording | Concise v2 | Change |
|---|---:|---:|---:|
| Accuracy | 64/90 (71.1%) | 49/90 (54.4%) | -16.7 pp |
| Unnecessary interruption | 9/30 (30.0%) | 0/30 (0.0%) | -30.0 pp |
| Missed help | 1/30 (3.3%) | 11/30 (36.7%) | +33.3 pp |
| REACT precision | 14/20 (70.0%) | 0/0 (N/A) | N/A |
| REACT recall | 14/30 (46.7%) | 0/30 (0.0%) | -46.7 pp |
| Latency p50 | 581.54 ms | 578.22 ms | -3.31 ms |
| Latency p95 | 1,100.80 ms | 1,519.69 ms | +418.89 ms |

Candidate predictions were 71 SILENT, zero REACT, and 19 REPLY. It repaired
all nine baseline interruptions, but only by collapsing the REACT class and by
introducing ten new missed requests. It lost all 14 previously correct REACT
decisions and gained none.

## Recommendation

**Reject concise v2 and do not apply it to production.** It fails the stated
goal of improving REACT recall and creates an unacceptable missed-help
regression. Keep the original wording, k=3, REPLY 0.20, REACT 0.04, model, and
policy unchanged.

The next safe development step, if separately approved, is one more wording
candidate that keeps the original question structure and makes only a minimal
REACT/SILENT boundary edit. No threshold change is supported by this run. Any
eventual final claim still needs independently retained labels and a new,
pre-frozen held-out evaluation; the 105 reserved cases remain locked.

Evidence:

- `eval/recovery/combined_reference/provenance_manifest.json`
- `config/wording_candidates/m5_recovery_concise_boundaries_v2.yaml`
- `results/m5_recovery/combined_reference/wording_candidates/m5-recovery-concise-boundaries-v2/20261017T224434Z/`

The original M5 NO-GO evidence remains preserved. M5 is not complete.
