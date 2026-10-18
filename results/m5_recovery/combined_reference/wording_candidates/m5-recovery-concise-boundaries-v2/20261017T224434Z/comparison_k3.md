# Combined three-contributor reference: wording comparison

> Development-only. The three contributors' individual decisions were not retained, so independence, consensus, and inter-rater agreement cannot be verified.

| Metric | Original wording | Concise v2 | Delta |
|---|---:|---:|---:|
| Accuracy | 71.1% | 54.4% | -16.7 pp |
| Unnecessary interruption | 30.0% | 0.0% | -30.0 pp |
| Missed help | 3.3% | 36.7% | +33.3 pp |
| REACT precision | 70.0% | N/A | N/A |
| REACT recall | 46.7% | 0.0% | -46.7 pp |
| Latency p50 | 581.54 ms | 578.22 ms | -3.31 ms |
| Latency p95 | 1100.80 ms | 1519.69 ms | +418.89 ms |

## Safety and regression checks

- new unnecessary interruptions: 0
- repaired unnecessary interruptions: 9
- new unnecessary reacts: 0
- repaired unnecessary reacts: 6
- new missed requests: 10
- repaired missed requests: 0
- new correct reacts: 0
- lost correct reacts: 14

All development review gates met: **FALSE**

Production wording, thresholds, model, and action policy remain unchanged.
