# Milestone M7 local submission-package acceptance

Status: **PUBLIC REPOSITORY PUBLISHED - ARTICLE, VIDEO, AND FINAL GO PENDING**

Date: 2026-10-18

## Scope

M7 packages the existing project for the hackathon. It does not change the
frozen model, thresholds, architecture, held-out result, or M6 evidence. This
phase launched no AWS resource and made no Decider or Bedrock call.

## Required local deliverables

- [x] Submission-facing README additions: setup, text architecture, results,
  limitations, license, and evidence links.
- [x] `ARTICLE_NOTES.md` with article facts and real numbers.
- [x] `DEMO_SCRIPT.md` with a sub-three-minute real-output shot list.
- [x] Reusable package guide, standalone gate wrapper, minimal example, and
  official Strands intervention wiring.
- [x] Offline regression and documentation validation.
- [x] Guarded Playwright recorder with separate MOCK preview and one-call
  real-service modes; generated video artifacts remain local and ignored.
- [x] Public MIT-licensed source repository:
  `https://github.com/Yussif-Attabio/lurker-ai`.
- [ ] Human review and final M7 GO/NO-GO.

## Local verification

- Targeted M7, frozen-policy, M6 reliability, and IAM recovery suite: **28
  passed** in 2.72 seconds.
- Final pre-publication full offline regression suite: **126 passed** in 3.92
  seconds.
- Post-recorder full offline regression suite: **132 passed** in 4.38 seconds.
- Automated preview: **PASS**, 62.04 seconds, 1440×900, three expected actions,
  zero errors, zero AWS/Bedrock calls, and visibly non-submission-eligible MOCK
  output.
- Python compilation for the new reusable modules: PASS.
- Frontend JavaScript syntax: PASS.
- Required local files and MIT license: PASS.
- Minimal example: 11 nonblank lines, below the 25-line build-spec limit.
- Credential, account-identifier, and failed-endpoint scan: PASS.
- AWS resources launched: 0.
- Real Decider calls: 0.
- Bedrock calls: 0.

Reproducible evidence:
`data/m7_submission/20261018T213056Z/validation.json`.
Recorder validation:
`data/m7_submission/20261018T215531Z/demo_recorder_validation.json`.

## Evidence boundaries

- Original M5 held-out performance remains NO-GO.
- Original failed M6 deployment remains a preserved NO-GO.
- Successful M6 recovery transcripts and measurements remain unchanged.
- Frozen `decision_pattern/lurker_gate.py`, `config/default.yaml`, and published
  M5 evidence remain byte-for-byte unchanged.
- No protected reserve scenario is used in submission material.

## Mandatory human publishing actions

The official rules require all three parts; missing any part is a pass/fail
qualification failure:

1. Publish the article on AWS Builder Center.
2. ~~Publish this repository publicly under the MIT License.~~ Completed at
   `https://github.com/Yussif-Attabio/lurker-ai`.
3. Record and publicly upload a demo video under three minutes.
4. Add `#strands-decider-2b` and `#policy` to the entry.
5. Confirm entrant eligibility, ownership, and the final submitter.
6. Submit before October 23, 2026 at 11:59 p.m. PT.

The owner separately authorized this public GitHub publication. Article and
video publication, final hackathon submission, AWS deployment, and Bedrock
invocation still require their applicable approvals.

## Acceptance gate

M7 cannot receive final GO until local checks pass and the owner verifies the
article, public repository, public video, tags, eligibility, and submitted
entry. Production readiness remains explicitly unapproved.
