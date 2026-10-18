# Lurker AI evaluation report

- Generated: 2026-10-16T06:37:35.537614+00:00
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
| 0 | 20 | 10 | 16/20 (80.0%) | 3/10 (30.0%) | 1/10 (10.0%) | 651.22 ms | 1105.89 ms | PENDING |
| 3 | 20 | 10 | 15/20 (75.0%) | 5/10 (50.0%) | 0/10 (0.0%) | 710.14 ms | 1469.63 ms | PENDING |
| 5 | 20 | 10 | 15/20 (75.0%) | 5/10 (50.0%) | 0/10 (0.0%) | 673.76 ms | 738.94 ms | PENDING |

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
| 0.0-0.5 | 6/7 | 85.7% |
| 0.5-0.7 | 4/7 | 57.1% |
| 0.7-0.9 | 6/6 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

### k = 3

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 6/9 | 66.7% |
| 0.5-0.7 | 4/6 | 66.7% |
| 0.7-0.9 | 5/5 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

### k = 5

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 6/9 | 66.7% |
| 0.5-0.7 | 4/6 | 66.7% |
| 0.7-0.9 | 5/5 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

## Ambiguous cases

Ambiguous cases are listed but excluded from every scored rate.

| k | ID | Raw choice | Final action | Confidence |
|---:|---|---|---|---:|
| 0 | c007 | SILENT | SILENT | 0.2888 |
| 0 | c009 | SILENT | SILENT | 0.1610 |
| 0 | c020 | REPLY | REPLY | 0.1500 |
| 0 | c026 | REPLY | REPLY | 0.6421 |
| 0 | c031 | REPLY | REPLY | 0.7152 |
| 0 | c033 | SILENT | SILENT | 0.3638 |
| 0 | c034 | SILENT | SILENT | 0.5681 |
| 0 | c037 | REPLY | REPLY | 0.0834 |
| 0 | c039 | REACT | REACT | 0.0880 |
| 0 | c043 | SILENT | SILENT | 0.4821 |
| 3 | c007 | SILENT | SILENT | 0.2888 |
| 3 | c009 | SILENT | SILENT | 0.1610 |
| 3 | c020 | REPLY | REPLY | 0.2136 |
| 3 | c026 | REPLY | REPLY | 0.7161 |
| 3 | c031 | REPLY | REPLY | 0.5980 |
| 3 | c033 | SILENT | SILENT | 0.3638 |
| 3 | c034 | SILENT | SILENT | 0.7084 |
| 3 | c037 | REPLY | REPLY | 0.0834 |
| 3 | c039 | REPLY | REPLY | 0.1431 |
| 3 | c043 | SILENT | SILENT | 0.2492 |
| 5 | c007 | SILENT | SILENT | 0.2888 |
| 5 | c009 | SILENT | SILENT | 0.1610 |
| 5 | c020 | REPLY | REPLY | 0.2136 |
| 5 | c026 | REPLY | REPLY | 0.7161 |
| 5 | c031 | REPLY | REPLY | 0.5980 |
| 5 | c033 | SILENT | SILENT | 0.3638 |
| 5 | c034 | SILENT | SILENT | 0.7084 |
| 5 | c037 | REPLY | REPLY | 0.0834 |
| 5 | c039 | REPLY | REPLY | 0.1431 |
| 5 | c043 | SILENT | SILENT | 0.2492 |

## Decision status

This report is evidence only. The project owner must record the final decision in `GO_NOGO.md`.
