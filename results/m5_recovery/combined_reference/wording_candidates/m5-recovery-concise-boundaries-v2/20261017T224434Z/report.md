# Combined-reference wording candidate: m5-recovery-concise-boundaries-v2

> Development-only. Three people contributed to one final-label document, but independence, consensus, and inter-rater agreement cannot be verified. This is not held-out evidence or production approval.

- Generated: 2026-10-17T22:44:34.137666+00:00
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
| 3 | 90 | 0 | 0 | 49/90 (54.4%) | 0/30 (0.0%) | 11/30 (36.7%) | 578.22 ms | 1519.69 ms | FAIL |

## Low-confidence handling

### k = 3

- Downgraded: 8
- Accuracy before downgrade: 8/8 (100.0%)
- Accuracy after downgrade: 0/8 (0.0%)

## Calibration

### k = 3

| Confidence bin | Correct / count | Accuracy |
|---|---:|---:|
| 0.0-0.5 | 28/50 | 56.0% |
| 0.5-0.7 | 18/36 | 50.0% |
| 0.7-0.9 | 3/4 | 75.0% |
| 0.9-1.0 | 0/0 | N/A |

## Ambiguous cases

No human-ambiguous cases were present in this split.

## Decision status

This report is evidence only. The project owner must record the final decision in `GO_NOGO.md`.
