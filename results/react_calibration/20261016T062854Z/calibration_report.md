# M1 REACT calibration analysis

This report combines the preserved original tuning predictions with the separate calibration run. It does not use held-out scenarios or modify production thresholds.

## Evidence

- Original tuning scenarios at k=3: 30
- Calibration scenarios at k=3: 15
- Combined scenarios at k=3: 45
- Calibration consensus: {'SILENT': 7, 'REACT': 4, 'REPLY': 0, 'AMBIGUOUS': 4}
- Combined raw choices: {'SILENT': 24, 'REACT': 2, 'REPLY': 19, 'AMBIGUOUS': 0}

## Unthresholded combined metrics

- Accuracy: 71.0%
- Unnecessary-interruption rate: 35.3%
- Missed-help rate: 0.0%

## Candidate thresholds

- Reply threshold: 0.4
- REACT threshold: 0.05
- Accuracy: 25/31 (80.6%)
- Unnecessary interruption: 2/17 (11.8%)
- Missed help: 1/10 (10.0%)
- Meets all criteria: True
- Unidentifiable thresholds: []

## REACT-class check

- Human-consensus REACT cases: 4
- Scored REACT predictions after thresholds: 1
- Correct REACT predictions: 1
- REACT precision: 100.0%
- REACT recall: 25.0%

The overall success criteria do not contain a class-specific REACT recall gate. A passing overall result therefore does not by itself establish strong REACT coverage.

## Decision status

PENDING. The project owner must review this evidence before changing `config/default.yaml` or approving final M1 GO.
