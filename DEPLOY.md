# AWS deployment plan

Status: **M3 local skeleton ready; AWS deployment not started**

No EC2 instance, EBS volume, load balancer, container registry, or other paid
resource has been created. The project owner must explicitly approve the
estimated spend before the real M3 deployment acceptance run.

## Selected compute candidate

Use one Linux `m7i.2xlarge` EC2 instance in `us-east-2` for the first controlled
deployment:

- 8 x86-64 vCPUs
- 32 GiB system memory
- CPU Decider inference (`DECIDER_DEVICE=cpu`)
- 40 GiB encrypted gp3 root volume
- On-Demand only; no long-term commitment

The official Strands Decider inference guide supports Linux CPU serving and
documents an approximately 1.6-second v21 ask on a Xeon CPU using eight threads.
It also states that the Qwen3.5 2B base download is about 4.5 GB. A GPU is
therefore not required for M3's one-health-check/one-decision acceptance gate.
The selected instance provides eight vCPUs and enough memory headroom for model
weights, model loading, the FastAPI process, and Docker.

Official references:

- https://github.com/strands-labs/strands-decider/blob/main/docs/inference.md
- https://github.com/strands-labs/strands-decider
- https://aws.amazon.com/ec2/instance-types/m7i/
- https://docs.aws.amazon.com/ec2/latest/instancetypes/ec2-instance-regions.html

The previous provisional `g6.2xlarge` recommendation is preserved as a fallback,
not the default. It has an NVIDIA L4 GPU and should be considered only if the
deployed CPU measurement is too slow for the demo. Changing to it requires a
separate owner cost decision.

## Cost boundary

The current planning estimate for Linux On-Demand `m7i.2xlarge` in Ohio is
**$0.4032 per running hour**, billed per second after the minimum. A controlled
deployment lasting one hour should therefore stay below **$0.50 of EC2 compute**.
The 40 GiB gp3 volume, public IPv4 address, outbound model downloads, and any
Bedrock invocation are separate small charges. The instance and volume should be
terminated immediately after evidence is saved unless the owner explicitly asks
to retain them.

The authenticated AWS Price List API confirmed **$0.4032 per hour** on
2026-10-16. Pricing should still be checked immediately before launch in case it
changes.

## Local container

`Dockerfile` uses Python 3.12, the official CPU-only PyTorch wheel, and the exact
Strands Decider source revision already exercised in M0-M2. It runs the API as a
non-root `lurker` user and includes a real `/health` container check.

Build and run locally when Docker is available:

```bash
docker buildx build --platform linux/amd64 --load \
  --tag lurker-ai:m3-amd64 .
docker run --rm --publish 8000:8000 \
  --env MOCK_DECIDER=true \
  --env LURKER_DATA_DIR=/app/data \
  lurker-ai:m3-amd64
```

Then verify:

```bash
curl --fail http://127.0.0.1:8000/health
```

The `linux/amd64` image was built successfully on the Apple Silicon Mac with
Docker buildx. Safe MOCK-mode verification passed `/health`, all three WebSocket
actions, and the full 56-test suite inside the amd64 image. The fully
materialized image is 1,908,564,122 bytes and runs as non-root UID 999.

Docker Desktop exposes 7.75 GiB to its Linux VM. The same pinned real Decider CPU
loader measured 8.46 GiB peak RSS natively, so forcing a real CPU load inside the
cross-architecture local container would exceed the Docker VM budget. The planned
32 GiB instance has about 23.54 GiB headroom over that measured peak. Native Linux
amd64 peak RSS must still be recorded during deployed acceptance.

## Planned AWS resources

Only these resources are in scope for the controlled M3 run:

1. One `m7i.2xlarge` EC2 instance in `us-east-2`.
2. One 40 GiB encrypted gp3 root volume.
3. One security group with TCP 8000 restricted to the tester's current public IP.
4. One EC2 instance role containing:
   - the minimum Systems Manager permissions needed to administer the instance;
   - `bedrock:InvokeModel` only for the approved Claude Haiku 4.5 inference
     profile/model resources.

There will be no database, GPU, load balancer, NAT gateway, permanent container
registry, or embedded AWS access keys. Port 22 should remain closed; use Systems
Manager for administration.

## Runtime configuration

The deployed container must receive configuration at runtime, never in the image:

```text
AWS_REGION=us-east-2
BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
DECIDER_DEVICE=cpu
CONTEXT_K=3
REPLY_THRESHOLD=0.20
REACT_THRESHOLD=0.04
FORCE_REPLY_ON_MENTION=false
MOCK_DECIDER=false
LURKER_DATA_DIR=/app/data
LURKER_RESULTS_DIR=/app/results
```

For the one M3 SILENT acceptance case, set `BEDROCK_ALLOWED_LATEST_TEXT` to a
non-matching guard value. This prevents an unexpected REPLY classification from
invoking Bedrock. No held-out evaluation data is used.

## Required preflight after AWS login

These are read-only checks. Do not launch anything if any check fails:

```bash
aws sts get-caller-identity --query 'Arn' --output text
aws configure get region
aws ec2 describe-instance-type-offerings \
  --region us-east-2 \
  --location-type region \
  --filters Name=instance-type,Values=m7i.2xlarge
aws service-quotas get-service-quota \
  --region us-east-2 \
  --service-code ec2 \
  --quota-code L-1216C47A
aws bedrock get-inference-profile \
  --region us-east-2 \
  --inference-profile-identifier \
  us.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --query status --output text
```

Suppress account identifiers when recording the results. The standard On-Demand
instance quota must allow at least eight vCPUs.

## M3 acceptance procedure

1. Obtain explicit owner approval for the estimated maximum duration and cost.
2. Reauthenticate the AWS CLI and pass every read-only preflight.
3. Launch only the resources listed above and start the real container.
4. From the Mac, confirm public `/health` reports `real` and `model_ready=true`.
5. Run one deployed SILENT decision from outside the instance:

   ```bash
   PYTHONPATH=. python scripts/smoke_deployed.py \
     --base-url http://DEPLOYED_HOST:8000
   ```

6. Save the external transcript, real Decider latency, instance type, image
   identifier, and any errors under `data/deployment_acceptance/<timestamp>/`.
7. Stop or terminate the instance immediately after the evidence is collected.
8. Mark M3 complete only if every item in
   `docs/archive/milestones/M3_ACCEPTANCE.md` passes.

## Security and reproducibility constraints

- Never put AWS access keys, login tokens, or account identifiers in the repo,
  image, user data, logs, or screenshots.
- Pin the deployment to the Decider source revision in `requirements.txt`.
- Do not expose the Decider package's own unauthenticated server; expose only the
  Lurker FastAPI application for this short acceptance run.
- Restrict port 8000 to the tester's IP and terminate the instance after use.
- Final reported deployment latency must come from the deployed instance, not
  from upstream benchmarks or the local Mac.
- Keep the M5 held-out scenarios untouched.
