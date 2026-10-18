# Lurker AI Builder Center article notes

Status: **LOCAL DRAFT FACTS - NOT PUBLISHED**

These are evidence-backed notes for the human-authored AWS Builder Center
article. They are not a finished submission and contain no invented metrics.

## Required submission metadata

- Required tag: `#strands-decider-2b`
- Decision-pattern tag: `#policy`
- Deadline: October 23, 2026 at 11:59 p.m. PT
- Public repository URL: **human must add after publication**
- Public video URL: **human must add after upload**
- Official rules: <https://builder.aws.com/build/hackathons/4f50957c-1d08-37ab-b11c-97516b9adeb4/agent-experience-hackathon?tab=rules>

## Working title

**Lurker AI: The Group-Chat Agent That Knows When Not to Answer**

## One-line pitch

Most AI assistants are designed to answer. This one decides whether it should
answer at all.

## Problem and solution

- Group-chat assistants can interrupt ordinary conversation or repeat an answer
  a person already supplied.
- Strands Decider 2B reads synthetic recent chat state and chooses SILENT,
  REACT, or REPLY.
- A human-owned confidence policy can downgrade REACT or REPLY to SILENT.
- SILENT does nothing; REACT selects a local emoji; only REPLY calls Claude
  Haiku 4.5 through Amazon Bedrock Converse.
- Errors and timeouts fail closed to SILENT.

## Architecture facts

- Python 3.12, FastAPI, uvicorn, Pydantic v2, WebSocket, vanilla JavaScript.
- Real Decider access is isolated in `src/lurker/decider_adapter.py`.
- Frozen experiment: `k=3`, REPLY threshold `0.20`, REACT threshold `0.04`.
- Bedrock: Claude Haiku 4.5 cross-region profile in `us-east-2`.
- Controlled host: Linux `amd64` `m7i.2xlarge`, 32 GiB RAM.

## Reusable decision pattern

- Folder: `decision_pattern/`; options: SILENT, REACT, REPLY.
- `ChimeInGate` accepts any compatible Decider adapter.
- `ChimeInIntervention` uses the documented Strands
  `InterventionHandler.before_invocation` seam.
- Only REPLY returns `Proceed`. SILENT and REACT deny text generation before
  the model call; the host does nothing or renders an emoji.

## Real measured results

### One-time held-out evaluation

- 15 scenarios and 45 real Decider predictions across `k=0/3/5`, zero errors.
- Nine unanimous cases were scored; six ambiguous cases were reported only.
- Accuracy: 6/9 = 66.7% against a 70% minimum.
- Unnecessary interruption: 2/3 = 66.7% against a 20% maximum.
- Missed help: 1/6 = 16.7% against a 25% maximum.
- REACT recall unavailable: zero unanimous held-out REACT labels.
- `k=3` latency: p50 598.81 ms, p95 682.34 ms on Apple-silicon CPU.
- Honest conclusion: model-performance NO-GO; no held-out rerun or retuning.
- Source: `results/published.json` and `M5_FINAL_ACCEPTANCE.md`.

### Final controlled deployed reliability run

- Three no-retry real-service replays; nine messages total.
- Three SILENT, three REACT, three REPLY; exactly three Bedrock calls.
- Six calls avoided versus calling Bedrock on every message.
- Zero runtime errors and zero duplicate events.
- Decider p50/p95: 1,406.05/1,516.44 ms.
- Average Bedrock latency: 961.29 ms.
- Bedrock usage: 477 input tokens and 90 output tokens.
- Peak memory: 12.41 GiB under a 24 GiB limit; no OOM.
- Recovery gross estimate: $0.05913; zero unexpected resources after cleanup.
- Source: `data/m6_recovery_acceptance/20261018T201525Z/`.

## The failure worth explaining

- The first M6 deployment stopped without retry on a Bedrock IAM denial.
- Investigation found a condition incorrectly applied to both the inference
  profile and underlying models.
- The least-privilege correction separated the exact profile permission from
  the exact, profile-conditioned destination model permissions.
- Three real recovery calls passed; the original NO-GO remains preserved.

## What we learned

- Reliability can pass while model quality remains NO-GO.
- No unanimous REACT examples means held-out REACT recall is unknowable.
- Fail-closed control flow, call caps, immutable evidence, and honest failure
  reporting matter as much as a successful demo.
- Avoiding six of nine Bedrock calls is measured replay evidence, not proof of
  production savings at scale.

## Limitations to state plainly

- Experimental model and synthetic chat only.
- Held-out accuracy and interruption missed their gates.
- Missing held-out Bedrock-judge baseline.
- No authentication, database, multi-room support, or third-party integration.
- One temporary instance is not high availability or sustained-load evidence.
- M6 FINAL GO is controlled deployment viability, not production readiness.

## Suggested article structure

1. Open with the “already answered” interruption problem.
2. Show the actions and why only REPLY reaches Bedrock.
3. Explain the reusable policy pattern and intervention seam.
4. Walk through SILENT, REACT, and REPLY in the UI.
5. Report both the successful deployed replay and held-out NO-GO.
6. Explain the IAM failure and minimal correction.
7. Close with what should improve before real-world use.

## Claims not to make

- Do not say production-ready, highly available, or safe for private chats.
- Do not present M6 replay correctness as held-out model accuracy.
- Do not imply these thresholds generalize beyond synthetic chat.
- Do not claim a Bedrock judge comparison; it was not run.
- Do not claim zero total project cost; controlled AWS runs had recorded costs.
