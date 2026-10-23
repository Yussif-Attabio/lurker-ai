# Milestone M3 acceptance

Status: **FINAL GO - PROJECT-OWNER APPROVED 2026-10-16**

## Final owner decision

The project owner approved Milestone M3 as a final GO on 2026-10-16 based on
the successful controlled AWS deployment acceptance. This approval permits
planning for M4; it is not production-readiness approval and does not authorize
new AWS resources or M4 implementation.

## Local preparation

- [x] Official Decider CPU/GPU serving requirements reviewed.
- [x] CPU-first EC2 candidate selected and documented.
- [x] Dockerfile added with CPU-only PyTorch installation.
- [x] Container runs as a non-root user and has a real health check.
- [x] Runtime and evidence directories excluded from the image context.
- [x] Decider dependency pinned to the source revision proven in M0-M2.
- [x] External one-decision acceptance script added.
- [x] Docker image built successfully for `linux/amd64`.
- [x] Container `/health` verified locally in safe MOCK mode.
- [x] SILENT, REACT, and REPLY passed through the local container WebSocket.
- [x] Complete offline suite passes inside the amd64 image (56 tests).
- [x] Container dependency check reports no broken requirements.
- [x] Planned 32 GiB memory is compatible with the measured deployed peak.

## Owner-approved deployment controls

- Region: `us-east-2`.
- Instance: one On-Demand `m7i.2xlarge` (8 vCPUs, 32 GiB), Linux amd64.
- Spending boundary: at most one hour and $0.50 EC2 compute, plus the approved
  small EBS, public IPv4, bandwidth, and Bedrock charges.
- Automatic termination: EC2 instance-initiated shutdown behavior was
  `terminate`, backed by an active 50-minute systemd shutdown timer.
- Network: inbound TCP 22 and 8000 only from the controlling Mac's current
  public IPv4 `/32`; outbound HTTPS, VPC DNS, and Amazon Time Sync only.
- IAM: the temporary instance role allowed `bedrock:InvokeModel` only for the
  approved Claude Haiku 4.5 inference profile and its three destination model
  ARNs, constrained by the inference-profile ARN. No static AWS credentials
  were copied to the host.
- Storage: one encrypted 40 GiB gp3 root volume with delete-on-termination.
- No load balancer, NAT gateway, Elastic IP, database, S3 bucket, ECR
  repository, GPU, or additional instance was created.

All controls were confirmed before the application image was run.

## Real deployment acceptance - 2026-10-16

- [x] Project owner explicitly approved the maximum duration and estimated spend.
- [x] AWS CLI session authenticated without recording identity fields.
- [x] `m7i.2xlarge` was available and the 16-vCPU quota covered the required 8.
- [x] Claude Haiku 4.5 inference profile status was active.
- [x] Exactly the approved EC2, EBS, security-group, key-pair, and instance-role
      resources were launched.
- [x] Deployed `/health` was reachable from outside the instance.
- [x] `/health` reported `decider_mode=real` and `model_ready=true`.
- [x] One real Decider decision succeeded through the deployed WebSocket pipeline.
- [x] The acceptance case made zero Bedrock calls.
- [x] Real external transcript, latency, hardware, and errors were saved under
      `data/archive/cloud_deployment_acceptance/20261016T194448Z/`.
- [x] The instance was terminated immediately after evidence collection.
- [x] Temporary infrastructure was deleted and a zero-resource cleanup check passed.
- [x] No held-out scenario or M5 result was accessed.

Acceptance result:

| Check | Result |
|---|---|
| Health | `status=ok`, real Decider, model ready |
| Input | `Let's meet at four tomorrow.` |
| Raw/final decision | `SILENT` / `SILENT` |
| Confidence | 0.4553 |
| Real Decider latency | 1,279.03 ms |
| Bedrock calls | 0 |
| Runtime errors | 0 |
| OOM killed | no |

Memory evidence:

| Measurement | Result |
|---|---:|
| Container cgroup current | 13,243,207,680 bytes (12.33 GiB) |
| Container cgroup peak | 13,260,681,216 bytes (12.35 GiB) |
| Main-process high-water RSS | 11,881,908 KiB (11.33 GiB) |
| Container limit | 25,769,803,776 bytes (24 GiB) |
| Instance memory | 32 GiB |
| Peak headroom under container limit | 11.65 GiB |
| Peak headroom against instance memory | 19.65 GiB |

The instance launched at `2026-10-16T19:38:23Z` and termination completed at
`2026-10-16T19:46:19Z`, a 7 minute 56 second paid window. At the verified
$0.4032/hour On-Demand rate, estimated EC2 compute is approximately $0.0533.
Ancillary EBS/public-IPv4 charges should be well under one cent for this window;
the AWS bill is authoritative once usage data settles. Bedrock cost for this
acceptance case is $0 because it made no invocation.

Post-run verification found zero active run-scoped instances, volumes, security
groups, key pairs, Elastic IPs, NAT gateways, snapshots, IAM roles, or instance
profiles. The temporary SSH private key was deleted from the Mac.

## Evidence and limitations

- Summary: `data/archive/cloud_deployment_acceptance/20261016T194448Z/summary.json`.
- WebSocket transcript:
  `data/archive/cloud_deployment_acceptance/20261016T194448Z/websocket_transcript.json`.
- Infrastructure/memory record:
  `data/archive/cloud_deployment_acceptance/20261016T194448Z/deployment_measurements.json`.
- Local amd64 preparation:
  `data/archive/container_verification/20261016T190727Z/summary.json`.

This was one short, single-user, single-decision deployment check. It does not
establish production security, availability, concurrency, autoscaling, durable
storage, sustained-load behavior, or production cost. M1 remains provisional,
and the original held-out dataset stays locked until M5. M4 has not begun.

Every technical M3 acceptance requirement passed, and the project owner issued
the final M3 GO. M3 proves controlled deployment viability only. It does not
prove production readiness, high availability, concurrency, autoscaling,
durable storage, or sustained-load performance.

## Post-approval cleanup confirmation

A read-only AWS inventory check after final approval reconfirmed that the M3
run has zero active instances, volumes, security groups, key pairs, Elastic IPs,
NAT gateways, IAM roles, or instance profiles. A broader `us-east-2` check also
found zero active EC2 instances or volumes, Elastic IPs, NAT gateways, load
balancers, or RDS instances. No new resources were launched by this check.
