# M5 one-time held-out evaluation procedure

Status: **PREPARED, LOCKED, AND NOT AUTHORIZED**

This procedure may be executed only after the project owner gives a separate,
explicit authorization that names the held-out run, AWS duration/spending cap,
and Bedrock judge call cap/model. Preparing or verifying this document does not
open the held-out dataset, load the Decider, call AWS, or permit execution.

## Frozen contract

- Freeze file: `config/m5_frozen_evaluation.yaml`.
- Primary pass/fail context: k=3.
- Comparison-only contexts: k=0 and k=5.
- REPLY threshold: 0.20; REACT threshold: 0.04 for every context.
- Model revision: `216d1ccb46a9e9b036eb9187b248db98480f77d4`.
- Expected held-out cases: 15; expected Decider predictions: 45.
- No threshold, context, prompt, policy, metric, denominator, or success gate
  may change after authorization or after any held-out result becomes visible.

## Pre-unlock stop conditions

Stop without opening held-out data if any condition fails:

1. A new written owner authorization has not been recorded.
2. `scripts/verify_m5_freeze.py` does not return PASS.
3. Any tuning/calibration evidence tree checksum differs from the freeze file.
4. The frozen model revision is missing or its metadata checksums differ.
5. Any prior final held-out output or publication target exists.
6. AWS authentication, quota, restricted networking, least-privilege IAM,
   automatic termination, or cost controls fail preflight.
7. The owner-approved Bedrock baseline model/call cap is absent.

## Single unlock and execution sequence

After authorization, record its identifier and UTC timestamp without copying
scenario text into logs. Then perform this sequence once:

1. Run the offline freeze verifier and preserve its JSON output in a new,
   exclusive `results/m5_heldout/<UTC timestamp>/` directory.
2. Start the approved controlled deployment window. Verify the automatic
   termination safeguard and cost/resource inventory before model work.
3. On the target instance, run the physically separate 30-row tuning input at
   k=0/3/5 with the frozen model and policy. This is an environment/latency
   confirmation only and cannot alter the freeze.
4. Open the pre-registered shared scenario source for the first authorized
   time. Materialize exactly the 15 `heldout` rows into a run-local file,
   validate unique IDs/split/labels, record only its checksum and count in the
   manifest, and do not print scenario text.
5. Run the real Decider once over those 15 cases at k=0/3/5 using
   `config/m5_frozen_evaluation.yaml` values: exactly 45 predictions, no mock
   rows, no retries. Any model error is preserved and fails the run.
6. Run the zero-model punctuation baseline at k=3.
7. Run the owner-approved Bedrock judge baseline at k=3, temperature 0, eight
   output tokens, at most 15 invocations, and no automatic retry. Preserve
   tokens, latency, responses, and errors.
8. Compute the frozen metrics. AMBIGUOUS cases are listed separately and
   excluded from label-dependent rates but included in completeness, latency,
   error totals, and prediction counts.
9. Determine PASS/FAIL only from k=3 accuracy >=70%, unnecessary interruption
   <=20%, missed help <=25%, zero Decider errors, 45/45 predictions, and zero
   mock rows. k=0/k=5, REACT precision/recall, and latency are reporting-only.
10. Assemble the immutable M5 bundle, verify all raw counts and checksums, then
    publish it once. Never overwrite or silently rerun failed evidence.
11. Run the separately approved synthetic WebSocket SILENT/REACT/REPLY check,
    allowing exactly one Bedrock reply invocation.
12. Terminate paid infrastructure immediately and preserve a zero-leftover
    inventory check. A failed gate yields an honest M5 NO-GO and a new plan,
    not retuning or another held-out pass.

## Reproducible commands prepared for the authorized window

The exact timestamp, authorization ID, run directory, held-out input path,
Bedrock model, and AWS limits must be filled from the future approval. Until
then these commands are intentionally non-executable placeholders.

```bash
PYTHONPATH=. python scripts/verify_m5_freeze.py \
  --output results/m5_heldout/<UTC_TIMESTAMP>/freeze_preflight.json

PYTHONPATH=. python scripts/prepare_heldout_unlock.py \
  --allow-heldout --authorization-id <RECORDED_OWNER_AUTHORIZATION_ID> \
  --output results/m5_heldout/<UTC_TIMESTAMP>/heldout_locked.jsonl

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 AWS_EC2_METADATA_DISABLED=true \
PYTHONPATH=. python scripts/run_eval.py \
  --split heldout --allow-heldout \
  --scenarios results/m5_heldout/<UTC_TIMESTAMP>/heldout_locked.jsonl \
  --config config/default.yaml --k 0 3 5 \
  --output-root results/m5_heldout/<UTC_TIMESTAMP>/decider

PYTHONPATH=. python scripts/run_baselines.py \
  --baseline always_questions --split heldout --allow-heldout \
  --scenarios results/m5_heldout/<UTC_TIMESTAMP>/heldout_locked.jsonl \
  --context-k 3 \
  --output-dir results/m5_heldout/<UTC_TIMESTAMP>/baseline_questions

AWS_REGION=us-east-2 BASELINE_MODEL_ID=<OWNER_APPROVED_MODEL> \
PYTHONPATH=. python scripts/run_baselines.py \
  --baseline bedrock_judge --split heldout --allow-heldout \
  --scenarios results/m5_heldout/<UTC_TIMESTAMP>/heldout_locked.jsonl \
  --context-k 3 --max-calls 15 \
  --output-dir results/m5_heldout/<UTC_TIMESTAMP>/baseline_bedrock
```

No command in this document has been run as part of the freeze.
