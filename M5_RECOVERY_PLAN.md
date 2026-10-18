# M5 recovery and improvement plan

Status: **DATASET PREPARATION, LABELING INFRASTRUCTURE, AND DEVELOPMENT-ONLY TOOLING APPROVED**

Prepared: 2026-10-17

## Owner-authorized single-rater amendment

On 2026-10-17, the owner authorized a separate exploratory analysis using only
evaluator `a1`. This amendment does not replace the three-independent-evaluator
recovery design below. Single-rater labels may create a balanced,
family-isolated development set and local model evidence, but they cannot:

- establish inter-rater agreement or identify ambiguous cases;
- create a validated recovery held-out set;
- satisfy the dataset-quality gates in sections 5-7;
- reverse the original M5 NO-GO or support final M5 approval.

The untouched single-rater reserve must not be evaluated. The original held-out
bundle remains prohibited development material. No AWS or Bedrock use is
authorized by this amendment.

## 1. Non-negotiable evidence boundary

The original M5 result remains an immutable NO-GO. The following artifacts are
diagnostic evidence only and may never become development, prompt-tuning,
threshold-tuning, training, few-shot, or regression-assertion examples:

- `results/m5_heldout/20261017T053719Z/heldout_locked.jsonl`;
- all 45 raw predictions in `decider/20261017T053818Z/per_case.csv`;
- the saved metrics, manifest, configuration snapshot, acceptance record, and
  checksums in the same result bundle;
- the original frozen contract in `config/m5_frozen_evaluation.yaml`.

The original run remains: k=3, REPLY 0.20, REACT 0.04, model revision
`216d1ccb46a9e9b036eb9187b248db98480f77d4`, 45/45 predictions, zero errors,
66.7% accuracy, 66.7% unnecessary interruption, 16.7% missed help, and NO-GO.
No existing artifact will be overwritten, relabeled, rescored under a new
policy, or rerun.

Any recovery work must use newly written scenarios and new independent human
labels. The original held-out examples may inform only the high-level failure
taxonomy below; their wording, score values, and labels must not be copied into
development prompts or tests.

## 2. Read-only error audit of the nine unanimous k=3 cases

Six of nine unanimous cases were correct: four technical/direct REPLY cases,
one ordinary-discussion SILENT case, and one brief request-for-opinion REPLY
case. Three were wrong:

| ID | Human label | Raw choice | Confidence | Final action | Diagnosis |
|---|---|---|---:|---|---|
| c003 | REPLY | SILENT | 0.1663 | SILENT | Raw classification error. A direct named request was not recognized as requiring a response. The policy cannot promote SILENT, so thresholds cannot repair it. |
| c030 | SILENT | REPLY | 0.5526 | REPLY | Raw classification error. The immediately preceding context already contained the answer, but the model treated the repeated question as unanswered. A scalar threshold cannot safely isolate this high-confidence error. |
| c041 | SILENT | REACT | 0.0554 | REACT | Raw classification error exposed by the permissive REACT threshold. The model treated a routine reciprocal acknowledgment as reaction-worthy; the policy correctly passed the raw REACT because confidence exceeded 0.04. |

At k=3 there were zero policy downgrades. Therefore:

- **Model/wording classification mistakes:** all three incorrect final actions
  began as incorrect raw choices.
- **Threshold-caused mistakes:** none was created by downgrading a correct raw
  choice.
- **Threshold-sensitive mistake:** c041 could have been suppressed by a higher
  REACT threshold, but that observation is held-out evidence and cannot choose
  a new threshold.
- **Action-policy implementation mistakes:** none observed. The frozen policy
  behaved as specified.

Development-only evidence also explains why changing thresholds alone is not a
sound recovery. In the preserved development/calibration set, correct REACT
choices included confidence 0.0455 while the known false REACT was 0.0267; the
approved 0.04 threshold separated those tiny samples. Raising it above the
held-out 0.0554 value would already discard a genuine development REACT. For
REPLY, correct and false choices overlap substantially in confidence: there are
correct development replies below 0.21 and false replies above 0.62. A single
confidence cutoff cannot reliably replace semantic understanding of context.

## 3. What the original held-out sample can and cannot establish

The primary denominator was only nine unanimous cases: six REPLY, three SILENT,
and zero REACT. Six additional cases were AMBIGUOUS.

- With only three SILENT cases, every error changes unnecessary interruption by
  33.3 percentage points. The observed 2/3 is a serious failure under the
  registered gate, but a very imprecise estimate of deployment prevalence.
- With six REPLY cases, every miss changes missed help by 16.7 points.
- Overall accuracy changes by 11.1 points per unanimous case.
- With zero unanimous REACT cases, REACT recall is mathematically unavailable;
  this held-out set cannot validate whether useful reactions are recognized.
- REACT precision is 0/1, based on one scored prediction. It identifies an
  error but cannot estimate stable class precision.
- The 40% ambiguity rate (6/15) indicates that the labeling rubric and scenario
  composition need stronger pre-model validation.

These limitations do not reverse the NO-GO. They mean the next evaluation must
have pre-registered minimum denominators for every class and must not rely on
overall accuracy alone.

## 4. Development-only improvement program

No change is recommended yet. Candidate changes must be proposed, selected,
and measured only on a new development set.

### 4.1 Decision wording candidates

Test small, general wording variants that clarify principles already present in
the architecture:

1. **Direct unanswered help:** choose REPLY for an explicit request or question
   that still needs a response. If the requested information is unavailable,
   asking a concise clarifying question still counts as REPLY.
2. **Already answered:** inspect recent context before replying. If an adequate
   answer is already present, choose SILENT even when the newest message repeats
   the question or asks for confirmation.
3. **Valuable reaction:** reserve REACT for a meaningful acknowledgment of a
   concrete achievement, support, gratitude, or shared humor.
4. **Low-value reciprocity:** choose SILENT for routine conversational closure,
   reciprocal politeness, ordinary status updates, and acknowledgments where an
   emoji would add noise.

These are hypotheses, not approved wording. They must be tested on newly
authored scenario families that do not reuse or closely paraphrase original
held-out messages.

### 4.2 Threshold and action-policy candidates

- Keep 0.20/0.04 as the recovery baseline.
- Sweep candidate thresholds only on new development predictions.
- Report the complete tradeoff surface, including class raw counts; do not pick
  a threshold from one convenient error.
- Prefer wording improvements when confidence distributions overlap.
- If development evidence supports it, compare a conservative REACT threshold
  or a top-choice margin rule. Any new rule must remain general, fail closed to
  SILENT, and pass regression tests.
- Do not add message-specific keywords, scenario IDs, or deterministic overrides
  derived from the original held-out cases.
- Keep the model architecture and revision unchanged for the first recovery
  cycle. Model replacement or fine-tuning would require a separate plan.

### 4.3 Candidate-selection method

Evaluate the frozen baseline and each candidate on the same new development
set at k=0/3/5. Use grouped cross-validation so paraphrases and variants from
one scenario family never appear in both selection and validation folds. Select
the simplest candidate that meets every development gate and improves macro
class behavior; do not optimize a single aggregate metric. Preserve all losing
candidates and results to prevent selective reporting.

## 5. New independently labeled dataset

Recommended target: **150 new unanimously labeled scenarios** plus a separately
retained ambiguous pool.

- Development: 90 unanimous cases — 30 SILENT, 30 REACT, 30 REPLY.
- New held-out: 60 unanimous cases — 20 SILENT, 20 REACT, 20 REPLY.
- Generate approximately 180–210 candidates initially so disagreement does not
  prevent class quotas.
- Retain every non-unanimous case in an ambiguity audit; never silently discard
  it from dataset-quality reporting.

Scenario families should cover:

- SILENT: already-answered questions, routine updates, ordinary back-and-forth,
  scheduling, reciprocal thanks, rhetorical remarks, and resolved decisions;
- REACT: concrete milestones, gratitude worth acknowledging, supportive moments,
  clearly shared humor, and meaningful celebration;
- REPLY: explicit requests, unanswered technical questions, missing information,
  requests for judgment, and cases requiring clarification;
- boundaries: partial versus complete prior answers, mention without request,
  punctuation/no punctuation, short versus long history, subtle gratitude,
  humor versus routine chatter, and questions that should not be re-answered.

Three evaluators label every candidate independently as SILENT, REACT, or REPLY
using the revised rubric. They must not see intended classes, model outputs,
confidence, thresholds, other evaluators' answers, or split assignment. Ideally
at least one evaluator is new to the project. The labeling interface creates
separate exports and randomizes order per evaluator.

After labeling—but before any model prediction—perform a deterministic,
family-grouped, class-stratified split. All variants of one scenario family stay
in one split. Freeze the seed, scenario IDs, labels, source hashes, split
manifest, and evaluator-export hashes. If any class quota is short, author and
label additional candidates before splitting; never move cases after model
results exist.

Dataset-quality gates before model access:

- at least 30 unanimous development cases per class;
- at least 20 unanimous new-held-out cases per class;
- overall ambiguity rate reported, with a target at or below 20%;
- Fleiss' kappa reported, with a target of at least 0.60;
- zero scenario-family leakage across splits;
- duplicate and near-duplicate review completed;
- human sign-off on guidelines, quotas, split, and hashes.

## 6. Proposed recovery success criteria

These criteria must receive owner approval and be frozen before opening the new
held-out split. Recommended primary gates on the single pre-registered context:

- overall accuracy >=75%;
- unnecessary-interruption rate <=20% on at least 20 unanimous SILENT cases;
- missed-help rate <=25% on at least 20 unanimous REPLY cases;
- REACT precision >=70%;
- REACT recall >=70% on at least 20 unanimous REACT cases;
- exact prediction completeness, zero model errors, and zero mock rows;
- no threshold, wording, policy, context, or code change after unlock.

Latency p50/p95, calibration, per-class confusion, action counts, and ambiguous
predictions remain mandatory reports. A latency gate should be added only if
the target hardware and warm-up treatment are frozen in advance; it must not be
invented after results are visible.

The new held-out result stands alone. It does not erase or supersede the
original NO-GO, which remains part of the final report and hackathon narrative.

## 7. Freeze and one-time evaluation procedure

Before the new held-out split can be accessed:

1. Complete all scenario authoring and blind labeling.
2. Pass dataset-quality gates and freeze the grouped split.
3. Finish all wording, threshold, context, and action-policy selection using
   only the new development split.
4. Freeze exact model revision, prompt text, options, context, thresholds,
   policy code, metric code, criteria, dependency versions, hardware target,
   and all relevant SHA-256 hashes.
5. Record the primary context and whether comparison contexts will run. Only
   the primary context controls PASS/FAIL.
6. Prove the development loader cannot open the new held-out file.
7. Run dataset-isolation, metric, policy, completeness, no-overwrite, no-mock,
   and one-time-unlock tests.
8. Obtain explicit owner authorization for exactly one new held-out evaluation.
9. Evaluate once. If any gate fails, preserve the result and stop; no hidden
   rerun or post-hoc threshold change.

The new evidence must use a new result root and publication ID. The original
`results/m5_heldout/20261017T053719Z/` directory remains untouched.

## 8. Testing requirements

Minimum verification before a new freeze:

- all existing 89 offline tests continue to pass;
- unit tests for every revised wording/policy boundary using synthetic or new
  development fixtures only;
- hand-computed metric tests for accuracy, interruption, missed help, REACT
  precision/recall, empty denominators, and ambiguous exclusion;
- dataset tests for exact class quotas, three complete label exports, unique
  IDs, family grouping, deterministic split, and no near-duplicate leakage;
- guard tests proving development commands cannot open either old or new
  held-out sources;
- checksum tests proving the original NO-GO evidence is unchanged;
- threshold sweeps that accept development rows only;
- real local Decider development evaluation with raw predictions and resource
  evidence;
- one dry run using synthetic fixtures to prove one-time output collision and
  publication refusal behavior;
- manual review of the final freeze manifest before owner approval.

No AWS or Bedrock work is necessary for dataset creation, labeling, local model
selection, or the new local held-out evaluation. Deployment and judge baselines
remain separate approvals.

## 9. Estimated time and cost

| Work | Estimated effort | Direct service cost |
|---|---:|---:|
| Guidelines and scenario-family design | 2–3 hours | $0 |
| Author/review 180–210 candidates | 3–5 hours | $0 |
| Three blind labeling passes | 1.5–2 hours per evaluator | $0 with volunteers |
| Merge, agreement analysis, quota completion, split | 1–2 hours | $0 |
| Wording/threshold experiments on development data | 3–5 hours | $0 local |
| Tests, freeze manifest, audit review | 2–3 hours | $0 |
| One new local held-out run and report | 1–2 hours | $0 |

Expected total: roughly **12–20 person-hours over 2–3 calendar days**, depending
on evaluator availability and disagreement. Local compute should take minutes,
not hours, and incur no cloud charge. Paid evaluators, if used, are the only
unpriced human cost.

An optional later controlled AWS deployment would require separate approval.
Based on the prior accepted m7i.2xlarge rate, a 10–15 minute window would be
roughly $0.07–$0.10 in EC2 compute plus small storage/IPv4 charges. Bedrock judge
cost is excluded until a model, call cap, and current price are separately
approved.

## 10. Authorization boundary

The approved scope covers only the new dataset/guideline, labeling
infrastructure, and development-evaluation tooling. It does not authorize a new
held-out run, AWS deployment, Bedrock call, model replacement, or changes to
the preserved original evidence.

## 11. Approval record

On 2026-10-17, the project owner approved candidate preparation, three blind
labeling workflows, family-grouped split tooling, and development-only
evaluation tooling. This approval does not authorize collecting labels on
behalf of humans, evaluating the new held-out split, changing production
configuration, calling AWS or Bedrock, or reversing the original M5 NO-GO.
