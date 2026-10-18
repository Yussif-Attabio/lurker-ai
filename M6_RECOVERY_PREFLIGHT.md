# M6 recovery deployment preflight

Status: **NO-GO - EFFECTIVE SCP CLEARANCE NOT ESTABLISHED**

Checked: 2026-10-18

## Recommendation

Do not authorize the recovery deployment yet. Every directly verifiable
capacity, price, profile, identity-policy, and static safeguard gate passes,
but effective AWS Organizations service control policy clearance remains
unknown. This account is an Organizations member account, not the management
account, and its current administrative identity is denied the read operations
needed to inspect account, parent-OU, and root SCPs. Permission is not assumed.

The approved no-invocation alternative is a dated, redacted export or written
attestation from an Organizations management-account administrator confirming
that `bedrock:InvokeModel` is permitted for the `us-east-2` profile call and
the profile's model evaluations in `us-east-1`, `us-east-2`, and `us-west-2`.
Exact instructions are in `M6_SCP_CLEARANCE_REQUEST.md`.

If organization inspection cannot be obtained, the only conclusive alternative
is a separately authorized one-call runtime canary from the exact corrected
temporary role. That would be a real Bedrock invocation and is outside the
current authorization.

## Verification matrix

| Gate | Result | Evidence |
|---|---|---|
| Effective SCP clearance | **BLOCKED** | Member account; Organizations list/read calls denied |
| `m7i.2xlarge` availability | PASS | Offered in `us-east-2` |
| Standard On-Demand quota | PASS | 16 vCPUs available; instance needs 8 |
| Haiku inference profile | PASS | ACTIVE, system-defined |
| Profile destinations | PASS | `us-east-1`, `us-east-2`, `us-west-2` |
| Haiku request quota | PASS | 10 requests/minute; recovery needs at most 3 total |
| Haiku token quota | PASS | 5,000,000 tokens/minute |
| Corrected role policy | PASS in isolation | Zero Access Analyzer findings; all four exact resources simulate `allowed` |
| Least privilege | PASS | Only `bedrock:InvokeModel`; no wildcards, streaming, control-plane, or admin access |
| 50-minute shutdown script | PASS statically | Valid shell; one `--on-active=50m` timer and shutdown command |
| Runtime timer active | Launch-time gate | Must be verified active before tests; stop and terminate otherwise |
| Terminate-on-shutdown | Launch-time gate | Must be set and read back before tests |
| Cost ceiling | PASS | `$0.44976` guarded estimate below `$0.55` |
| Evidence preservation | PASS | Original M6/M5 hashes unchanged |

## Refreshed prices and estimate

Read-only AWS Price List queries reconfirmed:

- Ohio Linux `m7i.2xlarge`: `$0.4032/hour`;
- Ohio gp3 storage: `$0.08/GB-month`;
- one in-use public IPv4: `$0.005/hour`.

The current AWS Bedrock material lists US geographic Claude Haiku 4.5 at
`$1.10/million` input tokens and `$5.50/million` output tokens. The public AWS
Price List API currently exposes older Anthropic catalog entries but not Haiku
4.5, so the Bedrock rate is sourced from AWS's live Bedrock pricing material
and AWS-published Haiku 4.5 regional pricing table rather than that API.

For 50 minutes:

| Item | Guarded amount |
|---|---:|
| EC2 | `$0.336000` |
| Encrypted 40-GB gp3 | `$0.003653` |
| Public IPv4 | `$0.004167` |
| Three Bedrock calls | `$0.005940` conservative allowance |
| Subtotal | `$0.349760` |
| Operational contingency | `$0.100000` |
| Guarded total | **`$0.449760`** |
| Hard ceiling | **`$0.550000`** |

No credit is assumed. A normal 15-minute run is estimated near `$0.1042`, but
the AWS bill is authoritative.

Official references:

- `https://aws.amazon.com/ec2/pricing/on-demand/`
- `https://aws.amazon.com/ebs/pricing/`
- `https://aws.amazon.com/vpc/pricing/`
- `https://aws.amazon.com/bedrock/pricing/`
- `https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html`

## IAM result

The corrected policy remains the smallest suitable role permission:

1. unconditional `bedrock:InvokeModel` on the exact account-scoped Ohio
   inference profile; and
2. `bedrock:InvokeModel` on the three exact foundation-model ARNs, with
   `bedrock:InferenceProfileArn` equal to the approved profile.

The profile resource simulated `allowed`; each model resource simulated
`allowed` with the exact profile context; Access Analyzer returned no findings;
and five offline policy/frozen-contract tests passed. This proves the identity
policy in isolation, not the missing SCP layer.

## Safeguard result

`deploy/m6_ec2_bootstrap.sh` is syntactically valid and installs an independent
systemd shutdown timer at exactly 50 minutes. The launch procedure also requires
instance-initiated shutdown behavior `terminate`, encrypted delete-on-
termination gp3 storage, IMDSv2, `/32` inbound access, constrained outbound
traffic, a three-call server cap, and no retries.

Because no instance exists, timer activation and terminate-on-shutdown cannot
yet be runtime-confirmed. They remain mandatory post-launch/pre-test checks:
any failure requires immediate termination before a model call.

## Preserved status

No EC2 instance was launched, no IAM policy was changed, no Bedrock model was
invoked, no replay was run, and no protected evaluation data was accessed.
Incremental cost is `$0`. The original failed deployment remains preserved and
M6 remains **NO-GO**. M5's frozen configuration and model-performance NO-GO are
unchanged; production readiness is not claimed.
