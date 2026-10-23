# Lurker AI: The Group-Chat Agent That Knows When Not to Answer

Most AI assistants are designed to answer. I built one that first decides
whether it should answer at all.

Lurker AI observes a synthetic group conversation and chooses one of three
actions for every new message:

- **SILENT** — do nothing when speaking would add noise;
- **REACT** — add one lightweight local emoji when acknowledgment has value;
- **REPLY** — ask Amazon Bedrock for a concise answer when someone still needs
  help.

The key architectural rule is simple: **only REPLY may invoke the generative
model**. SILENT and REACT stop before text generation. This makes the decision
to participate an explicit, inspectable part of the agent rather than another
instruction buried inside a large-model prompt.

- Source code: [github.com/Yussif-Attabio/lurker-ai](https://github.com/Yussif-Attabio/lurker-ai)
- Demo video: [youtu.be/hmZlMHcUCZc](https://youtu.be/hmZlMHcUCZc)
- Decision pattern: **Policy**

## The problem: helpful agents can still be annoying

Group chat is full of messages that do not need an AI answer: routine updates,
plans between people, jokes, congratulations, and questions that somebody has
already answered. An assistant that responds to everything quickly becomes the
most distracting participant in the room.

Prompting a generative model to “be less chatty” does not fully solve this. The
model has already been invoked, cost and latency have already been incurred,
and the participation decision is difficult to test separately from answer
quality.

Lurker separates those responsibilities. A small local Strands Decider 2B
model decides whether an action is warranted. Amazon Bedrock is reserved for
the one path that actually needs generated text.

## The decision I handed to Decider 2B

For each incoming message, Lurker gives Decider 2B a compact state containing:

- the agent name, `Lurker`;
- up to the three messages immediately before the latest message; and
- the latest sender and message text.

It then asks this typed question:

> Given the recent conversation and latest message, what should Lurker do?
> Choose REPLY only if someone needs an answer or help that nobody has given
> yet. Otherwise, choose REACT if a brief emoji would meaningfully acknowledge
> a noteworthy achievement, gratitude, support, or shared humor. Otherwise
> choose SILENT, including for routine updates, ordinary back-and-forth,
> already-handled points, or when a reaction would add noise.

The option set is deliberately small and typed:

```python
OPTIONS = ["SILENT", "REACT", "REPLY"]
```

This is a **policy decision**: classify the current conversational situation
before the agent acts. It is meaningful because the result controls whether a
generative-model call is allowed to happen at all.

Decider 2B returns both a choice and a confidence value. A separate,
human-owned policy then applies the frozen experimental thresholds:

- SILENT always stays SILENT;
- REACT proceeds at confidence 0.04 or above, otherwise it becomes SILENT;
- REPLY proceeds at confidence 0.20 or above, otherwise it becomes SILENT;
- errors, timeouts, and unknown choices fail closed to SILENT.

These thresholds are preserved experiment settings, not recommendations for
other applications. Another builder should tune and evaluate the pattern on
their own domain data before using it.

## Architecture: decide before generating

The application uses Python 3.12, FastAPI, Pydantic, WebSockets, vanilla
JavaScript, Strands Decider 2B, and Claude Haiku 4.5 through Amazon Bedrock.

```text
Browser chat
    |
    | WebSocket message
    v
FastAPI pipeline ---> last three messages + latest message
    |
    v
Strands Decider 2B ---> SILENT ---> log only
    |                   REACT  ---> render a local emoji
    |                   REPLY  ---> confidence gate ---> Bedrock Converse
    |                                                   |
    +---------------------------------------------------> short reply

Decision log ---> metrics API ---> Live and Evaluation views
```

Real Decider access is isolated behind one adapter, and the model is loaded
once rather than once per message. The application logs raw choice, confidence,
final action, policy reason, latency, and any error. That separation made it
possible to evaluate the decision layer independently from the quality of the
Bedrock-generated answer.

The reusable implementation also includes a Strands intervention. Before a
model invocation, `ChimeInIntervention` runs the gate:

```python
decision = gate.decide(recent_messages, latest_message)

if decision.action == "REPLY":
    return Proceed(reason="Lurker selected REPLY")

return Deny(reason=f"Lurker selected {decision.action}; skip text generation")
```

For REACT, the host reads the recorded decision and renders one local emoji.
For SILENT, it does nothing. A Bedrock exception never produces a fabricated
assistant message.

## Three messages, three different actions

The final demo sends three synthetic messages through the real Decider and
WebSocket pipeline.

First:

> “Let's meet at four tomorrow.”

Lurker chooses SILENT. This is ordinary coordination between people, so the
assistant does not interrupt and Bedrock is not called.

Second:

> “Congratulations everyone—we made the hackathon finals! 🎉”

Lurker chooses REACT and adds a local celebration emoji. The moment is
acknowledged without turning it into another AI-written paragraph, and
Bedrock is still not called.

Third:

> “Lurker, please answer: why does the API return 401?”

Lurker chooses REPLY. Only then does the pipeline invoke Claude Haiku 4.5
through Amazon Bedrock and post the recorded answer to the conversation.

The three decisions use the same question, option set, model revision, and
confidence policy. There is no punctuation-only shortcut and no hard-coded
mapping for these messages.

## What I measured

I treated deployment reliability and decision quality as separate questions.
That distinction became one of the most important lessons in the project.

### Controlled real-service reliability

The final controlled AWS recovery run executed three consecutive, no-retry
replays: nine messages producing three SILENT, three REACT, and three REPLY
actions.

- Exactly three Bedrock calls were made—one for each REPLY.
- Six Bedrock calls were avoided compared with replying to every message.
- Runtime errors: zero.
- Duplicate messages, decisions, reactions, or calls: zero.
- Decider latency: 1,406.05 ms p50 and 1,516.44 ms p95 on the deployed CPU.
- Average Bedrock latency: 961.29 ms.
- Bedrock usage: 477 input tokens and 90 output tokens.
- Peak container memory: 12.41 GiB with no out-of-memory event.
- Gross estimate for the recovery run: $0.05913.

The temporary EC2 instance and its supporting resources were deleted
immediately after acceptance, and the cleanup inventory found no unexpected
billable resources.

These results demonstrate a functioning control path and measured call
avoidance for this replay. They do not prove savings at production scale.

### Honest model-quality evaluation

The one-time frozen held-out evaluation produced 45 real Decider predictions
across context sizes 0, 3, and 5. The primary configuration used the last three
messages. Nine cases had unanimous human labels and were scored; six ambiguous
cases were reported separately rather than forced into a label.

The primary result was:

| Metric | Result | Predefined gate |
|---|---:|---:|
| Accuracy | 6/9 = 66.7% | at least 70% — **FAIL** |
| Unnecessary interruption | 2/3 = 66.7% | at most 20% — **FAIL** |
| Missed help | 1/6 = 16.7% | at most 25% — **PASS** |
| Decider errors | 0 | 0 — **PASS** |

There were no unanimously labeled REACT cases in the held-out set, so held-out
REACT recall is unavailable. I did not retune on these cases or rerun the
evaluation after seeing the result.

The honest conclusion is **model-performance NO-GO**. The software and
controlled deployment work, but this experiment is not production-ready. The
Evaluation view and public documentation preserve that result instead of
turning a successful demo into a broader quality claim.

## A failure that improved the design

The first deployed M6 acceptance run reached REPLY but received an Amazon
Bedrock `AccessDeniedException`. The run stopped immediately—there was no
silent retry and no fabricated answer—and the failed evidence was preserved.

The problem was a least-privilege IAM condition applied too broadly across the
inference profile and its destination foundation-model resources. I corrected
the policy by separating permission for the exact Claude Haiku 4.5 inference
profile from the exact profile-conditioned destination models. A later bounded
recovery deployment passed all three real-service replays.

The original failure still remains in the project record. For an agent that
decides whether another model may run, observable failure behavior is part of
the product—not an inconvenient detail to hide.

## A reusable policy pattern

The repository's [`decision_pattern/`](https://github.com/Yussif-Attabio/lurker-ai/tree/main/decision_pattern)
directory packages the idea as a reusable **Chime-In Gate**. It contains:

- the typed question and `SILENT`, `REACT`, `REPLY` option set;
- the confidence and fail-closed policy;
- a `ChimeInGate` wrapper that accepts a compatible Decider adapter;
- `ChimeInIntervention`, wired through
  `InterventionHandler.before_invocation`; and
- a small standalone example and usage guide.

The reusable lesson is broader than group chat: put a small typed decision in
front of an expensive or disruptive agent action. Keep the action policy owned
by application code, log the raw and final decisions, cap external calls, and
evaluate ambiguous cases honestly.

## Limitations and next steps

Lurker AI is an experimental prototype using synthetic conversation data. It
does not include authentication, persistent chat storage, multiple rooms, or a
third-party messaging integration. One temporary deployment does not establish
high availability, concurrency limits, or sustained-load performance. The
held-out Bedrock-judge baseline was not run, and the held-out class balance was
too small to measure REACT recall.

Before real-world use, I would collect a larger independently labeled dataset
with strong SILENT, REACT, and REPLY coverage, preregister a new evaluation,
improve unnecessary-interruption performance using development data only, and
repeat the held-out test once under a newly frozen configuration.

For now, Lurker demonstrates a useful agent design principle: sometimes the
best AI action is not a generated answer. It may be a small acknowledgment—or
the discipline to leave the conversation alone.

#strands-decider-2b #policy
