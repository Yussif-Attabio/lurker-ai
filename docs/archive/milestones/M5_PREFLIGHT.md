# M5 final-evaluation preflight

Status: **PASS - CONFIGURATION FROZEN; HELD-OUT AUTHORIZATION PENDING**

Generated: 2026-10-17T00:31:56Z

## Safety boundary

- Held-out dataset opened during this freeze/preflight: no.
- Held-out predictions or metrics produced: 0.
- Real Decider loads/invocations: 0.
- AWS API calls, resources, or deployments: 0.
- Bedrock calls: 0.
- Production configuration changes: 0.

## Owner-approved frozen configuration

| Item | Frozen value |
|---|---|
| Primary context | k=3 |
| Comparison-only contexts | k=0 and k=5 |
| REPLY threshold | 0.20 |
| REACT threshold | 0.04 |
| Model | `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610` |
| Model revision | `216d1ccb46a9e9b036eb9187b248db98480f77d4` |
| Device | CPU |
| Decision options | SILENT, REACT, REPLY |
| Frozen configuration SHA-256 | `90adbd547d71d1766bcf3e0a254317104c0f7549ab02ca99cb09e650054981ed` |
| Freeze-file SHA-256 | `52a54a7058f53886bc789d930670e6f74407603105b13c13d01238ca24658401` |

The exact decision wording, context construction, action policy, fail-closed
behavior, metric formulas, criteria, model metadata, source-file hashes, and
evidence-tree hashes are recorded in `config/m5_frozen_evaluation.yaml`.

## Locked metrics and success rules

Only k=3 determines the held-out PASS/FAIL result:

- accuracy >= 70%;
- unnecessary-interruption rate <= 20%;
- missed-help rate <= 25%;
- exactly 45/45 Decider predictions across k=0/3/5;
- zero Decider errors and zero mock rows.

Accuracy, unnecessary interruption, missed help, REACT precision/recall, p50
and p95 latency, calibration, errors, decision counts, and ambiguous cases must
all be reported with raw counts where applicable. REACT precision/recall and
latency have no newly invented pass threshold and cannot be used to retune.

`AMBIGUOUS` cases are excluded from accuracy, unnecessary interruption, missed
help, REACT precision/recall, and calibration accuracy. They remain included in
prediction completeness, action counts, latency, error totals, and a separate
ambiguous-case listing.

## Preserved pre-freeze evidence

The original 30-scenario tuning subset at k=3 recorded:

- accuracy: 16/20 (80.0%);
- unnecessary interruptions: 3/10 (30.0%);
- missed help: 1/10 (10.0%);
- ten ambiguous cases and no unanimous REACT case.

The separate tuning-plus-REACT-calibration evidence recorded:

- accuracy: 26/31 (83.9%);
- unnecessary interruptions: 3/17 (17.6%);
- missed help: 1/10 (10.0%);
- REACT precision: 3/3 (100%);
- REACT recall: 3/4 (75%).

The 17.6% combined interruption rate does not replace or conceal the 30.0%
result on the original tuning subset.

Both evidence trees remain byte-for-byte unchanged:

| Evidence | Files | Frozen tree SHA-256 |
|---|---:|---|
| `results/m5_tuning/20261016T223019Z` | 20 | `4975f3062c0b637369ed6e3b3e5687dfb0d1c34f09e51dead1d9bbd1f67a2819` |
| `results/react_wording/anchored_final` | 14 | `e5479f8deeb3506c48288e4afc063ad4ccda7f0e404c2bf0478f8be4262e9030` |

## Isolation and regression verification

- Tuning loader selected only `eval/tuning_scenarios.jsonl`.
- Tuning rows: exactly 30; observed splits: tuning only.
- Audited loader test proved the shared scenario source was not opened.
- Accidental held-out evaluation without the explicit override was refused.
- Threshold tuning rejected mixed/held-out prediction input.
- Named dataset-isolation suite: 4 passed.
- Freeze/unlock focused suite: 10 passed.
- Complete offline regression suite: 89 passed.
- Freeze verifier status: PASS; every config, code, model, and evidence digest
  matched.

Machine-readable evidence is preserved at
`data/archive/evaluation_freeze/20261017T002835Z/preflight.json`.

## One-time procedure readiness

`M5_HELDOUT_PROCEDURE.md` defines the stop conditions, single unlock, 45
Decider predictions, both baselines, frozen scoring, immutable publication,
end-to-end check, and AWS cleanup sequence. The prepared unlock utility requires
both `--allow-heldout` and a recorded owner authorization ID, writes only to new
paths, records count/checksums without printing scenario text, and refuses an
existing output. It was tested only with synthetic fixtures and has not been
run against the real held-out source.

## Pending authorization

The held-out dataset remains locked. The next action requires a separate owner
authorization covering the one-time held-out unlock/evaluation and, if the same
window will include them, the controlled AWS duration/spending limit and the
Bedrock judge model/call cap. No such authorization is inferred from the
configuration freeze.
