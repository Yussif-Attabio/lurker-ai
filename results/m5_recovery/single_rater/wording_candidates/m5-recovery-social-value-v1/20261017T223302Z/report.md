# Single-evaluator wording candidate: m5-recovery-social-value-v1

> Development-only comparison. This is not human consensus, held-out evidence, production configuration, or final M5 acceptance.

- Generated: 2026-10-17T22:33:02.295793+00:00
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
| 0 | 90 | 0 | 0 | 68/90 (75.6%) | 2/30 (6.7%) | 1/30 (3.3%) | 803.58 ms | 1211.81 ms | PASS |
| 3 | 90 | 0 | 0 | 64/90 (71.1%) | 5/30 (16.7%) | 1/30 (3.3%) | 848.25 ms | 1605.11 ms | PASS |
| 5 | 90 | 0 | 0 | 64/90 (71.1%) | 5/30 (16.7%) | 1/30 (3.3%) | 853.67 ms | 1602.93 ms | PASS |

## Low-confidence handling

### k = 0

- Downgraded: 0
- Accuracy before downgrade: 0/0 (N/A)
- Accuracy after downgrade: 0/0 (N/A)

### k = 3

- Downgraded: 0
- Accuracy before downgrade: 0/0 (N/A)
- Accuracy after downgrade: 0/0 (N/A)

### k = 5

- Downgraded: 0
- Accuracy before downgrade: 0/0 (N/A)
- Accuracy after downgrade: 0/0 (N/A)

## Calibration

### k = 0

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 32/46 | 69.6% |
| 0.5-0.7 | 27/34 | 79.4% |
| 0.7-0.9 | 9/10 | 90.0% |
| 0.9-1.0 | 0/0 | N/A |

### k = 3

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 33/52 | 63.5% |
| 0.5-0.7 | 25/31 | 80.6% |
| 0.7-0.9 | 6/7 | 85.7% |
| 0.9-1.0 | 0/0 | N/A |

### k = 5

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 33/52 | 63.5% |
| 0.5-0.7 | 25/31 | 80.6% |
| 0.7-0.9 | 6/7 | 85.7% |
| 0.9-1.0 | 0/0 | N/A |

## Ambiguous cases

No human-ambiguous cases were present in this split.

## Decision status

This report is evidence only. The project owner must record the final decision in `GO_NOGO.md`.
