# Lurker AI evaluation report

- Generated: 2026-10-16T06:45:23.990736+00:00
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
| 0 | 20 | 10 | 16/20 (80.0%) | 3/10 (30.0%) | 1/10 (10.0%) | 524.70 ms | 569.48 ms | PENDING |
| 3 | 20 | 10 | 15/20 (75.0%) | 5/10 (50.0%) | 0/10 (0.0%) | 554.66 ms | 642.61 ms | PENDING |
| 5 | 20 | 10 | 15/20 (75.0%) | 5/10 (50.0%) | 0/10 (0.0%) | 579.51 ms | 1050.52 ms | PENDING |

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
| 0.0-0.5 | 3/6 | 50.0% |
| 0.5-0.7 | 10/11 | 90.9% |
| 0.7-0.9 | 3/3 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

### k = 3

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 5/8 | 62.5% |
| 0.5-0.7 | 7/9 | 77.8% |
| 0.7-0.9 | 3/3 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

### k = 5

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 5/8 | 62.5% |
| 0.5-0.7 | 7/9 | 77.8% |
| 0.7-0.9 | 3/3 | 100.0% |
| 0.9-1.0 | 0/0 | N/A |

## Ambiguous cases

Ambiguous cases are listed but excluded from every scored rate.

| k | ID | Raw choice | Final action | Confidence |
|---:|---|---|---|---:|
| 0 | c007 | SILENT | SILENT | 0.3757 |
| 0 | c009 | SILENT | SILENT | 0.2480 |
| 0 | c020 | SILENT | SILENT | 0.3561 |
| 0 | c026 | REPLY | REPLY | 0.5456 |
| 0 | c031 | REPLY | REPLY | 0.4806 |
| 0 | c033 | SILENT | SILENT | 0.4366 |
| 0 | c034 | SILENT | SILENT | 0.5299 |
| 0 | c037 | SILENT | SILENT | 0.1626 |
| 0 | c039 | REACT | REACT | 0.2114 |
| 0 | c043 | SILENT | SILENT | 0.4732 |
| 3 | c007 | SILENT | SILENT | 0.3757 |
| 3 | c009 | SILENT | SILENT | 0.2480 |
| 3 | c020 | SILENT | SILENT | 0.2280 |
| 3 | c026 | REPLY | REPLY | 0.6711 |
| 3 | c031 | REPLY | REPLY | 0.5630 |
| 3 | c033 | SILENT | SILENT | 0.4366 |
| 3 | c034 | SILENT | SILENT | 0.6195 |
| 3 | c037 | SILENT | SILENT | 0.1626 |
| 3 | c039 | REACT | REACT | 0.1854 |
| 3 | c043 | SILENT | SILENT | 0.2992 |
| 5 | c007 | SILENT | SILENT | 0.3757 |
| 5 | c009 | SILENT | SILENT | 0.2480 |
| 5 | c020 | SILENT | SILENT | 0.2280 |
| 5 | c026 | REPLY | REPLY | 0.6711 |
| 5 | c031 | REPLY | REPLY | 0.5630 |
| 5 | c033 | SILENT | SILENT | 0.4366 |
| 5 | c034 | SILENT | SILENT | 0.6195 |
| 5 | c037 | SILENT | SILENT | 0.1626 |
| 5 | c039 | REACT | REACT | 0.1854 |
| 5 | c043 | SILENT | SILENT | 0.2992 |

## Decision status

This report is evidence only. The project owner must record the final decision in `GO_NOGO.md`.
