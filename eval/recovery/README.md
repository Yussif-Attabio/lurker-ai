# M5 recovery dataset workflow

Status: candidate preparation is complete. One genuine evaluator export has
been received and is authorized for a separate exploratory workflow. The
three-rater consensus workflow is still incomplete.

## Current artifacts

- `candidates.jsonl`: 195 new synthetic conversations in 39 five-item families.
- `design_manifest.json`: owner-only authoring coverage. Do not give this file to evaluators.
- `label_templates/`: three complete blank CSVs in distinct orders.
- `LABELING_INSTRUCTIONS.md`: the evaluator rubric and browser/spreadsheet workflow.
- `quality_report.json` and `PREFLIGHT.md`: reproducible preparation checks.

No file in this directory contains a human consensus label, model prediction, or split assignment yet.

## Hard boundaries

- The original M5 NO-GO bundle remains under `results/m5_heldout/20261017T053719Z/` and is read-only.
- No original held-out text or prediction may be copied into recovery development data, prompts, tests, or examples.
- `scripts/run_recovery_development.py` accepts only the future physical file `eval/recovery/development/development.jsonl`.
- The future new held-out file will live separately at `eval/recovery/heldout/new_heldout_locked.jsonl`.
- Neither held-out set may be evaluated without a new explicit authorization and freeze.
- Recovery scripts do not call AWS or Bedrock.

## After three genuine evaluations arrive

Do not run these commands until the three people have independently completed all 195 rows.

Merge using unanimous consensus:

```bash
PYTHONPATH=. python scripts/merge_recovery_labels.py \
  --a1 /path/to/recovery_labels_a1.csv \
  --a2 /path/to/recovery_labels_a2.csv \
  --a3 /path/to/recovery_labels_a3.csv
```

Review `labeling/agreement_report.json` before splitting. Required quality targets are:

- at least 50 unanimous rows for each class;
- ambiguity rate at or below 20%;
- Fleiss' kappa at least 0.60;
- every disagreement retained in `labeling/ambiguity_audit.jsonl`.

If a class is short, author and independently label additional families. Do not lower quotas or force a majority label.

After a human approves the agreement report, create the deterministic family-grouped split once:

```bash
PYTHONPATH=. python scripts/split_recovery_dataset.py
```

This creates exactly 90 development rows (30 per class) and 60 new held-out rows (20 per class). Extra unanimous rows stay in a family-locked reserve. The split script refuses to overwrite its outputs.

## Development-only evaluation tools

The starting baseline remains unchanged:

- context: k=3 primary, with k=0 and k=5 comparisons;
- REPLY threshold: 0.20;
- REACT threshold: 0.04;
- existing local Decider model and architecture.

After labels, quality approval, and split creation, a real local development run can be made with:

```bash
PYTHONPATH=. python scripts/run_recovery_development.py --k 0 3 5
```

This tool has no path option for held-out data. It requires exactly 90 `rc`-prefixed, unanimous, balanced development rows and records zero AWS/Bedrock calls in its manifest.

Development thresholds can be explored without another model call:

```bash
PYTHONPATH=. python scripts/tune_recovery_thresholds.py \
  results/m5_recovery/development/<run>/per_case.csv
```

Compare approved development variants with:

```bash
PYTHONPATH=. python scripts/compare_recovery_development.py \
  baseline=results/m5_recovery/development/<baseline-run> \
  candidate=results/m5_recovery/development/<candidate-run> \
  --output results/m5_recovery/development/comparison.json
```

These tools report accuracy, unnecessary interruptions, missed help, REACT precision/recall, latency, errors, configuration hashes, and raw predictions. They never edit `config/default.yaml`; any later configuration change requires owner approval.

## Single-evaluator exploratory workflow

The owner authorized using evaluator `a1` alone while ignoring the other two
exports. This does not produce human consensus and cannot support final M5
acceptance. The original merge and split commands above still require three
independent exports and have not been weakened.

The isolated single-rater preparation command is:

```bash
PYTHONPATH=. python scripts/prepare_single_rater_recovery.py \
  --labels /path/to/recovery_labels_a1.csv --evaluator-id a1
```

It creates a balanced development-only set of 90 cases, using complete scenario
families, and a locked reserve of 105 cases. It does not create a held-out set.
Run the local exploratory evaluation with:

```bash
PYTHONPATH=. python scripts/run_single_rater_recovery.py --k 0 3 5
```

Every resulting artifact is marked `EXPLORATORY_ONLY`, `human_consensus=false`,
and `final_m5_evidence=false`. Production thresholds remain unchanged.
