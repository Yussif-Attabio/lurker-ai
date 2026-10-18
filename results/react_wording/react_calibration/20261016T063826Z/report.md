# Lurker AI evaluation report

- Generated: 2026-10-16T06:38:26.028882+00:00
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
| 0 | 11 | 4 | 6/11 (54.5%) | 1/7 (14.3%) | 0/0 (N/A) | 648.59 ms | 1125.56 ms | PENDING |
| 3 | 11 | 4 | 4/11 (36.4%) | 3/7 (42.9%) | 0/0 (N/A) | 746.00 ms | 996.34 ms | PENDING |
| 5 | 11 | 4 | 4/11 (36.4%) | 3/7 (42.9%) | 0/0 (N/A) | 758.14 ms | 825.60 ms | PENDING |

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
| 0.0-0.5 | 5/10 | 50.0% |
| 0.5-0.7 | 1/1 | 100.0% |
| 0.7-0.9 | 0/0 | N/A |
| 0.9-1.0 | 0/0 | N/A |

### k = 3

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 4/11 | 36.4% |
| 0.5-0.7 | 0/0 | N/A |
| 0.7-0.9 | 0/0 | N/A |
| 0.9-1.0 | 0/0 | N/A |

### k = 5

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 4/11 | 36.4% |
| 0.5-0.7 | 0/0 | N/A |
| 0.7-0.9 | 0/0 | N/A |
| 0.9-1.0 | 0/0 | N/A |

## Ambiguous cases

Ambiguous cases are listed but excluded from every scored rate.

| k | ID | Raw choice | Final action | Confidence |
|---:|---|---|---|---:|
| 0 | r003 | SILENT | SILENT | 0.1763 |
| 0 | r012 | SILENT | SILENT | 0.3953 |
| 0 | r013 | SILENT | SILENT | 0.3356 |
| 0 | r014 | SILENT | SILENT | 0.3127 |
| 3 | r003 | SILENT | SILENT | 0.1763 |
| 3 | r012 | SILENT | SILENT | 0.2949 |
| 3 | r013 | REPLY | REPLY | 0.1411 |
| 3 | r014 | SILENT | SILENT | 0.2498 |
| 5 | r003 | SILENT | SILENT | 0.1763 |
| 5 | r012 | SILENT | SILENT | 0.2949 |
| 5 | r013 | REPLY | REPLY | 0.1411 |
| 5 | r014 | SILENT | SILENT | 0.2498 |

## Decision status

This report is evidence only. The project owner must record the final decision in `GO_NOGO.md`.
