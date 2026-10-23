# Milestone M4 implementation plan

Status: **IMPLEMENTED - TECHNICAL PASS, AWAITING OWNER FINAL M4 GO**

The completed implementation and browser evidence are recorded in
`M4_ACCEPTANCE.md` and `data/m4_acceptance/20261016T213850Z/`. Every technical
criterion below passed; only the project owner's final M4 GO remains open.

## Objective

Build the original specification's one-page frontend: a three-participant chat
on the left and a live decision dashboard on the right. A human must be able to
play Alex, Lea, and an editable third participant from one browser and watch
every SILENT, REACT, and REPLY decision appear live.

M4 will use the existing FastAPI, REST, and WebSocket contracts. It will not
change the Decider model, provisional M1 thresholds, message pipeline, Bedrock
boundary, evaluation data, or deployment architecture.

## Execution boundary

The project owner subsequently authorized M4 implementation. It was completed
locally within these boundaries:

- No EC2 or other paid AWS resource was launched.
- Bedrock was not invoked.
- The held-out split was not read, evaluated, copied, or rendered.
- M5's Evaluation tab and baseline work were not started.
- The required M4 implementation and acceptance cost was $0.

## Specification traceability

M4 covers the frontend requirements from sections 8 and 12 of the original
build specification:

- One page with two columns and plain custom styling; no brand logos or frontend
  framework.
- Left chat panel with a sender selector for Alex, Lea, and an editable third
  participant; a message list; visually distinct Lurker messages; emoji
  reactions attached to their target messages; an input; and a send button.
- Right dashboard with Live and About views first.
- Live view with the last decision, confidence bar, Decider latency, downgrade
  status/reason, exact counters, and a scrolling decision log.
- About view populated from the same typed question, options, and policy values
  the backend uses.
- A visible MOCK DECIDER banner whenever `/health` reports mock mode.
- Readable operation in a normal 1280-pixel-wide laptop browser and during a
  screen recording.
- Human acceptance: one person can play three participants and watch decisions
  appear live.

The full Evaluation tab remains an M5 deliverable. M4 may include its disabled
tab shell with an honest "Available after M5 evaluation" empty state, but it
must not call `/api/eval/latest`, show sample metrics, or touch held-out data.

## Fixed inputs and design constraints

- Frontend files: one `web/index.html`, one `web/styles.css`, and one
  `web/app.js` with no compilation or package-manager build step.
- Same-origin REST and WebSocket connections so the UI works locally and in the
  existing Docker image without environment-specific URLs.
- Existing provisional configuration remains context k = 3, reply threshold
  0.20, and REACT threshold 0.04.
- Existing WebSocket events remain authoritative: `chat`, `decision`,
  `reaction`, and `metrics`.
- The client does not invent or estimate counts, confidence, latency, actions,
  timestamps, or evaluation numbers.
- User-provided text is rendered with DOM `textContent`, never untrusted
  `innerHTML`.
- Tests and required acceptance run entirely in local MOCK mode. Mock mode must
  be unmistakable in the UI.
- The UI remains a synthetic one-room demo, with no authentication, private chat
  ingestion, database, third-party chat connector, or analytics service.

## Deliverables

| Deliverable | Purpose |
|---|---|
| `web/index.html` | Semantic two-column application shell, chat controls, dashboard tabs, empty/loading/error states |
| `web/styles.css` | Custom responsive styling, distinct action/message states, accessible focus and contrast, 1280px recording layout |
| `web/app.js` | Same-origin REST hydration, WebSocket client, event reducer, safe DOM rendering, sender editing, tabs, connection state |
| `src/lurker/api.py` updates | Serve `/` and static assets; expose a non-secret `/api/about` contract sourced from backend constants |
| `tests/test_m4_frontend.py` | Static route, About contract, security, and frontend contract tests |
| `M4_ACCEPTANCE.md` | Human checklist, real observed UI outputs, screenshots/evidence paths, limitations, and final owner decision |
| `data/m4_acceptance/<timestamp>/` | Acceptance summary, browser screenshot, and mock WebSocket transcript; no evaluation artifacts |
| `README.md` and `NOTES.md` updates | Copy-paste local launch steps, verified results, provenance, and limitations |

## Work packages

### 1. Static-serving and About contracts

- Mount the `web/` assets through FastAPI and serve `web/index.html` at `/`.
- Keep `/api/*`, `/health`, and `/ws` route behavior unchanged.
- Add `GET /api/about`, returning only non-secret values sourced from the same
  Python constants/config used by the running backend:
  - typed `QUESTION`;
  - ordered `OPTIONS` (`SILENT`, `REACT`, `REPLY`);
  - current context k and approved thresholds;
  - concise policy descriptions for confident and low-confidence outcomes;
  - whether direct mentions force a reply.
- Add cache headers suitable for a hackathon demo: HTML should revalidate;
  versionless assets should not be cached indefinitely.
- Confirm Docker's existing `COPY . .` includes `web/` and that the non-root
  runtime can read every asset.

### 2. Chat interface

- Build a sender selector with Alex, Lea, and a third participant whose display
  name can be edited without code changes.
- Render chat messages in arrival order and visually distinguish Lurker replies.
- Correlate reactions by `message_id` and render each emoji beneath its target
  message, including when events arrive close together.
- Validate non-empty messages, disable sending while disconnected or in flight,
  and support Enter to send without creating duplicate submissions.
- Let the server's `chat` echo create the visible message; do not optimistically
  render a second local copy.
- Keep the most recent message visible while respecting a user's manual scroll
  position where practical.

### 3. WebSocket lifecycle and state

- Derive `ws://` or `wss://` from the current page origin.
- Show explicit connecting, connected, disconnected, and error states.
- Route each event type through a small client-side reducer so rendering logic is
  deterministic and testable.
- Retain the last known UI state during a transient disconnect.
- Implement a bounded basic reconnect with backoff, while reserving formal
  reconnect failure drills and three-clean-replay evidence for M6.
- On initial load, hydrate `/health`, `/api/metrics`, and
  `/api/decisions?limit=50`; do not fabricate chat history that the backend does
  not expose.

### 4. Live dashboard

- Last-decision card:
  - final action with distinct SILENT/REACT/REPLY styling;
  - raw choice;
  - confidence as text and a 0-100% visual bar;
  - Decider latency in milliseconds;
  - downgraded yes/no plus exact reason;
  - mock/real marker.
- Counters with the exact backend labels and values:
  - messages read;
  - silent;
  - react;
  - reply;
  - Bedrock calls made;
  - bedrock calls avoided vs. every message.
- Scrolling newest-first decision log with time, sender/text excerpt, raw choice,
  confidence, and final action.
- Use neutral placeholders such as em dashes or "No decisions yet" until real
  event/API values exist. Never show sample numbers.
- Provide a guarded Reset demo button that calls `POST /api/reset`, clears only
  current UI state after success, and explains that historical JSONL is rotated,
  not deleted.

### 5. About and milestone boundaries

- Render the question, options, context setting, thresholds, and policy from
  `/api/about`; do not duplicate them in JavaScript.
- Explain SILENT, REACT, and REPLY in plain language.
- Explain that REACT is local and only REPLY may call Bedrock.
- Display the experimental/synthetic-data limitation and M1 provisional status.
- Include an Evaluation tab placeholder only if it clearly states that full
  evaluation is deferred to M5 and presents no metrics.

### 6. Accessibility and visual quality

- Use semantic landmarks, real form labels, buttons, and an ARIA live region for
  connection/decision updates.
- Ensure every control works by keyboard and focus remains visible.
- Do not communicate actions by color alone; include text labels/icons.
- Verify sufficient contrast, long-message wrapping, 200% browser zoom, and no
  horizontal overflow at 1280px.
- Use a compact responsive fallback below desktop width without compromising the
  required two-column 1280px recording layout.
- Respect `prefers-reduced-motion`; avoid decorative animation that obscures
  timing or state.

### 7. Evidence and documentation

- Add local MOCK launch instructions that open the UI at
  `http://127.0.0.1:8000/`.
- Save a timestamped M4 acceptance summary and screenshot under `data/`, not
  `results/`.
- Save only synthetic messages and no AWS/account identifiers.
- Record exact test counts and observed browser outputs in `M4_ACCEPTANCE.md` and
  `NOTES.md`.
- Preserve all M0-M3 evidence and configuration rollback files unchanged.

## Testing strategy

### Automated offline tests

All automated tests use injected `MockDecider` and `MockBedrockReplier`; they
must never load the real Decider or call AWS.

1. Static delivery:
   - `GET /` returns the application HTML;
   - CSS and JavaScript return 200 with correct content types;
   - missing assets return 404 without exposing filesystem paths;
   - existing REST/WebSocket routes remain reachable.
2. About provenance:
   - question/options exactly equal `decision_pattern.lurker_gate` constants;
   - thresholds/context equal the injected test config;
   - no model credentials, account identifiers, or environment secrets appear.
3. Browser-security contracts:
   - no external CDN/script/font dependency;
   - no unsafe `innerHTML`, `eval`, or hard-coded `ws://` production URL;
   - MOCK banner logic depends on `/health`, not a JavaScript constant.
4. WebSocket integration:
   - a plan message produces visible SILENT evidence without Bedrock;
   - a celebration produces REACT and an emoji under the correct message;
   - a question produces REPLY and a visually distinct mock Lurker message;
   - counters and decision log match the backend events exactly;
   - malformed messages produce a readable error without breaking the session.
5. Regression:
   - the existing 56-test suite and all new M4 tests pass;
   - Docker/static contract tests pass;
   - no test imports or opens the held-out scenario split.

### Human browser acceptance

Run locally in visible MOCK mode at 1280px and use one browser:

1. Select Alex and send `Let's meet at four tomorrow.`; verify chat echo plus a
   live SILENT decision card/log entry and no reaction/reply.
2. Select Lea and send `Great news, we passed!`; verify a REACT decision and a
   celebration emoji attached to Lea's message.
3. Rename the third participant to Sam, select Sam, and send
   `Can someone explain this API error?`; verify a REPLY decision and a distinct
   Lurker mock response.
4. Verify counters are 3 messages with one SILENT, one REACT, one REPLY, zero
   real Bedrock calls, and three calls avoided versus every message.
5. Verify the decision log contains all three messages and that confidence,
   latency, raw choice, and final action are direct event values.
6. Verify About exactly matches backend question/options/policy values.
7. Verify the MOCK DECIDER banner is persistent and unmistakable.
8. Verify keyboard-only sending, focus visibility, zoom behavior, and readable
   screen-recording layout.
9. Save the screenshot, transcript, summary, and human PASS/FAIL notes.

M4 is not complete until every automated check passes, the interactive browser
check is reviewed, and the project owner gives a final M4 GO.

## Acceptance criteria

- [x] One browser can act as Alex, Lea, and an editable third participant.
- [x] Chat messages are live and Lurker replies are visually distinct.
- [x] Emoji reactions attach to the correct target messages.
- [x] SILENT, REACT, and REPLY decisions appear live without invented values.
- [x] Last-decision card, confidence, latency, downgrade reason, counters, and
      decision log match backend events/API responses.
- [x] MOCK mode is visibly labeled whenever `/health` reports mock.
- [x] About content comes from backend constants/config.
- [x] The page is readable and operable at 1280px and by keyboard.
- [x] Existing plus new offline tests pass with zero AWS calls.
- [x] Browser acceptance evidence is saved under `data/m4_acceptance/`.
- [x] Held-out data remains untouched and M5 work has not started.
- [ ] Project owner records the final M4 GO.

## Expected costs

Required M4 implementation and acceptance are local and mock-only:

- EC2/EBS/public IPv4/load balancer: $0.
- Bedrock: $0.
- External frontend hosting/CDN/services: $0.
- Required estimated total: **$0**.

No AWS deployment is needed for M4 acceptance because M3 already proved the
real deployment path, and the original M4 gate is human frontend interaction.
If the owner later requests an optional deployed visual check, it requires a
new explicit approval and the same termination safeguards. At the M3-verified
$0.4032/hour rate, 10-15 minutes of `m7i.2xlarge` compute would be approximately
$0.0672-$0.1008, plus small EBS/public-IPv4 charges and any explicitly approved
Bedrock invocation. That optional check is not authorized by this plan.

## Remaining risks and mitigations

| Risk | M4 mitigation | Remaining boundary |
|---|---|---|
| Asynchronous events arrive close together | Correlate by message ID and use a deterministic reducer | Sustained concurrency is not proven |
| WebSocket disconnect loses events | Connection state, bounded reconnect, REST hydration for metrics/decisions | Formal reconnect drills are M6; chat history has no REST replay |
| UI accidentally invents metrics | Render only API/event values and explicit empty states | Full evaluation provenance is M5 |
| Mock output is mistaken for real evidence | Persistent MOCK banner and `mock` badges | Real end-to-end frontend replay is deferred unless separately approved |
| User text creates XSS | Use `textContent`, validation, and no external scripts | Public deployment still lacks authentication/rate limiting |
| About text drifts from policy | Fetch backend constants/config from `/api/about` | Threshold changes still require owner approval |
| Layout is hard to record | 1280px-first design and human screenshot review | Broader device/browser coverage is not production-grade |
| M4 scope leaks into M5 | Evaluation placeholder only; no eval API call or held-out access | M5 needs separate authorization |
| In-memory one-room state resets on restart | State this clearly in About/limitations | Durable storage is outside M4 |

## Proposed execution order after approval

1. Add failing static-route and About-contract tests.
2. Add FastAPI static serving and `/api/about` with no pipeline changes.
3. Build the semantic HTML shell and responsive CSS.
4. Implement REST hydration and WebSocket state/event handling.
5. Complete Live and About views, reset behavior, empty/error states, and MOCK
   labeling.
6. Run offline regression and container-static tests.
7. Start the local mock server and perform browser/accessibility acceptance.
8. Save evidence, update documentation, and stop for the owner's M4 GO decision.

No step above permits AWS deployment, real Bedrock calls, held-out access, M5
evaluation, or production-readiness claims without separate approval.
