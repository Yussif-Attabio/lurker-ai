# Milestone M2 acceptance

Status: **PASS - M2 COMPLETE**

## Implemented locally

- [x] Validated configuration and startup guards
- [x] Real Decider adapter remains the sole Decider import boundary
- [x] Deterministic `MockDecider` for UI work and tests
- [x] Bounded one-room context
- [x] Shared confidence policy using the provisional M1 thresholds
- [x] Local emoji reactor
- [x] Bedrock Converse replier with latency and token accounting
- [x] Background SILENT / REACT / REPLY pipeline
- [x] Append-only JSONL event store, counters, and p50/p95 latency
- [x] REST API contract
- [x] WebSocket API contract
- [x] Guarded scripted WebSocket acceptance client

## Verified evidence

- Offline tests: **49 passed**
- Dependency check: **PASS**
- MOCK uvicorn startup: **PASS**
- MOCK `/health` and `/api/metrics`: **PASS**
- MOCK WebSocket actions: **SILENT, REACT, REPLY**
- Real Decider invoked during final acceptance: **yes, locally on CPU**
- Bedrock invoked during final acceptance: **yes, exactly once**
- Paid AWS resources launched: **no**
- Held-out dataset evaluated: **no**

## Real-service acceptance - PASS - 2026-10-16

- Execution environment: local Mac, real Decider on CPU
- AWS Region: `us-east-2`
- Bedrock model: `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- Policy: context k = 3, reply threshold 0.20, REACT threshold 0.04
- `/health`: real mode, model ready
- Hard Bedrock budget: one invocation
- Exact-message guard: only the approved final REPLY message could invoke
  Bedrock

| Expected | Raw choice | Confidence | Final action | Decider latency | Bedrock called | Error |
|---|---|---:|---|---:|---|---|
| SILENT | SILENT | 0.4553 | SILENT | 1068.28 ms | no | none |
| REACT | REACT | 0.2398 | REACT | 599.78 ms | no | none |
| REPLY | REPLY | 0.3842 | REPLY | 688.56 ms | yes | none |

Real Bedrock response:

> I'm not sure—I haven't seen the API error logs or recent code changes. Have
> you checked if the authentication token might be expired?

- Bedrock latency: 1072.45 ms
- Input tokens: 159
- Output tokens: 32
- Bedrock calls made: 1
- Bedrock calls avoided versus every message: 2
- Decider latency p50: 688.56 ms
- Decider latency p95: 1030.31 ms
- Downgraded decisions: 0
- Errors: 0
- Evidence directory: `data/m2_acceptance/20261016T071233Z/`

All M2 acceptance requirements pass. M2 is complete.

## Scope limitation

This checkpoint is not production-readiness approval and does not authorize an
AWS compute instance, deployment, load balancer, or any other paid resource.
It is one controlled synthetic local run, not a reliability, load, security, or
deployment assessment. The held-out evaluation dataset remains locked until M5.
