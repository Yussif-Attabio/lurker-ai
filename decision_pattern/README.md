# Chime-In Gate

`decision_pattern/` is Lurker AI's reusable Strands Decider 2B **policy**
pattern. It answers one bounded question before an agent generates text:

> Should the assistant stay SILENT, add a lightweight REACT, or REPLY?

The exact typed question and option set live in `lurker_gate.py`. The app,
evaluation code, and reusable wrapper all import that same contract.

## What it decides

- `SILENT`: ordinary conversation, already-handled points, or no useful input.
- `REACT`: one local emoji adds value but a text answer does not.
- `REPLY`: someone still needs an answer or directly asks the assistant.

Only `REPLY` may reach the generative model. A Decider error, unknown output,
or confidence below the human-owned threshold becomes `SILENT`.

## Typed question and options

```python
from decision_pattern import OPTIONS, QUESTION
```

`OPTIONS` is exactly `['SILENT', 'REACT', 'REPLY']`. Read `QUESTION` from the
package rather than copying it so evaluation and runtime wording cannot drift.

## Confidence policy

`apply_policy` accepts a normalized result plus separate REPLY and REACT
thresholds. SILENT is never upgraded. REACT or REPLY below its threshold is
downgraded to SILENT. Thresholds must be selected on your own development data,
not copied from Lurker's synthetic-chat experiment.

## Install

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Drop-in example

`ChimeInGate` accepts any adapter with
`decide(state, question, options)`. `ChimeInIntervention` uses the official
Strands `InterventionHandler.before_invocation` seam. It returns `Proceed` only
for REPLY; SILENT and REACT return a fail-closed `Deny` before the Strands model
call. The host reads `last_decision` to do nothing or render an emoji.

```python
from strands import Agent
from decision_pattern import ChimeInGate
from decision_pattern.strands_hook import ChimeInIntervention

gate = ChimeInGate(your_adapter, reply_threshold=0.7, react_threshold=0.6, k=3)
intervention = ChimeInIntervention(gate)
agent = Agent(interventions=[intervention])
```

See `example_usage.py` for a complete minimal wiring example. Running it may
invoke the default Strands Bedrock model on REPLY and therefore requires AWS
credentials and explicit cost authorization.

## Tune it on your data

1. Create realistic scenarios for your domain.
2. Collect independent human labels for SILENT, REACT, and REPLY.
3. Split related scenario families before tuning to prevent leakage.
4. Tune thresholds only on development data.
5. Freeze wording, model revision, policy, and thresholds before held-out use.
6. Report ambiguous labels separately rather than forcing agreement.

## Limitations

- Strands Decider 2B is experimental.
- Lurker was tested only on synthetic group-chat scenarios.
- Lurker's original held-out model result was a performance NO-GO; its
  thresholds are examples, not recommendations.
- The intervention cancels non-REPLY text generation. The host application is
  responsible for rendering REACT and for logging decisions.
- This pattern is not production security, moderation, or authorization logic.

The implementation follows the official Strands Decider intervention example:
<https://github.com/strands-labs/strands-decider/tree/main/examples/strands>.
