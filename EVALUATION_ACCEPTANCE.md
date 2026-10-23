# Evaluation acceptance report

Status: **TECHNICALLY COMPLETE / MODEL PERFORMANCE NO-GO**

The project owner approved technical closure on 2026-10-18 with the documented
performance NO-GO and Bedrock-baseline deviation. This approval does not accept
the model's performance and is not production-readiness approval.

This report distinguishes implementation completion from model-performance
acceptance. It uses recorded evidence only. No held-out evaluation was rerun,
no protected reserve scenario was opened, no AWS resource was launched, no
Bedrock call was made, and M6 was not started.

## Frozen configuration

- Context: k=3
- REPLY threshold: 0.20
- REACT threshold: 0.04
- Model: `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610`
- Revision: `216d1ccb46a9e9b036eb9187b248db98480f77d4`
- Original decision wording, model architecture, context builder, and action
  policy: unchanged

Frozen checksums remain unchanged:

- `config/default.yaml`: `7e36315af0cd8c389493a711b1b30cf9ca5ddee07b98ab42503a5a9d15e1b832`
- `decision_pattern/lurker_gate.py`: `f3318f1ee95a661c720b1f6c770c926a3a1f8f7688e6b83f3825803dfb699a2b`
- `scripts/run_eval.py`: `efa7a8107f322e045ab03ee686ebfe78d7289b89158134e5a2819095aa87724a`

## Original held-out result

The original one-time held-out result is preserved without a rerun or
modification.

| Metric | Result | Gate |
|---|---:|---:|
| Accuracy | 6/9 (66.7%) | FAIL: requires >=70% |
| Unnecessary interruption | 2/3 (66.7%) | FAIL: requires <=20% |
| Missed help | 1/6 (16.7%) | PASS: requires <=25% |
| REACT precision | 0/1 (0.0%) | report only |
| REACT recall | 0/0 (N/A) | unavailable |
| Latency p50 / p95 | 598.81 / 682.34 ms | report only |

Only nine cases were unanimous and scored: three SILENT, zero REACT, and six
REPLY. Six additional cases were AMBIGUOUS. With no unanimous REACT case,
held-out REACT recall cannot be measured. The governing model-performance
decision remains **NO-GO**.

## Supplementary combined reference

Three people contributed to one combined 195-label document, but individual
answers and the aggregation process were not retained. Independence,
unanimity/group consensus, ambiguity, and inter-rater agreement cannot be
verified. The existing 90 development scenarios remain separate from the 105
protected reserve scenarios.

The original k=3 Decider result on the accessible 90-case reference is 71.1%
accuracy, 30.0% unnecessary interruption, 3.3% missed help, 70.0% REACT
precision, and 46.7% REACT recall. This is supplementary development evidence,
not held-out acceptance evidence.

## Question-mark baseline

The free question-mark baseline was completed locally on the same 15 held-out
cases. It did not invoke the Decider, AWS, or Bedrock and did not modify or
rerun the frozen Decider evaluation:

| Metric | Result |
|---|---:|
| Accuracy | 6/9 (66.7%) |
| Unnecessary interruption | 1/3 (33.3%) |
| Missed help | 2/6 (33.3%) |
| REACT precision | 0/0 (N/A) |
| REACT recall | 0/0 (N/A) |
| Model/AWS/Bedrock calls | 0 |

This confirms that punctuation alone is a weak decision baseline. The run
satisfies the free held-out baseline item while preserving the original
Decider predictions and acceptance record.

## Real pipeline evidence

Existing M2 real-service evidence is sufficient to verify all three actions:

- SILENT: real Decider, no Bedrock call;
- REACT: real Decider, no Bedrock call;
- REPLY: real Decider, exactly one Claude Haiku 4.5 call;
- observed Bedrock usage: 159 input tokens, 32 output tokens, 1,072.45 ms;
- pipeline errors: zero.

No additional paid pipeline run is necessary for M5 technical closure.

## Evaluation tab and verification

`results/published.json` now publishes an explicit real-evidence closure
artifact. The Evaluation tab displays:

- `PUBLISHED NO-GO` and primary `FAIL`;
- k=0/3/5 held-out metrics with raw counts;
- missing held-out REACT recall;
- the held-out question-mark baseline;
- `Bedrock judge: Not run` rather than fabricated metrics;
- the technical-closure, strict-spec, and production-readiness limitations.

Browser acceptance at 1280x900 passed: the loading state is hidden after load,
the evidence view is visible, all three context rows and all three baseline
status rows render, and there are zero console errors. The local acceptance
server used MockDecider only to host the frontend; the displayed evaluation
numbers came exclusively from recorded real-run artifacts.

Regression verification: 104 safe offline tests passed, JavaScript syntax
passed, and one legacy audit was deliberately deselected because it opens the
original held-out file to hash it. The protected reserve and held-out scenario
contents were not accessed by finalization.

## Bedrock judge: necessity and cost

Paid Bedrock calls are **not necessary** to close M5 as a technical
implementation with a documented performance NO-GO and explicit spec
deviation. They **are necessary** to satisfy the original M5 requirement for
both held-out baselines.

The prepared strict-spec run would use:

- Region: `us-east-2`
- Model: `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- Maximum calls: 15, no retries
- Maximum output: 8 tokens per call
- Maximum prompt: 1,000 UTF-8 bytes per call; oversized prompts fail before invocation
- Regional price used for the cap: $1.10 per million input tokens and $5.50 per
  million output tokens
- Pricing source: `https://aws.amazon.com/jp/blogs/news/amazon-bedrock-now-supports-japan-cross-region-inference/`
- Charge formula: `input_tokens * 1.10 / 1,000,000 + output_tokens * 5.50 / 1,000,000`
- Conservative maximum inference charge: **$0.01716**
- Expected charge with prompts similar to the verified 159-token pipeline call:
  approximately **$0.0033**
- EC2/infrastructure charge: **$0.00**; the baseline runs locally

Actual billing is token-based and can only be known after AWS returns usage.
No call will be made without separate owner approval.

## Final acceptance distinction

- **Implementation completion:** technically complete by owner approval.
- **Model-performance acceptance:** NO-GO.
- **Strict original M5 checklist:** incomplete only because the Bedrock judge
  baseline was not run on the original held-out set.
- **Production readiness:** not approved.

M5 is closed as **TECHNICALLY COMPLETED WITH DOCUMENTED PERFORMANCE NO-GO AND
BEDROCK-BASELINE DEVIATION**. The model did not pass evaluation. A future
Bedrock judge run would satisfy the remaining strict checklist item but is not
authorized or required for this technical closure.
