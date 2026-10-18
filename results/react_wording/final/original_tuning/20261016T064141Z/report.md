# Lurker AI evaluation report

- Generated: 2026-10-16T06:41:41.151892+00:00
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
| 0 | 20 | 10 | 16/20 (80.0%) | 4/10 (40.0%) | 0/10 (0.0%) | 470.96 ms | 511.17 ms | PENDING |
| 3 | 20 | 10 | 14/20 (70.0%) | 6/10 (60.0%) | 0/10 (0.0%) | 529.37 ms | 590.41 ms | PENDING |
| 5 | 20 | 10 | 14/20 (70.0%) | 6/10 (60.0%) | 0/10 (0.0%) | 529.47 ms | 589.45 ms | PENDING |

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
| 0.5-0.7 | 3/6 | 50.0% |
| 0.7-0.9 | 7/7 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

### k = 3

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 5/7 | 71.4% |
| 0.5-0.7 | 3/5 | 60.0% |
| 0.7-0.9 | 6/8 | 75.0% |
| 0.9-1.0 | 0/0 | N/A |

### k = 5

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 5/7 | 71.4% |
| 0.5-0.7 | 3/5 | 60.0% |
| 0.7-0.9 | 6/8 | 75.0% |
| 0.9-1.0 | 0/0 | N/A |

## Ambiguous cases

Ambiguous cases are listed but excluded from every scored rate.

| k | ID | Raw choice | Final action | Confidence |
|---:|---|---|---|---:|
| 0 | c007 | SILENT | SILENT | 0.3845 |
| 0 | c009 | SILENT | SILENT | 0.1475 |
| 0 | c020 | REPLY | REPLY | 0.3355 |
| 0 | c026 | REPLY | REPLY | 0.6962 |
| 0 | c031 | REPLY | REPLY | 0.7661 |
| 0 | c033 | SILENT | SILENT | 0.3643 |
| 0 | c034 | SILENT | SILENT | 0.3747 |
| 0 | c037 | REPLY | REPLY | 0.4136 |
| 0 | c039 | REPLY | REPLY | 0.1670 |
| 0 | c043 | SILENT | SILENT | 0.4010 |
| 3 | c007 | SILENT | SILENT | 0.3845 |
| 3 | c009 | SILENT | SILENT | 0.1475 |
| 3 | c020 | REPLY | REPLY | 0.3368 |
| 3 | c026 | REPLY | REPLY | 0.7943 |
| 3 | c031 | REPLY | REPLY | 0.7079 |
| 3 | c033 | SILENT | SILENT | 0.3643 |
| 3 | c034 | SILENT | SILENT | 0.7018 |
| 3 | c037 | REPLY | REPLY | 0.4136 |
| 3 | c039 | REACT | REACT | 0.2021 |
| 3 | c043 | REPLY | REPLY | 0.1450 |
| 5 | c007 | SILENT | SILENT | 0.3845 |
| 5 | c009 | SILENT | SILENT | 0.1475 |
| 5 | c020 | REPLY | REPLY | 0.3368 |
| 5 | c026 | REPLY | REPLY | 0.7943 |
| 5 | c031 | REPLY | REPLY | 0.7079 |
| 5 | c033 | SILENT | SILENT | 0.3643 |
| 5 | c034 | SILENT | SILENT | 0.7018 |
| 5 | c037 | REPLY | REPLY | 0.4136 |
| 5 | c039 | REACT | REACT | 0.2021 |
| 5 | c043 | REPLY | REPLY | 0.1450 |

## Decision status

This report is evidence only. The project owner must record the final decision in `GO_NOGO.md`.
