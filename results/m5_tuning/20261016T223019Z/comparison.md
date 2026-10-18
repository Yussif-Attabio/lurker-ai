# M5 local real-Decider tuning comparison

Scope: tuning data only. No held-out row was predicted, scored, included in a
result artifact, or used for threshold selection. Production configuration was
not changed.

## Fresh 30-scenario run at the provisional thresholds

| Context | Accuracy | Unnecessary interruption | Missed help | REACT precision | REACT recall | p50 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| k=0 | 16/20 (80.0%) | 3/10 (30.0%) | 1/10 (10.0%) | N/A (0/0) | N/A (0/0) | 619.21 ms | 2,007.27 ms |
| k=3 | 16/20 (80.0%) | 3/10 (30.0%) | 1/10 (10.0%) | N/A (0/0) | N/A (0/0) | 612.01 ms | 790.95 ms |
| k=5 | 16/20 (80.0%) | 3/10 (30.0%) | 1/10 (10.0%) | N/A (0/0) | N/A (0/0) | 615.78 ms | 1,068.60 ms |

The 30 original scenarios contain 20 unanimous cases: 10 SILENT, 10 REPLY,
and zero REACT. Ten cases are AMBIGUOUS and excluded from label-dependent
rates. REACT precision and recall are therefore unidentifiable on this subset;
the one REACT output at each context occurred on an ambiguous case.

All 90 raw choices and confidence scores exactly match the preserved M1 run.
There are zero raw-choice changes and a maximum confidence delta of 0. Six
final actions differ because the M1 provisional thresholds are now applied;
the model itself shows no observed prediction drift.

Compared on the same 30 scenarios at k=3, the provisional policy raises
accuracy from 75.0% to 80.0% and lowers unnecessary interruption from 50.0% to
30.0%, while missed help rises from 0.0% to 10.0%. Compared with the broader
45-scenario M1 tuning-plus-calibration baseline, the fresh 30-only result is
3.9 percentage points lower in accuracy and 12.4 points higher in unnecessary
interruption, with missed help unchanged. That second comparison is not
like-for-like because the fresh run intentionally excludes the separate REACT
calibration set.

## Offline threshold evidence

The new 30-only sweep cannot identify a REACT threshold because it has no
unanimous REACT label. The preserved tuning-only calibration predictions do
contain four unanimous REACT cases, so they were combined offline with the
fresh-drift-checked original tuning evidence; this made no additional model
call.

| Candidate | Accuracy | Unnecessary interruption | Missed help | REACT precision | REACT recall |
|---|---:|---:|---:|---:|---:|
| k=0, reply 0.40, REACT 0.13 | 27/31 (87.1%) | 1/17 (5.9%) | 1/10 (10.0%) | 2/2 (100%) | 2/4 (50%) |
| k=3, reply 0.20, REACT 0.04 | 26/31 (83.9%) | 3/17 (17.6%) | 1/10 (10.0%) | 3/3 (100%) | 3/4 (75%) |
| k=5, reply 0.20, REACT 0.04 | 26/31 (83.9%) | 3/17 (17.6%) | 1/10 (10.0%) | 3/3 (100%) | 3/4 (75%) |

## Recommendation for owner review

Keep **k=3, reply threshold 0.20, and REACT threshold 0.04** as the proposed M5
freeze. k=0 improves overall accuracy by 3.2 points and interruption by 11.7
points, but its REACT recall drops by 25 points. k=5 provides no measured
quality benefit over k=3 and has worse fresh-run p95 latency. The existing k=3
configuration is the best balanced tuning-only choice and remains a top-ranked
passing threshold pair on the combined tuning evidence.

This is a recommendation, not a freeze or production change. Owner approval is
still required before any deployed or held-out work. The current loader also
opened the shared scenario source before filtering during this run; although no
held-out row was inferred, scored, emitted, or used, that is a strict-lock
limitation of the run. The runner was corrected afterward, without another
model call, to default to a physically separate 30-row tuning input.
