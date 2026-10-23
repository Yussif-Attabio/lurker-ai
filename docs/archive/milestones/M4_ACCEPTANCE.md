# Milestone M4 acceptance

Status: **FINAL GO - PROJECT-OWNER APPROVED 2026-10-16**

## Final owner decision

The project owner manually retested the updated frontend, confirmed that it is
working correctly, and approved Milestone M4 as a FINAL GO on 2026-10-16. This
approval includes the post-acceptance mock question/reaction correction and the
complete 76-test offline regression suite.

M4 is complete. The approval establishes frontend and local-demo viability; it
does not establish production readiness, authentication, durable history,
multi-room isolation, sustained load, high availability, or failure recovery.
It authorizes M5 planning only and does not itself authorize held-out evaluation,
real-model execution, Bedrock calls, or paid AWS resources.

## Scope and boundaries

M4 implemented the original specification's one-page frontend: a
three-participant synthetic chat on the left and Live/About decision views on
the right. Work stayed local and mock-only.

- AWS resources launched: 0.
- Bedrock calls: 0.
- Required cost: $0.
- Held-out dataset accessed: no.
- M5 implementation started: no.
- Existing model, architecture, context, and provisional thresholds changed:
  no.

## Delivered

- `web/index.html`: semantic one-page chat and decision-console shell.
- `web/styles.css`: custom laptop-first and responsive styling with visible
  focus, readable action states, and reduced-motion support.
- `web/app.js`: same-origin REST/WebSocket client, deterministic event state,
  reactions, decision dashboard, editable third participant, reset, reconnect,
  keyboard sending, and safe text rendering.
- FastAPI now serves `/` and `/assets/*` and exposes `/api/about` from the same
  backend question, options, policy descriptions, and configuration.
- `tests/test_m4_frontend.py`: local static, policy-provenance, safety, and
  three-action WebSocket contracts.

The Evaluation tab is visibly deferred to M5. It does not call
`/api/eval/latest`, show sample metrics, or read evaluation scenarios.

## Browser acceptance - PASS - 2026-10-16

The completed local page was exercised in the real in-app browser at the target
1280x900 viewport:

| Participant | Message | Browser result |
|---|---|---|
| Alex | `Let's meet at four tomorrow.` | SILENT displayed live; no reaction/reply |
| Lea | `Great news, we passed!` | REACT displayed live; 🎉 attached to Lea's message |
| Sam (editable third participant) | `Can someone explain this API error?` | REPLY displayed live; distinct mock Lurker reply |

After the required three-message flow, the browser showed exact counters of 3
messages, 1 SILENT, 1 REACT, 1 REPLY, 0 Bedrock calls, and 3 calls avoided versus
every message. The decision log contained all three messages newest-first.

Additional browser checks:

- MOCK DECIDER banner: visible and persistent.
- About question/options: exact backend values.
- About configuration: k=3, reply threshold 0.20, REACT threshold 0.04, direct
  mention override disabled.
- 1280px horizontal overflow: none.
- 640px zoom-equivalent horizontal overflow: none.
- Keyboard-only Enter send: PASS with a fourth synthetic SILENT message.
- Browser console warnings/errors: 0.
- External CDN, font, script, or analytics requests: none.
- User text rendering: DOM `textContent`; no unsafe `innerHTML` or `eval`.

The fourth keyboard-only message brought final local counters to 4 messages, 2
SILENT, 1 REACT, 1 REPLY, 0 Bedrock calls, and 4 avoided calls. The three-case
checkpoint above is preserved separately in the acceptance summary and
screenshot.

## Automated and packaging verification

- Initial pre-fix offline suite: 61 passed.
- Post-fix complete offline suite: 76 passed.
- Python dependency check: no broken requirements.
- JavaScript syntax check: PASS.
- Unsafe/external frontend-pattern scan: PASS.
- Linux amd64 image: `lurker-ai:m4-amd64`.
- Image ID:
  `sha256:7a139786fa86601577d340d1e8467c068b3cc843fab905199f3ec0dd049f672f`.
- Safe local mock-container check: `/`, `/health`, frontend JavaScript, and
  `/api/about` PASS; temporary container removed immediately.

The pytest cache warning is environmental only: the sandbox could not write
`.pytest_cache`; it did not affect any test result.

## Evidence

- Summary: `data/archive/frontend_acceptance/20261016T213850Z/summary.json`.
- Browser transcript:
  `data/archive/frontend_acceptance/20261016T213850Z/browser_transcript.json`.
- 1280px screenshot:
  `data/archive/frontend_acceptance/20261016T213850Z/live-dashboard-1280.jpg`.

## Remaining limitations

M4 proves that one person can operate the synthetic three-participant chat and
watch live decisions in a normal laptop browser. It does not establish
production readiness, authentication, multi-room isolation, durable chat
history, sustained concurrency, high availability, or reconnect reliability
under failure. Formal failure drills remain M6 work.

M1 remains provisional. Full context comparison, threshold tuning, baselines,
held-out evaluation, and the populated Evaluation tab remain M5 work and require
separate approval.

Every technical M4 acceptance check passed. The project owner's subsequent
manual retest and FINAL GO are recorded in the final decision above.

## Mock decision regression fix - 2026-10-16

A post-acceptance local investigation confirmed that `MockDecider` treated any
message containing `?` as REPLY and otherwise did not recognize shipping or the
celebration emoji as REACT signals. The mock now uses deterministic,
meaning-oriented heuristics: common question openers and direct help requests
are recognized without requiring question-mark punctuation, while gratitude,
humor, and celebration/achievement language can produce REACT. Questions retain
priority over reaction signals.

Verified regressions include:

- `is 401 safe` and `is 401 safe?`: REPLY.
- `We finally shipped the project! 🎉`: REACT.
- Ordinary declarative messages, including `I know how the API works.`: SILENT.
- A celebratory question such as `Did we finally ship the project 🎉`: REPLY.

The complete offline suite now has 76 passing tests. No real Decider threshold,
model, architecture, or policy was changed. AWS and Bedrock usage remained zero,
and the held-out evaluation dataset was not accessed.

## Final M4 acceptance summary

- Technical browser acceptance: PASS.
- Project-owner manual retest after the mock regression fix: PASS.
- Offline regression suite: 76 passed.
- Project-owner decision: FINAL GO.
- AWS resources and Bedrock calls for M4: 0.
- Held-out evaluation access during M4: 0.
- Remaining limitations: unchanged and carried forward to M5-M7.
