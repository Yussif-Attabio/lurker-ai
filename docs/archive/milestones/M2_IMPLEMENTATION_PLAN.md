# Milestone M2 implementation plan

## Current status - 2026-10-16

Work packages 1-8 are implemented and verified locally. The offline suite has
49 passing tests, dependency validation is clean, and the controlled local
real-service WebSocket run observed `SILENT`, `REACT`, and `REPLY` with exactly
one real Bedrock response. All M2 acceptance requirements passed on 2026-10-16.
M2 is complete; this does not imply production readiness.

## Objective and acceptance gate

Build the complete local backend defined by the original build specification:
adapter lifecycle, bounded chat context, confidence policy, message pipeline,
local emoji reactor, Bedrock replier, append-only metrics, REST API, and
WebSocket API.

M2 is accepted only when:

1. Offline unit tests pass for policy, metrics, context, adapter normalization,
   and the pipeline using `MockDecider`.
2. A scripted WebSocket client demonstrates one `SILENT`, one `REACT`, and one
   `REPLY` decision.
3. The `REPLY` path contains real Bedrock-generated text and records real
   latency and token counts.

The third check can incur Bedrock usage. Implement and verify everything else
locally first, then request explicit owner approval before the single controlled
real acceptance run. Do not launch compute instances or other paid AWS
resources during M2.

## Fixed inputs and boundaries

- Provisional policy: context k = 3, reply threshold 0.20, REACT threshold 0.04.
- Model and architecture remain unchanged.
- Only `src/lurker/decider_adapter.py` may import or call Strands Decider.
- Only a final `REPLY` may invoke Bedrock.
- A Decider error, timeout, or unparseable result fails closed to `SILENT`.
- Bedrock errors post no agent message, are recorded, and do not stop chat.
- Tests never call the real Decider or Bedrock.
- No authentication, database server, third-party chat integration, or frontend
  build system is added.
- The held-out evaluation split is not read or evaluated in M2.
- Synthetic messages only; no private chat data.

## Work packages

### 1. Configuration and schemas

- Add `src/lurker/config.py` to load `config/default.yaml` plus supported
  environment overrides.
- Validate context, timeouts, model identifiers, AWS region, and thresholds.
- Refuse non-mock startup when either threshold is missing.
- Extend `src/lurker/schemas.py` with `ChatMessage`, `DecisionEvent`, API payloads,
  and exact action/event field types from the specification.
- Keep secrets and credentials out of configuration files and logs.

### 2. Decider and mock lifecycle

- Keep the existing real adapter as the sole Decider boundary.
- Load the real engine once during application startup and call `warmup()` once.
- Add `src/lurker/mock_decider.py` with the same `decide()` interface,
  deterministic keyword rules, fixed fake confidence, and `mock=True`.
- Ensure mock events can never be confused with real evaluation output.

### 3. Context and local reactions

- Add a one-room bounded in-memory context store around the existing pure
  `build_state()` function.
- Support append, recent-history lookup, and reset while preserving k = 0, 3,
  and 5 behavior in tests.
- Add `src/lurker/reactor.py` with a small deterministic keyword-to-emoji map and
  a neutral default. It must make no model or network call.

### 4. Bedrock replier

- Add `src/lurker/bedrock_replier.py` using `boto3` Bedrock Runtime `Converse`.
- Read the model ID from `BEDROCK_MODEL_ID` and region from `AWS_REGION`.
- Use the specified quiet-teammate system prompt and include recent plus latest
  messages.
- Return text, latency, input tokens, and output tokens from the real response.
- Normalize failures into a recorded error with no posted reply.
- Unit-test with a stubbed client only.

### 5. Metrics and persistence

- Add `src/lurker/metrics.py` with an in-memory event list and append-only
  `data/decisions.jsonl` persistence.
- Compute counters from events: messages read, silent, react, reply, downgraded,
  errors, Bedrock calls made, and
  `bedrock_calls_avoided_vs_every_message`.
- Compute Decider latency p50 and p95 from recorded real values.
- Reset in-memory state while rotating to a new timestamped JSONL file; never
  delete historical logs.
- Keep mock events marked and out of real result artifacts.

### 6. Pipeline orchestration

- Add `src/lurker/pipeline.py` with dependency injection for adapter, replier,
  reactor, context, metrics, and event broadcasting.
- On each user message: append and broadcast chat immediately, then run decision,
  policy, action, and event recording in a background task.
- `SILENT`: emit the decision event only.
- `REACT`: choose locally and emit a reaction for the target message.
- `REPLY`: call Bedrock exactly once, then emit the agent chat message only when
  successful.
- Emit a decision and refreshed counters for every input, including `SILENT` and
  failures.

### 7. FastAPI and WebSocket contract

- Add `src/lurker/api.py` with application lifespan startup/shutdown and one-room
  connection management.
- Implement `GET /health`, `GET /api/metrics`,
  `GET /api/decisions?limit=50`, `POST /api/reset`, and
  `GET /api/eval/latest` exactly as specified.
- Implement `/ws` message validation and broadcast `chat`, `decision`,
  `reaction`, and `metrics` events with timestamps.
- Return clear errors for invalid payloads and unavailable required
  configuration without leaking credentials or account identifiers.

### 8. Tests and local acceptance tooling

- Add unit tests for every policy branch, metrics calculations and empty cases,
  bounded context, reactor selection, Bedrock response/error normalization,
  pipeline action routing, and API contracts.
- Assert `SILENT` makes zero Bedrock calls, `REACT` makes zero Bedrock calls,
  `REPLY` makes exactly one, and Decider failure becomes `SILENT`.
- Add `scripts/smoke_websocket.py` to send three synthetic messages and save an
  auditable transcript without exposing credentials.
- Run the full offline suite and dependency check before any real-service test.

## Execution order

1. Configuration and schemas.
2. MockDecider, context store, and reactor.
3. Metrics store and rotation behavior.
4. Stub-tested Bedrock replier.
5. Dependency-injected pipeline and background execution.
6. REST and WebSocket API.
7. Offline unit and API/WebSocket integration tests.
8. Start the backend locally in real-Decider mode and verify `/health` without
   invoking Bedrock.
9. Stop for owner approval before the billable real-Bedrock acceptance run.
10. Run the scripted SILENT/REACT/REPLY transcript once, record real outputs in
    `NOTES.md`, and mark M2 complete only if every acceptance condition passes.

## Evidence and rollback

- Preserve `config/default.pre_m1_provisional.yaml` as the configuration rollback
  point.
- Write runtime decisions only under `data/`; do not overwrite evaluation
  results.
- Save the final M2 WebSocket transcript and acceptance summary under a new
  timestamped results or data directory.
- Do not change the M1 thresholds during M2 without a new owner decision.
