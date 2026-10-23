# Single-evaluator exploratory recovery evaluation

> These metrics compare model predictions with one evaluator's labels. They are not human consensus, held-out evidence, or final M5 acceptance evidence.

- Generated: 2026-10-17T22:14:29.053739+00:00
- Split: `tuning`
- Model: `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610`
- Device: `cpu`
- Hardware: Darwin arm64 / arm
- Policy mode: `configured_thresholds`
- Reply threshold: `0.2`
- React threshold: `0.04`

## Human-approved success criteria

- Accuracy >= 70%
- Unnecessary-interruption rate <= 20%
- Missed-help rate <= 25%

## Context comparison

| k | Scored | Ambiguous | Errors | Accuracy | Unnecessary interruption | Missed help | Latency p50 | Latency p95 | Criteria |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 90 | 0 | 0 | 65/90 (72.2%) | 8/30 (26.7%) | 3/30 (10.0%) | 542.71 ms | 937.74 ms | FAIL |
| 3 | 90 | 0 | 0 | 64/90 (71.1%) | 9/30 (30.0%) | 1/30 (3.3%) | 581.54 ms | 1100.80 ms | FAIL |
| 5 | 90 | 0 | 0 | 64/90 (71.1%) | 9/30 (30.0%) | 1/30 (3.3%) | 586.22 ms | 1292.17 ms | FAIL |

## Low-confidence handling

### k = 0

- Downgraded: 5
- Accuracy before downgrade: 1/5 (20.0%)
- Accuracy after downgrade: 2/5 (40.0%)

### k = 3

- Downgraded: 5
- Accuracy before downgrade: 0/5 (0.0%)
- Accuracy after downgrade: 2/5 (40.0%)

### k = 5

- Downgraded: 5
- Accuracy before downgrade: 0/5 (0.0%)
- Accuracy after downgrade: 2/5 (40.0%)

## Calibration

### k = 0

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 58/80 | 72.5% |
| 0.5-0.7 | 6/9 | 66.7% |
| 0.7-0.9 | 1/1 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

### k = 3

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 55/79 | 69.6% |
| 0.5-0.7 | 8/10 | 80.0% |
| 0.7-0.9 | 1/1 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

### k = 5

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 55/79 | 69.6% |
| 0.5-0.7 | 8/10 | 80.0% |
| 0.7-0.9 | 1/1 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

## Ambiguous cases

No human-ambiguous cases were present in this split.

## Decision status

This report is evidence only. The project owner must record the final decision in `GO_NOGO.md`.
