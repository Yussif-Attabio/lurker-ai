# Go / no-go decision

The success criteria below were approved by the project owner before the first
real M1 evaluation. Three genuine human label files and the separate REACT
calibration labels have been merged, and the real tuning evidence has been
reviewed. On 2026-10-16, the project owner approved M1 as a provisional GO.

- Accuracy: **at least 70%**
- Unnecessary-interruption rate: **at most 20%**
- Missed-help rate: **at most 25%**
- Decision: **PROVISIONAL GO**
- Approval scope: proceed to M2; this is not production-readiness approval
- Provisional context: **k = 3**
- Provisional reply threshold: **0.20**
- Provisional REACT threshold: **0.04**
- Primary evidence: `results/react_wording/anchored_final/`
- Rollback configuration: `config/default.pre_m1_provisional.yaml`

## Initial evaluation baseline (historical)

- Human agreement: 29/45 unanimous (64.44%); 16/45 `AMBIGUOUS`.
- Tuning set: 30 total; 20 scored (10 `SILENT`, 10 `REPLY`) and 10 ambiguous.
- Real Decider predictions: 90 across context k = 0, 3, and 5; zero model errors.
- Recommended context: k = 3.
- Candidate reply threshold: 0.40, selected from the tied 0.20-0.40 range
  using the quieter threshold as the tie-break.
- Candidate react threshold: 1.00 as a conservative fallback. The tuning set
  has no unanimous `REACT` labels and no scored raw `REACT` choices, so this
  threshold is not empirically identifiable from the current data.
- Candidate k = 3 results: accuracy 17/20 (85%); unnecessary interruptions
  2/10 (20%); missed help 1/10 (10%). All approved numeric criteria pass.
- Label-quality limitation: no `REACT` class is represented in the scored
  consensus set, and overall unanimity is 64.44%.

This evidence is preserved as the initial baseline. It was superseded by the
separate calibration and wording-improvement evidence below. Do not evaluate
the held-out split before M5.

## REACT calibration baseline (historical)

- Separate calibration labels: 11/15 unanimous (73.33%); 4/15 `AMBIGUOUS`.
- Unanimous calibration consensus: 4 `REACT`, 7 `SILENT`, and 0 `REPLY`.
- Calibration Decider run: 45 predictions across context k = 0, 3, and 5;
  zero model errors.
- Combined k = 3 tuning evidence: 45 total scenarios; 31 scored
  (17 `SILENT`, 4 `REACT`, 10 `REPLY`) and 14 ambiguous.
- Updated candidate thresholds: reply 0.40 and react 0.05.
- Updated candidate k = 3 metrics: accuracy 25/31 (80.6%); unnecessary
  interruptions 2/17 (11.8%); missed help 1/10 (10.0%). All three approved
  overall numeric criteria pass.
- REACT-class limitation: only 1/4 unanimous `REACT` cases was predicted as
  `REACT`, for 25% recall. The other three were raw `SILENT` choices, so a
  confidence threshold cannot recover them. Scored REACT precision is 1/1.
- Evidence directory: `results/react_calibration/20261016T062854Z/`.
- This calibration exposed low observed REACT recall and led to the approved
  wording-improvement pass below.

The calibration merge and analysis are separate from the original held-out
dataset and original result directory. At the time of this historical run,
production thresholds remained unchanged.

## Approved provisional M1 baseline

- The shared decision wording was revised using general action boundaries; no
  evaluation examples or IDs were embedded in the question.
- Architecture and model are unchanged. The same local CPU Decider produced 90
  original-tuning and 45 calibration predictions across k = 0, 3, and 5.
- Approved provisional k = 3 thresholds from the fine-grained tuning-only
  sweep: reply 0.20 and react 0.04. They are recorded in
  `config/default.yaml`; the prior null-threshold file is preserved for rollback.
- Before versus after: accuracy 80.6% to 83.9%; REACT precision 100% to 100%;
  REACT recall 25% to 75%; unnecessary interruptions 11.8% to 17.6%; missed
  help remains 10%.
- Ordinary-conversation check: false emoji reactions on unanimous SILENT cases
  remain 0/17. The one additional interruption is a false REPLY, not a REACT.
- All approved criteria pass, but interruption headroom is small (3/17 versus
  a maximum of 20%) and the REACT sample contains only four unanimous cases.
- Evidence: `results/react_wording/anchored_final/analysis/20261016T064604Z/`
  and `results/react_wording/anchored_final/comparison/`.

### Remaining limitations accepted for provisional continuation

- Only 31 of 45 combined tuning/calibration cases are scored; 14 are ambiguous.
- The unanimous REACT sample contains only four cases. Candidate REACT recall is
  3/4 (75%), so one genuine REACT case is still missed.
- Unnecessary interruption is 3/17 (17.6%), leaving one-case headroom below the
  approved 20% ceiling. The added interruption is a false REPLY, not a false
  emoji reaction.
- The REACT threshold is based on a narrow observed separation: the lowest
  retained correct REACT confidence is 0.0455, while the scored false REACT is
  0.0267. More labeled REACT evidence is needed before production use.
- Evaluation uses synthetic chat scenarios and a local CPU environment. It does
  not establish deployed latency, reliability, security, load capacity, or
  production behavior.
- The held-out dataset remains untouched until M5. M2-M4 work must not use it.
- The M2 end-to-end WebSocket acceptance check still must demonstrate SILENT,
  REACT, and REPLY, including one real Bedrock-generated reply.

### Owner decision - 2026-10-16

**PROVISIONAL GO.** M1 is accepted for the purpose of continuing to M2 with
context k = 3, reply threshold 0.20, and REACT threshold 0.04. This decision is
not production-readiness approval. No paid AWS resources may be launched, and
any billable M2 Bedrock acceptance invocation requires a separate explicit
approval before it is run. Historical configurations and results must remain
available for comparison and rollback.
