# Lurker AI demo script

Status: **LOCAL SHOT LIST - NOT RECORDED OR PUBLISHED**

Target runtime: **2 minutes 45 seconds maximum**. Use no third-party logos,
copyrighted music, private chat, mock output, or fabricated overlays.

## Recording gate

Record only with the real Decider active and the MOCK banner absent. A fresh
REPLY may make one paid Bedrock call and requires separate owner approval. Do
not launch AWS infrastructure unless separately authorized. Label preserved
evidence as recorded evidence rather than pretending it is live.

## Shot list

### 0:00-0:12 - Hook

**Screen:** Lurker AI title and empty synthetic chat.

**Voice:** “Most AI assistants are designed to answer. Lurker decides whether
it should answer at all.”

### 0:12-0:30 - The decision

**Screen:** About tab with the typed question and three options.

**Voice:** “A local Strands Decider model chooses SILENT, REACT, or REPLY. Only
REPLY is allowed to call Amazon Bedrock.”

### 0:30-0:52 - SILENT

Send: `Let's meet at four tomorrow.`

Show the real decision. Voice: “That is a routine plan, so Lurker stays silent.
The decision is logged, but no model writes a message.”

### 0:52-1:14 - REACT

Send: `Congratulations everyone—we made the hackathon finals! 🎉`

Show the real REACT and local emoji. Voice: “Good news deserves acknowledgment,
not another paragraph. Bedrock is still not called.”

### 1:14-1:45 - REPLY

Send: `Lurker, please answer: why does the API return 401?`

Show the real REPLY and actual Bedrock response. Never subtitle a predicted
response. Voice: “This is a direct unanswered request. Decider selects REPLY,
and only now does Claude Haiku generate a short answer.”

### 1:45-2:05 - Measured behavior

Show counters, decision log, and preserved M6 summary. Voice: “Three final
acceptance replays made three Bedrock calls for nine messages, avoided six
calls versus replying to everything, and recorded zero errors or duplicates.”

### 2:05-2:25 - Reusable pattern

Show `decision_pattern/README.md`, `QUESTION`, `OPTIONS`, `ChimeInGate`, and
`ChimeInIntervention`. Voice: “The reusable pattern includes the typed question,
confidence gate, and official Strands intervention wiring.”

### 2:25-2:45 - Honest close

Show the Evaluation tab. Voice: “Deployment reliability passed, but the
original held-out evaluation did not: accuracy was 66.7%, and unnecessary
interruption was 66.7%. Lurker is an experiment in knowing when to help—and
when to leave the conversation alone.”

## Post-recording checks

- Runtime is below 3:00; target no more than 2:45.
- No MOCK banner; each action matches a real event.
- REPLY text is the actual recorded Bedrock output.
- Metrics match preserved JSON evidence.
- No account number, ARN, IP, credential, secret, key, or private chat appears.
- No third-party logo or copyrighted music appears.
- Upload publicly to YouTube, Vimeo, Facebook Video, or Youku.
- Add the public video URL to the article and checklist.
