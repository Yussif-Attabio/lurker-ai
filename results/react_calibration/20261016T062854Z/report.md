# Lurker AI evaluation report

- Generated: 2026-10-16T06:28:54.176805+00:00
- Split: `tuning`
- Model: `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610`
- Device: `cpu`
- Hardware: Darwin arm64 / arm
- Policy mode: `unthresholded_tuning`
- Reply threshold: `None`
- React threshold: `None`

## Human-approved success criteria

- Accuracy >= 70%
- Unnecessary-interruption rate <= 20%
- Missed-help rate <= 25%

> This is an unthresholded tuning run. Use `tune_thresholds.py`, have a human choose thresholds, update config, and rerun before making a go/no-go decision.

## Context comparison

| k | Scored | Ambiguous | Accuracy | Unnecessary interruption | Missed help | Latency p50 | Latency p95 | Criteria |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 11 | 4 | 7/11 (63.6%) | 0/7 (0.0%) | 0/0 (N/A) | 471.25 ms | 971.43 ms | PENDING |
| 3 | 11 | 4 | 7/11 (63.6%) | 1/7 (14.3%) | 0/0 (N/A) | 536.62 ms | 611.39 ms | PENDING |
| 5 | 11 | 4 | 7/11 (63.6%) | 1/7 (14.3%) | 0/0 (N/A) | 547.48 ms | 591.74 ms | PENDING |

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
| 0.0-0.5 | 5/9 | 55.6% |
| 0.5-0.7 | 2/2 | 100.0% |
| 0.7-0.9 | 0/0 | N/A |
| 0.9-1.0 | 0/0 | N/A |

### k = 3

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 7/11 | 63.6% |
| 0.5-0.7 | 0/0 | N/A |
| 0.7-0.9 | 0/0 | N/A |
| 0.9-1.0 | 0/0 | N/A |

### k = 5

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 7/11 | 63.6% |
| 0.5-0.7 | 0/0 | N/A |
| 0.7-0.9 | 0/0 | N/A |
| 0.9-1.0 | 0/0 | N/A |

## Ambiguous cases

Ambiguous cases are listed but excluded from every scored rate.

| k | ID | Raw choice | Final action | Confidence |
|---:|---|---|---|---:|
| 0 | r003 | SILENT | SILENT | 0.3524 |
| 0 | r012 | SILENT | SILENT | 0.4473 |
| 0 | r013 | SILENT | SILENT | 0.4569 |
| 0 | r014 | SILENT | SILENT | 0.3651 |
| 3 | r003 | SILENT | SILENT | 0.3524 |
| 3 | r012 | SILENT | SILENT | 0.2392 |
| 3 | r013 | SILENT | SILENT | 0.0537 |
| 3 | r014 | SILENT | SILENT | 0.2473 |
| 5 | r003 | SILENT | SILENT | 0.3524 |
| 5 | r012 | SILENT | SILENT | 0.2392 |
| 5 | r013 | SILENT | SILENT | 0.0537 |
| 5 | r014 | SILENT | SILENT | 0.2473 |

## Decision status

This report is evidence only. The project owner must record the final decision in `GO_NOGO.md`.
