# M5 recovery wording candidate

Status: **DEVELOPMENT-ONLY CANDIDATE; NOT PRODUCTION CONFIGURATION**

Candidate: `m5-recovery-social-value-v1`

## Baseline failure analysis

The analysis uses only the 90 frozen single-evaluator development cases and the
existing k=3 baseline predictions. It does not use the 105-case reserve or an
original/new held-out set.

At k=3, the baseline produced 64/90 correct decisions. Its main errors were:

- REACT recall: 14/30. Fifteen reference-REACT cases became SILENT and one
  became REPLY after policy.
- Unnecessary interruptions: 9/30 reference-SILENT cases. Six became REACT and
  three became REPLY.
- Missed help: 1/30 reference-REPLY cases.

The missed REACT cases cluster around concrete achievements and beneficial
impact stated without overt celebration, emotionally mixed support moments,
sincere gratitude or belonging, personal good news, and shared humor. The
unnecessary interruptions cluster around routine positive results,
conversational answers to earlier questions, reciprocal jokes, ordinary social
closure, and acknowledgments where the evaluator preferred no additional
signal.

The single evaluator also drew different boundaries within several closely
related families. That is a material limitation: wording can be compared with
this person's labels, but the result cannot establish a stable human-consensus
boundary.

## General decision principles

1. **REPLY for unresolved need.** Choose REPLY only when the latest message
   directly or indirectly asks for information, help, judgment, clarification,
   or action that is still unresolved.
2. **Read the latest message in context.** An earlier question does not make the
   latest answer or update another request. Do not reply to a need that the
   conversation has already handled.
3. **REACT for meaningful social value.** When no reply is needed, use a brief
   reaction for a concrete achievement or beneficial impact, sincere gratitude
   or support, important personal news, a significant setback or recovery
   moment, belonging or welcome, or clearly shared humor.
4. **Meaning beats punctuation.** A socially meaningful moment can merit REACT
   without an exclamation mark, emoji, or celebratory wording.
5. **SILENT for routine closure and noise.** Ordinary positivity, routine
   results, reciprocal politeness, self-contained answers, conversational
   closure, and already-handled points stay SILENT when acknowledgment adds no
   clear value.
6. **Tie-break in priority order.** Unresolved need → REPLY. No reply needed but
   clear social value → REACT. Otherwise → SILENT.

The candidate preserves the model ID and revision, k values, context builder,
options, REPLY threshold 0.20, REACT threshold 0.04, and action policy. It does
not modify `decision_pattern/lurker_gate.py` or `config/default.yaml`.

## Development comparison result

The real local run completed 270/270 predictions over the same 90 development
cases at k=0/3/5 with zero model errors. The primary k=3 comparison is:

| Metric | Original wording | Candidate | Change |
|---|---:|---:|---:|
| Accuracy | 64/90 (71.1%) | 64/90 (71.1%) | 0.0 pp |
| Unnecessary interruption | 9/30 (30.0%) | 5/30 (16.7%) | -13.3 pp |
| Missed help | 1/30 (3.3%) | 1/30 (3.3%) | 0.0 pp |
| REACT precision | 14/20 (70.0%) | 10/15 (66.7%) | -3.3 pp |
| REACT recall | 14/30 (46.7%) | 10/30 (33.3%) | -13.3 pp |
| Latency p50 | 581.54 ms | 848.25 ms | +266.71 ms |
| Latency p95 | 1,100.80 ms | 1,605.11 ms | +504.31 ms |

The candidate repaired five baseline unnecessary REACT decisions and introduced
no new missed requests. However, it gained only two correct REACT decisions and
lost six previously correct REACT decisions. Four reference-SILENT cases also
became newly classified as REACT relative to their baseline action, although
three of those were already unnecessary REPLY interruptions. The result is
quieter overall but overcorrects toward SILENT and does not improve REACT
recognition.

## Recommendation

**Reject this candidate for production.** Keep the original production wording,
thresholds, and policy unchanged. The lower interruption rate does not justify
the worse REACT precision, worse REACT recall, and higher latency. A future
development candidate should be shorter and should separate socially
meaningful acknowledgment from routine positivity without adding another long
list of exclusions. It requires separate approval and must use only the same
development set.
