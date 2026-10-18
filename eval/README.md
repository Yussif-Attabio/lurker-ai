# M1 human evaluation workflow

> M5 recovery uses a separate candidate pool and separate instructions in
> `eval/recovery/LABELING_INSTRUCTIONS.md`. Do not mix its files with the M1
> datasets or either held-out set.

`scenario_candidates.jsonl` contains synthetic candidate conversations only. They are not ground truth and must not be passed to the evaluation runner.

The project owner approved a locked, stratified split in `split_manifest.json`:

- 30 tuning scenarios
- 15 held-out scenarios

The labeling interface intentionally hides this split, scenario categories,
other evaluators' answers, and all Decider predictions. The held-out set may be
labeled now, but it must not be evaluated by any model before M5.

## Decision guide

- `SILENT`: no response would improve the conversation. Use it for routine
  updates, ordinary back-and-forth between people, already-settled answers, and
  messages where an emoji would add noise or make Lurker seem intrusive.
- `REACT`: a lightweight emoji acknowledgment adds genuine social value, but
  written help is unnecessary. Typical examples are celebrating a concrete
  success, acknowledging sincere thanks, showing support after a setback, or
  appreciating a clearly shared joke.
- `REPLY`: an unanswered question, a request for help, or a direct request to
  Lurker needs a written answer.

Use this tie-breaker between `REACT` and `SILENT`: imagine the chat with no
Lurker response. If a small acknowledgment would make the interaction feel
noticeably warmer, more supportive, or more complete, choose `REACT`. If the
conversation already feels complete and the emoji would merely announce
Lurker's presence, choose `SILENT`. Do not choose `REACT` simply because a
message is positive, contains an emoji, or could technically receive one.

Judge each scenario independently. Do not try to balance the number of labels,
infer what a scenario was designed to test, or consult another evaluator.

## Run the labeling interface

From the project folder:

```bash
source .venv/bin/activate
PYTHONPATH=. python scripts/labeling_server.py
```

Open `http://127.0.0.1:8765`. Assign one person to each evaluator slot. The
three people should work separately and export these files only after all 45
answers are complete:

- Evaluator 1: `labels_a1.csv`
- Evaluator 2: `labels_a2.csv`
- Evaluator 3: `labels_a3.csv`

Progress is stored only in that browser and evaluator slot. Each evaluator can
also import their own earlier CSV to resume. The interface never sends data to
AWS or another external service.

For the strongest independence, use a separate browser profile or device for
each person. If all three people share one computer, the project owner should
export and clear each completed slot before handing the computer to the next
person.

The specification-compatible blank spreadsheet can also be regenerated with:

```bash
PYTHONPATH=. python scripts/make_label_sheet.py
```

## Merge genuine labels

Place the three exported files somewhere outside source control, then run:

```bash
PYTHONPATH=. python scripts/merge_labels.py \
  --a1 /path/to/labels_a1.csv \
  --a2 /path/to/labels_a2.csv \
  --a3 /path/to/labels_a3.csv
```

The default agreement rule is unanimous (`--min-agree 3`). Any disagreement is
`AMBIGUOUS`, is shown in reports, and is excluded from scored rates. The merge
refuses incomplete files, invalid labels, unknown IDs, duplicate IDs, and reuse
of the same path for more than one evaluator.

Before a candidate can be copied into `scenarios.jsonl`, humans must:

1. Review it for clarity, realism, and synthetic-only content.
2. Assign `split` as `tuning` or `heldout` before seeing any model result.
3. Have three annotators independently assign `a1`, `a2`, and `a3` using only `SILENT`, `REACT`, or `REPLY`.
4. Set `consensus` to the agreed label only when the configured agreement rule is met; otherwise use `AMBIGUOUS`.
5. Record any genuine ambiguity in `notes`.

Do not let Decider or Bedrock predictions influence labels or split assignment.
Only the validated merge workflow may update `scenarios.jsonl`.

## Run the real tuning evaluation

After merging three genuine exports:

```bash
PYTHONPATH=. python scripts/run_eval.py --split tuning --k 0 3 5
```

The first run is unthresholded because human-owned thresholds remain `null`.
It creates real prediction evidence under `results/<timestamp>/` and does not
call Bedrock. Then sweep thresholds using only the default k=3 tuning rows:

```bash
PYTHONPATH=. python scripts/tune_thresholds.py results/<timestamp>/per_case.csv
```

Review `threshold_sweep.csv` and `threshold_recommendation.json`. A human must
choose the thresholds and copy them into `config/default.yaml`; the script never
changes configuration automatically. Rerun the tuning evaluation to generate
the thresholded `report.md`, then the project owner records the final decision
in `GO_NOGO.md`.

`run_eval.py --split heldout` is locked by default. Its explicit override is
reserved for the approved M5 run.

## Separate REACT calibration

The calibration set is an additional tuning-only dataset. It does not replace,
relabel, append to, or evaluate the original 15 held-out scenarios. Its design
metadata is owner-only and is removed from the evaluator API.

Start the neutral calibration view:

```bash
source .venv/bin/activate
PYTHONPATH=. python scripts/labeling_server.py --dataset calibration
```

Use the same three human evaluators. They must work independently and should
not be told which scenarios were designed as clear or borderline examples.
After all 15 scenarios are labeled, collect:

- `calibration_labels_a1.csv`
- `calibration_labels_a2.csv`
- `calibration_labels_a3.csv`

Merge them with unanimous consensus into the separate reviewed dataset:

```bash
PYTHONPATH=. python scripts/merge_react_calibration_labels.py \
  --a1 /path/to/calibration_labels_a1.csv \
  --a2 /path/to/calibration_labels_a2.csv \
  --a3 /path/to/calibration_labels_a3.csv
```

Only after that merge succeeds, run the real Decider locally on the calibration
set. This command does not call AWS or Bedrock:

```bash
PYTHONPATH=. python scripts/run_eval.py \
  --split tuning \
  --scenarios eval/react_calibration_scenarios.jsonl \
  --output-root results/react_calibration \
  --k 0 3 5
```

Combine that new run with the preserved original tuning predictions and create
an approval-only recommendation:

```bash
PYTHONPATH=. python scripts/analyze_react_calibration.py \
  --original-predictions results/<original-run>/per_case.csv \
  --calibration-predictions results/react_calibration/<calibration-run>/per_case.csv
```

The analysis refuses held-out rows, writes only inside the calibration result
directory, and never edits `config/default.yaml`. Final M1 approval remains
pending until the project owner reviews the new recommendation.
