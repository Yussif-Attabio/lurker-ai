# Lurker AI

**A group-chat agent that knows when not to answer.**

Most assistants are optimized to respond. I built Lurker to make a smaller,
more important decision first: should the agent stay silent, acknowledge the
moment with an emoji, or write a reply?

Lurker uses Strands Decider 2B to choose one of three typed actions:

- `SILENT` — do nothing when speaking would add noise;
- `REACT` — add a lightweight local emoji when acknowledgment is useful;
- `REPLY` — call Amazon Bedrock when someone still needs an answer.

Only `REPLY` is allowed to reach the generative model. That rule makes agent
participation observable, testable, and cheaper than replying to every message.

- [Watch the 1:09 demo](https://youtu.be/hmZlMHcUCZc)
- [Read the Builder Center article draft](BUILDER_CENTER_ARTICLE.md)
- [Reuse the Chime-In Gate](decision_pattern/README.md)

> Status: hackathon prototype. The software and controlled deployment passed
> their acceptance checks, but the frozen held-out model evaluation did not.
> Lurker is not production-ready.

## Architecture

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

The Decider model loads once behind `src/lurker/decider_adapter.py`. A separate
policy applies the frozen experiment thresholds: 0.04 for `REACT` and 0.20 for
`REPLY`, using three prior messages of context. Low-confidence actions,
timeouts, malformed choices, and Decider errors fail closed to `SILENT`.
Bedrock errors never produce a fabricated reply.

The decision handed to Decider is intentionally narrow:

> Given the recent conversation and latest message, what should Lurker do?
> Choose REPLY only if someone needs an answer or help that nobody has given
> yet. Otherwise, choose REACT if a brief emoji would meaningfully acknowledge
> a noteworthy achievement, gratitude, support, or shared humor. Otherwise
> choose SILENT, including for routine updates, ordinary back-and-forth,
> already-handled points, or when a reaction would add noise.

## Quick start

Python 3.11 or newer is required. The default command below uses the explicit
mock mode, stays on localhost, and makes no AWS or Bedrock calls.

```bash
git clone https://github.com/Yussif-Attabio/lurker-ai.git
cd lurker-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
MOCK_DECIDER=true PYTHONPATH=. \
  uvicorn src.lurker.api:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. The UI clearly labels mock output so it cannot be
mistaken for evaluation evidence.

Run the offline regression suite:

```bash
PYTHONPATH=. python -m pytest -q
```

Real mode downloads the Decider model and may make a paid Bedrock call when the
action is `REPLY`. Deployment details and least-privilege IAM guidance are in
[DEPLOY.md](DEPLOY.md).

## Reusable policy pattern

[`decision_pattern/`](decision_pattern/) packages the core idea as a standalone
**Chime-In Gate**:

- a typed question and fixed `SILENT` / `REACT` / `REPLY` options;
- a confidence policy owned by application code;
- a `ChimeInGate` wrapper that accepts a compatible Decider adapter;
- a fail-closed `ChimeInIntervention` built on
  `InterventionHandler.before_invocation`; and
- a minimal example that does not run on import.

The intervention returns `Proceed` only for `REPLY`. For `REACT`, the host
renders an emoji locally; for `SILENT`, it does nothing. See the
[pattern guide](decision_pattern/README.md) for installation, adaptation, and
tuning notes.

## Submission results snapshot

I kept deployment reliability and decision quality separate. A clean demo does
not turn a weak evaluation into a pass.

### Frozen held-out evaluation

The one-time evaluation ran 45 real Decider predictions over 15 scenarios and
three context settings. Nine cases had unanimous human labels; ambiguous cases
were reported but not forced into the score.

| Metric | Result | Predefined gate |
|---|---:|---:|
| Accuracy | 6/9 = 66.7% | at least 70% — **FAIL** |
| Unnecessary interruption | 2/3 = 66.7% | at most 20% — **FAIL** |
| Missed help | 1/6 = 16.7% | at most 25% — **PASS** |
| Decider errors | **0** | 0 — **PASS** |

There were no unanimously labeled `REACT` cases, so held-out REACT recall is
unavailable. I did not retune on the held-out cases or rerun the evaluation.
The model-quality decision is **NO-GO**.

### Controlled deployed replay

After fixing a narrowly scoped IAM error, three consecutive no-retry replays
produced three `SILENT`, three `REACT`, and three `REPLY` actions:

| Evidence | Recorded result |
|---|---:|
| Bedrock calls | 3 for 9 messages; 6 avoided |
| Runtime errors / duplicate events | 0 / 0 |
| Decider latency | 1,406.05 ms p50 / 1,516.44 ms p95 |
| Average Bedrock latency | 961.29 ms |
| Bedrock tokens | 477 input / 90 output |
| Peak container memory | 12.41 GiB; no OOM |
| Recovery-run estimate | $0.05913 gross |

The original failed deployment remains preserved alongside the successful
recovery. All temporary AWS resources were deleted after testing.

Primary evidence:

- [published M5 evaluation bundle](results/published.json)
- [M5 final acceptance report](M5_FINAL_ACCEPTANCE.md)
- [M6 reliability and recovery report](M6_ACCEPTANCE.md)
- [public-release boundaries](PUBLIC_RELEASE.md)

## Project map

```text
src/lurker/       application, policy pipeline, metrics, and AWS wrapper
web/              single-page chat and decision console
decision_pattern/ reusable Chime-In Gate and Strands intervention
eval/             scenario, labeling, metric, and publication tooling
scripts/          smoke tests, replay tools, evaluation, and demo recorder
tests/            offline regression and contract tests
data/             redacted deployment and reliability evidence
results/          recorded evaluation outputs
config/           current and frozen experiment configurations
```

Historical milestone plans and acceptance records remain in the repository as
an audit trail. They are not claims of production readiness.

## Submission limitations

- The conversations and demo participants are synthetic.
- Held-out accuracy and unnecessary interruption missed their gates.
- Only nine held-out cases were unanimous, with no unanimous `REACT` cases.
- The optional held-out Bedrock-judge baseline was not run.
- The recovery label document records combined input from three contributors,
  not verifiable independent ratings or measurable inter-rater agreement.
- There is no authentication, database, multi-room support, or third-party chat
  integration.
- A bounded temporary deployment does not establish high availability,
  concurrency limits, or sustained-load performance.

The next model-quality step would be a new preregistered evaluation on a larger,
independently labeled and class-balanced dataset—not another run on the original
held-out cases.

## License

Released under the OSI-approved [MIT License](LICENSE).

#strands-decider-2b #policy
