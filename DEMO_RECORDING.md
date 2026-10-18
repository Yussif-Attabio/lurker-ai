# Automated demo recording

The Playwright recorder creates a repeatable, silent browser video from the
M7 shot list. It has two deliberately separate modes.

## Safe preview

The preview starts an isolated local server in MOCK mode, displays the MOCK
banner, uses a temporary decision log, reads only the published aggregate M5
result, and makes zero AWS or Bedrock calls.

```bash
npm install
npx playwright install ffmpeg
npm run demo:record:preview
```

The `.webm`, server log, and manifest are written under
`artifacts/demo-recordings/`, which is excluded from Git. The preview is not
submission eligible and must not be uploaded as if it were a real-Decider run.

For a quick workflow check, add `-- --pace 0.05`. The normal command uses
readable shot timing and records at 1440×900.

## Final real-service capture

Do not run final mode until the project owner separately authorizes exactly one
Bedrock call. The command refuses to start unless all safeguards below are
present. It starts the server locally, verifies the real Decider and frozen
`k=3 / reply 0.20 / react 0.04` policy, allows Bedrock only for the exact REPLY
prompt, runs once without retry, and requires a one-call metric delta.

```bash
DEMO_ALLOW_ONE_BEDROCK_CALL=I_APPROVE_ONE_CALL \
MOCK_DECIDER=false \
BEDROCK_MAX_CALLS=1 \
BEDROCK_ALLOWED_LATEST_TEXT='Lurker, please answer: why does the API return 401?' \
AWS_REGION=us-east-2 \
BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0 \
npm run demo:record:final
```

Final mode aborts on a wrong action, model/configuration mismatch, missing
reply, runtime error, MOCK banner, or Bedrock call count other than one. It
does not retry or silently substitute mock output.

## Narration and export

Playwright records the browser viewport without audio. Add the approved voice
track from `DEMO_SCRIPT.md` afterward with a local editor such as Cap, then
export MP4. Do not subtitle a predicted Bedrock response, add copyrighted
music, or include credentials, account identifiers, ARNs, IPs, or private chat.

Before public upload, verify the final file is under three minutes and that the
manifest reports `mode: final`, `status: pass`, `submission_eligible: true`,
`mock_banner_visible: false`, and `bedrock_call_delta: 1`.
