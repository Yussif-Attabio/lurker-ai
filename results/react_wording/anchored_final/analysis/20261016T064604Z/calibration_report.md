# M1 REACT calibration analysis

This report combines the preserved original tuning predictions with the separate calibration run. It does not use held-out scenarios or modify production thresholds.

## Evidence

- Original tuning scenarios at k=3: 30
- Calibration scenarios at k=3: 15
- Combined scenarios at k=3: 45
- Calibration consensus: {'SILENT': 7, 'REACT': 4, 'REPLY': 0, 'AMBIGUOUS': 4}
- Combined raw choices: {'SILENT': 22, 'REACT': 5, 'REPLY': 18, 'AMBIGUOUS': 0}

## Unthresholded combined metrics

- Accuracy: 74.2%
- Unnecessary-interruption rate: 41.2%
- Missed-help rate: 0.0%

## Candidate thresholds

- Reply threshold: 0.2
- REACT threshold: 0.04
- Accuracy: 26/31 (83.9%)
- Unnecessary interruption: 3/17 (17.6%)
- Missed help: 1/10 (10.0%)
- Meets all criteria: True
- Unidentifiable thresholds: []

## REACT-class check

- Human-consensus REACT cases: 4
- Scored REACT predictions after thresholds: 3
- Correct REACT predictions: 3
- REACT precision: 100.0%
- REACT recall: 75.0%

The overall success criteria do not contain a class-specific REACT recall gate. A passing overall result therefore does not by itself establish strong REACT coverage.

## Decision status

PENDING. The project owner must review this evidence before changing `config/default.yaml` or approving final M1 GO.
