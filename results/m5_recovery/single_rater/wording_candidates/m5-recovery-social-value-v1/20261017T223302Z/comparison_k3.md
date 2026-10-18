# Single-evaluator wording comparison

> Development-only evidence. Not human consensus, held-out evidence, or production approval.

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| Accuracy | 71.1% | 71.1% | +0.0 pp |
| Unnecessary interruption | 30.0% | 16.7% | -13.3 pp |
| Missed help | 3.3% | 3.3% | +0.0 pp |
| REACT precision | 70.0% | 66.7% | -3.3 pp |
| REACT recall | 46.7% | 33.3% | -13.3 pp |
| Latency p50 | 581.54 ms | 848.25 ms | +266.71 ms |
| Latency p95 | 1100.80 ms | 1605.11 ms | +504.31 ms |

## Regression checks

- new unnecessary reacts: 4
- repaired unnecessary reacts: 5
- new missed requests: 0
- repaired missed requests: 0
- new correct reacts: 2
- lost correct reacts: 6

All development review gates met: **FALSE**

Production wording, thresholds, and policy remain unchanged.
