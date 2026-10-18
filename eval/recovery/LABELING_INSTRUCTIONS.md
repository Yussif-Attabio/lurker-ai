# M5 recovery human-labeling instructions

Use these instructions for the new 195-candidate recovery pool only. The original M5 held-out set and its NO-GO result are not part of this exercise.

## Independent review rules

1. Each evaluator uses only their assigned slot or assigned CSV.
2. Do not discuss individual scenarios until all three exports are complete.
3. Do not look at another evaluator's answers.
4. Do not try to balance the number of SILENT, REACT, and REPLY choices.
5. Judge only the conversation shown. Do not assume hidden facts.
6. Choose what a quiet, useful group-chat assistant should do immediately after the latest message.
7. Punctuation is not decisive. A request can need a reply without ending in `?`, and a rhetorical question can need no answer.

The interface and CSVs intentionally omit scenario-family IDs, authoring targets, split assignments, thresholds, model predictions, and other evaluators' labels.

## Decision guide

### SILENT

Choose `SILENT` when no assistant action would improve the conversation.

Typical reasons:

- another person already answered the question adequately;
- the latest message is a routine status or availability update;
- people have settled a decision or schedule;
- the latest message is ordinary back-and-forth, an acknowledgment, or conversational closure;
- a mention of Lurker describes it but does not ask it to act;
- the message is rhetorical and does not seek information;
- an emoji would mainly announce the assistant's presence or add noise.

### REACT

Choose `REACT` when one lightweight emoji would add genuine social value and no written help is needed.

Typical reasons:

- a concrete milestone or meaningful success deserves celebration;
- someone expresses sincere gratitude that merits acknowledgment;
- a person shares a setback or recovery where quiet support would help;
- the group shares a clear joke;
- good news, recognition, welcome, or community impact benefits from a warm acknowledgment.

Do not choose `REACT` merely because a message is positive, contains an emoji, or could technically receive one.

### REPLY

Choose `REPLY` when a person still needs written help.

Typical reasons:

- an unanswered factual or technical question;
- a direct request to Lurker or the group;
- an indirect but clear request for assistance;
- a request for judgment, planning, review, explanation, summary, or transformation;
- an underspecified request where asking a concise clarifying question is the useful next step;
- a safety or security question that should not be ignored.

## Tie-breakers

`REPLY` versus `SILENT`: read the recent context. If someone already supplied an adequate answer, choose `SILENT`. If a real information or help need remains, choose `REPLY` even if the latest message has no question mark.

`REACT` versus `SILENT`: imagine Lurker does nothing. If one small acknowledgment would make the exchange noticeably warmer, more supportive, or more complete, choose `REACT`. If the exchange already feels complete and an emoji would add little, choose `SILENT`.

`REACT` versus `REPLY`: choose `REPLY` whenever written information, action, or clarification is still needed. Choose `REACT` only when acknowledgment is enough.

If the scenario genuinely supports more than one action, choose the action you believe is best and briefly explain the uncertainty in the optional note. Disagreements will be retained in a separate ambiguity audit; they will not be forced into consensus.

## Browser workflow

From the project folder:

```bash
source .venv/bin/activate
PYTHONPATH=. python scripts/labeling_server.py --dataset recovery --port 8765
```

Open `http://127.0.0.1:8765`. Assign exactly one slot to each evaluator. The interface saves progress only in that browser profile and exports:

- Evaluator 1: `recovery_labels_a1.csv`
- Evaluator 2: `recovery_labels_a2.csv`
- Evaluator 3: `recovery_labels_a3.csv`

For strongest independence, use separate browser profiles or devices. If evaluators share one device, export and clear the completed slot before the next person begins.

## Spreadsheet fallback

If the browser interface is inconvenient, give each person only their matching file in `eval/recovery/label_templates/`. Each file contains the same 195 scenarios in a different order. Enter exactly one of `SILENT`, `REACT`, or `REPLY` in every `label` cell. The optional note may be left blank.

Do not collect or merge labels until all three evaluators have completed their work independently.
