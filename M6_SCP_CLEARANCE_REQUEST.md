# M6 Organizations SCP clearance request

Status: **REQUIRED FROM THE AWS ORGANIZATION MANAGEMENT ACCOUNT**

The Lurker AI AWS account is a member account. Its current administrative role
cannot call `ListRoots`, `ListParents`, `ListPolicies`, or
`ListPoliciesForTarget`, so it cannot independently inspect effective service
control policies. No permission should be assumed from that lack of visibility.

An administrator authorized in the AWS Organizations management account should
perform the following read-only review and return a redacted policy export or a
written attestation containing the review time and result:

1. Identify the member account's parent with `organizations:ListParents`.
2. Walk every parent OU up to the organization root.
3. At the member account, every parent OU, and the root, call
   `organizations:ListPoliciesForTarget` for `SERVICE_CONTROL_POLICY`.
4. Call `organizations:DescribePolicy` for every attached SCP.
5. Evaluate both allow-list gaps and explicit Deny statements, including
   conditions on `aws:RequestedRegion`, `bedrock:InferenceProfileArn`, action,
   principal, and resource.
6. Confirm that `bedrock:InvokeModel` is effectively permitted for:

   - the originating call in `us-east-2` to the account-scoped inference
     profile `us.anthropic.claude-haiku-4-5-20251001-v1:0`;
   - the Claude Haiku 4.5 foundation model in `us-east-1`;
   - the Claude Haiku 4.5 foundation model in `us-east-2`; and
   - the Claude Haiku 4.5 foundation model in `us-west-2`.

If a Region-deny SCP exists, the administrator must verify an appropriate
inference-profile exception for the foundation-model evaluations. Such an
exception cannot bypass a restriction on the originating `us-east-2` profile
call. This request authorizes inspection and reporting only—not an SCP change.

Sufficient evidence is either:

- a redacted export of all applicable SCPs plus the account/OU/root attachment
  path, reviewed locally against the requirements above; or
- a dated attestation from an Organizations administrator explicitly stating
  that the four authorization evaluations above are allowed.

If neither form can be obtained, the only conclusive alternative is a
separately approved one-call runtime canary using the exact corrected temporary
role. That alternative would be a real Bedrock invocation and cannot be used
under the current pre-deployment-only authorization.
