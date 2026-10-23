# Evaluation results

The current evidence paths are intentionally limited:

- `published.json` is the immutable public M5 closure artifact.
- `m5_tuning/20261016T223019Z/` and `react_wording/anchored_final/` are locked
  by `config/m5_frozen_evaluation.yaml` and its checksum verifier.
- `m5_finalization/` records technical closure and the free question-mark
  baseline.
- `react_calibration/` and `20261016T054927Z/` preserve the M1 baseline used by
  the provisional decision.
- `archive/` contains superseded development experiments retained only for
  auditability.

New generated runs are ignored by default. Review provenance, privacy, and
held-out isolation before deliberately committing any result.
