# M5 final acceptance candidate

Status: **TECHNICALLY COMPLETE / MODEL PERFORMANCE NO-GO**

This report publishes only recorded evidence. It does not rerun held-out data, invoke Bedrock, open the protected reserve, or claim production readiness.

## Frozen original configuration

- Context: k=3
- REPLY threshold: 0.20
- REACT threshold: 0.04
- Model: `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610`
- Revision: `216d1ccb46a9e9b036eb9187b248db98480f77d4`
- Original decision wording and action policy: unchanged

## Original one-time held-out result

| Metric | Result | Acceptance |
|---|---:|---:|
| Accuracy | 6/9 (66.7%) | FAIL (requires >=70%) |
| Unnecessary interruption | 2/3 (66.7%) | FAIL (requires <=20%) |
| Missed help | 1/6 (16.7%) | PASS (requires <=25%) |
| REACT precision | 0/1 (0.0%) | report only |
| REACT recall | 0/0 (N/A) | unavailable: no unanimous REACT cases |
| Latency p50 / p95 | 598.81 / 682.34 ms | report only |

The held-out result remains NO-GO and was not rerun or modified.

## Baseline status

The free question-mark rule was run once on the same 15 held-out cases. It did not invoke a model or modify the frozen Decider result.

| Baseline | Scope | Accuracy | Interruption | Missed help | Calls |
|---|---|---:|---:|---:|---:|
| Question-mark rule | held-out | 6/9 (66.7%) | 1/3 (33.3%) | 2/6 (33.3%) | 0 |
| Bedrock judge | held-out | Not run | Not run | Not run | 0 |

The strict build specification now lacks only the held-out Bedrock judge. Completing it requires separate permission for up to 15 paid calls.

## Implementation and pipeline evidence

- Context comparison k=0/3/5: complete
- Threshold tuning and frozen configuration: complete
- One-time held-out Decider run: complete, NO-GO
- SILENT / REACT / REPLY real WebSocket pipeline: previously passed
- SILENT and REACT avoided Bedrock; REPLY invoked Bedrock exactly once
- Evaluation tab: publishes this real-evidence NO-GO closure candidate
- Bedrock judge held-out baseline: not run, separate approval required

## Acceptance distinction

- **Implementation completion:** technically complete by owner approval, with documented limitations.
- **Model-performance acceptance:** NO-GO.
- **Strict original M5 checklist:** incomplete because the Bedrock held-out baseline is absent.
- **Production readiness:** not approved.

M5 is technically closed with a performance NO-GO and explicit Bedrock-baseline deviation. This is not model-performance or production approval.
