# Lurker AI evaluation report

- Generated: 2026-10-16T05:49:27.932766+00:00
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
| 0 | 20 | 10 | 16/20 (80.0%) | 3/10 (30.0%) | 1/10 (10.0%) | 463.49 ms | 493.28 ms | PENDING |
| 3 | 20 | 10 | 15/20 (75.0%) | 5/10 (50.0%) | 0/10 (0.0%) | 521.69 ms | 583.05 ms | PENDING |
| 5 | 20 | 10 | 15/20 (75.0%) | 5/10 (50.0%) | 0/10 (0.0%) | 527.13 ms | 1369.31 ms | PENDING |

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
| 0.0-0.5 | 7/9 | 77.8% |
| 0.5-0.7 | 4/6 | 66.7% |
| 0.7-0.9 | 5/5 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

### k = 3

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 8/11 | 72.7% |
| 0.5-0.7 | 3/5 | 60.0% |
| 0.7-0.9 | 4/4 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

### k = 5

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 8/11 | 72.7% |
| 0.5-0.7 | 3/5 | 60.0% |
| 0.7-0.9 | 4/4 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

## Ambiguous cases

Ambiguous cases are listed but excluded from every scored rate.

| k | ID | Raw choice | Final action | Confidence |
|---:|---|---|---|---:|
| 0 | c007 | SILENT | SILENT | 0.3767 |
| 0 | c009 | SILENT | SILENT | 0.1027 |
| 0 | c020 | SILENT | SILENT | 0.2666 |
| 0 | c026 | REPLY | REPLY | 0.6113 |
| 0 | c031 | REPLY | REPLY | 0.5524 |
| 0 | c033 | SILENT | SILENT | 0.4274 |
| 0 | c034 | SILENT | SILENT | 0.6093 |
| 0 | c037 | SILENT | SILENT | 0.1869 |
| 0 | c039 | SILENT | SILENT | 0.2021 |
| 0 | c043 | SILENT | SILENT | 0.6093 |
| 3 | c007 | SILENT | SILENT | 0.3767 |
| 3 | c009 | SILENT | SILENT | 0.1027 |
| 3 | c020 | REPLY | REPLY | 0.0377 |
| 3 | c026 | REPLY | REPLY | 0.6596 |
| 3 | c031 | REPLY | REPLY | 0.5055 |
| 3 | c033 | SILENT | SILENT | 0.4274 |
| 3 | c034 | SILENT | SILENT | 0.6892 |
| 3 | c037 | SILENT | SILENT | 0.1869 |
| 3 | c039 | REACT | REACT | 0.1615 |
| 3 | c043 | SILENT | SILENT | 0.1276 |
| 5 | c007 | SILENT | SILENT | 0.3767 |
| 5 | c009 | SILENT | SILENT | 0.1027 |
| 5 | c020 | REPLY | REPLY | 0.0377 |
| 5 | c026 | REPLY | REPLY | 0.6596 |
| 5 | c031 | REPLY | REPLY | 0.5055 |
| 5 | c033 | SILENT | SILENT | 0.4274 |
| 5 | c034 | SILENT | SILENT | 0.6892 |
| 5 | c037 | SILENT | SILENT | 0.1869 |
| 5 | c039 | REACT | REACT | 0.1615 |
| 5 | c043 | SILENT | SILENT | 0.1276 |

## Decision status

This report is evidence only. The project owner must record the final decision in `GO_NOGO.md`.
