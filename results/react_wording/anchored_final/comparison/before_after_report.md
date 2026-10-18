# Decider REACT wording comparison

This comparison uses genuine unanimous labels and real local-Decider predictions from the original tuning and separate REACT calibration sets at k=3. It excludes held-out scenarios and does not modify production thresholds.

| Metric | Baseline | Candidate |
|---|---:|---:|
| Accuracy | 25/31 (80.6%) | 26/31 (83.9%) |
| REACT precision | 100.0% | 100.0% |
| REACT recall | 25.0% | 75.0% |
| Unnecessary interruption | 2/17 (11.8%) | 3/17 (17.6%) |
| Missed help | 1/10 (10.0%) | 1/10 (10.0%) |

## Ordinary-conversation safety

- Baseline: 15/17 consensus-SILENT cases remained SILENT; false REACT=0, false REPLY=2.
- Candidate: 14/17 consensus-SILENT cases remained SILENT; false REACT=0, false REPLY=3.
- The candidate does not add a false emoji reaction on consensus-SILENT cases at its candidate thresholds. Its one extra interruption is a REPLY, not a REACT.

## Candidate thresholds (not production configuration)

- reply_threshold=0.20
- react_threshold=0.04
- Human approval remains required before copying either value into config/default.yaml.

## Status

PROVISIONAL GO recommendation for final M1 approval, with the small-sample limitation documented. M1 remains PENDING until the project owner approves.
