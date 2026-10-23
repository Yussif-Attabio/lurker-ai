# Evidence data

This directory contains the small set of runtime artifacts needed to support
the public submission. It is evidence, not application source code.

- `demo/` contains the synthetic three-message replay fixture.
- `m6_acceptance/` preserves the redacted failed deployment, including the
  access-denied result and cleanup record.
- `m6_iam_recovery/` preserves the least-privilege IAM diagnosis and preflight.
- `m6_recovery_acceptance/` preserves the successful recovery deployment, all
  three replay transcripts, measurements, cost estimate, and cleanup record.
- `m7_submission/` contains the offline submission and recorder validations.
- `archive/` contains older M2-M5 evidence and superseded local M6 output. It
  is retained for auditability but is not part of the current evidence path.

Generated decision logs and new timestamped acceptance runs are ignored by
default. They should be reviewed and redacted before being deliberately added
to version control. Commit `56f319f` preserves the complete pre-cleanup layout.

No credential, private key, AWS account identifier, active endpoint, or
protected recovery-reserve dataset belongs in this directory.
