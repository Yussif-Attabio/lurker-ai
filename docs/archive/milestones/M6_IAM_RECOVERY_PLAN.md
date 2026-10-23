# M6 IAM recovery investigation and deployment plan

Status: **OFFLINE DIAGNOSIS COMPLETE - NO DEPLOYMENT AUTHORIZED**

Prepared: 2026-10-18

## Preserved outcome

The deployed M6 acceptance remains **NO-GO**. Its original configuration,
replay, redacted and private error evidence, measurements, cleanup record, and
cost record remain unchanged under `data/m6_acceptance/20261018T192248Z/`.
This investigation does not alter M5's model-performance NO-GO, does not access
protected evaluation data, and does not imply production readiness.

## Exact failure

The preserved redacted exception identifies:

- denied action: `bedrock:InvokeModel`;
- denied resource: the account-scoped system inference profile
  `arn:aws:bedrock:us-east-2:<ACCOUNT_ID>:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0`;
- principal: the temporary M6 EC2 instance role session (identifiers retained
  only in the private raw evidence);
- authorization reason: no identity-based policy allowed the action.

The failed REPLY made one provider attempt, received no input/output token
counts, generated no assistant reply, and was not retried. Replays 2 and 3 did
not start.

## Root cause

CloudTrail reconstruction confirms that the deleted role had one inline Allow
for `bedrock:InvokeModel`. It listed the correct Ohio inference profile and the
three current foundation-model destinations (`us-east-1`, `us-east-2`, and
`us-west-2`). However, the statement placed an
`bedrock:InferenceProfileArn` condition on **every** resource in the statement.

AWS does not populate that condition key while it evaluates the inference
profile resource. It populates the key only for the foundation-model resource
evaluations. The condition therefore failed for the profile itself, making the
only Allow inapplicable. This exactly matches the runtime message that no
identity-based policy allowed `bedrock:InvokeModel` on the profile.

The destination list was complete, but those model resources were also inside
the unusable combined statement. This is a policy-structure defect, not a
missing model Region, quota failure, credential failure, or Decider failure.

## Deny-layer review

- **Role identity policy:** one Allow, no explicit Deny. The condition-placement
  defect explains the implicit identity-policy denial.
- **Permissions boundary:** the CloudTrail `CreateRole` request and response
  contain no permissions boundary. None was applied to the temporary role.
- **Managed/session policies:** no managed policy attachment was observed. The
  EC2 instance profile assumed the role through the EC2 service; no custom STS
  session policy was supplied by the application.
- **SCP:** the account is in AWS Organizations, but the current administrative
  identity cannot list parents or attached SCPs. The original exception names
  an identity-policy implicit denial, not an SCP explicit/implicit denial, so
  an SCP is not the diagnosed cause. It cannot be conclusively ruled out for a
  corrected future request without an Organizations administrator check.
- **Resource/VPC endpoint policies:** no Bedrock VPC endpoint was deployed, and
  the call used the public Bedrock endpoint. No resource-based policy was part
  of the temporary profile setup.

## Smallest appropriate correction

Use `deploy/m6_bedrock_invoke_policy.template.json` after replacing
`<ACCOUNT_ID>` locally at deployment time:

1. An unconditional Allow for only `bedrock:InvokeModel` on the exact
   account-scoped Ohio inference-profile ARN.
2. A separate Allow for only `bedrock:InvokeModel` on the exact three
   foundation-model ARNs, conditioned with `ArnEquals` so they can be invoked
   only through that exact profile.

The candidate grants no Bedrock administrator, streaming, model-management,
wildcard-action, or wildcard-resource access. `Converse` uses
`bedrock:InvokeModel`, so no additional action is required for this test.

## Verification completed without mutation or inference

- Read-only `GetInferenceProfile` reconfirmed the exact three destination model
  ARNs in `us-east-1`, `us-east-2`, and `us-west-2`.
- CloudTrail reconstructed the deleted role and original inline policy; the
  role creation had no permissions boundary.
- Offline regression checks assert exact action, profile, destination list,
  split-statement shape, required condition, and absence of broad grants.
- AWS Access Analyzer validation and IAM simulation results are recorded in
  `data/m6_iam_recovery/20261018T195306Z/verification.json`.
- Original M6 and frozen M5 artifact hashes are recorded before and after the
  investigation to prove they were not modified.

The simulator validates the candidate identity policy in isolation. It cannot
prove that an inaccessible SCP will allow the future runtime call; that must be
cleared as a deployment preflight gate.

## Recovery deployment procedure (not authorized yet)

1. Reconfirm current AWS identity, `us-east-2`, instance availability, 16-vCPU
   quota, profile ACTIVE status, destination ARNs, current official prices, and
   a gross estimate below `$0.55` without relying on credits.
2. Obtain an Organizations administrator statement or policy-inspection result
   confirming that `bedrock:InvokeModel` is not denied for the Ohio source and
   all three US destination Regions. Stop before launch if this cannot be
   cleared.
3. Render `<ACCOUNT_ID>` only into a temporary local policy file. Run JSON
   parsing, the offline policy tests, AWS Access Analyzer validation, and IAM
   simulation. Require every exact resource to evaluate `allowed` and reject
   any warning, wildcard, or unexpected action.
4. Create one new tagged temporary role and instance profile with no permissions
   boundary unless an approved boundary explicitly allows the same resources.
   Attach only the corrected inline policy. Read the role back and compare its
   canonical policy hash to the validated temporary file.
5. Launch one temporary `m7i.2xlarge` in `us-east-2`: 50-minute independent
   termination timer, terminate-on-shutdown, IMDSv2, encrypted 40-GiB gp3 root
   volume deleted on termination, controller IPv4 `/32` inbound access, and the
   previously minimized outbound rules. Copy no static AWS credentials.
6. Run deterministic timeout/error/reconnect drills with networking disabled,
   then destroy and restart the disposable container after the timeout drill.
7. Use a fresh real container with the frozen `k=3`, REPLY `0.20`, REACT `0.04`
   configuration. Run exactly three consecutive public demo replays, with a
   server-side cap of three Bedrock calls. Preserve any failure, do not retry,
   and stop the sequence immediately on the first error.
8. Record actions, confidences, Decider/Bedrock latency, token usage, memory,
   errors, duplicates, call counts, and cost. M6 passes only if all three
   replays produce SILENT/REACT/REPLY, exactly three successful calls total,
   zero errors, and zero duplicates.
9. Terminate immediately after evidence collection. Delete the volume, security
   group, key pair, role policy, role, instance profile, and local key. Verify
   tagged and regional inventories contain no unexpected billable resources.

## Cost and remaining blocker

No charge was created by this investigation: no EC2 instance and no model
invocation occurred. Reusing the prior authorized shape gives a guarded
50-minute estimate of `$0.44976`, below a `$0.55` ceiling. A normal successful
run is expected to be near the prior 14.6-minute deployment cost (roughly
`$0.10-$0.12` gross) plus three small Haiku calls, but AWS billing is
authoritative.

The sole unresolved authorization blocker is independent SCP visibility. No
recovery deployment or IAM mutation should be authorized until that gate and a
fresh price/quota preflight pass.
