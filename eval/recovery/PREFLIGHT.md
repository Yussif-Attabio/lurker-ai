# M5 recovery candidate preflight

Status: **PASS — READY FOR INDEPENDENT HUMAN LABELING**

This preflight covers candidate preparation and labeling infrastructure only. It does not approve model evaluation, create a new split, alter production settings, or change the original M5 NO-GO.

## Composition

- Candidates: 195
- Scenario families: 39 (five candidates each)
- Owner-only authoring coverage: 65 SILENT-oriented, 65 REACT-oriented, 65 REPLY-oriented
- Questions without final `?` in the dedicated punctuation family: 5
- Candidate SHA-256: `bae691b2ef2121986f41bc40c8976f2dd1ba28e989d33736876e7a97790bb685`

The authoring coverage is a design hypothesis, not ground truth. Only unanimous labels from three independent people can assign a class.

| Neutral category | Candidates |
|---|---:|
| already answered | 15 |
| ambiguous | 5 |
| casual | 75 |
| direct request | 30 |
| joke | 5 |
| mention | 5 |
| ongoing discussion | 25 |
| technical question | 35 |

## Blind evaluator files

Each evaluator receives all 195 scenarios in a different deterministic order. Labels and notes are blank, and the files contain no family IDs, authoring targets, split assignments, thresholds, or model predictions.

| Evaluator | Rows | Labels blank | SHA-256 |
|---|---:|---|---|
| A1 | 195 | Yes | `9830729618ff42183517cc8a029bfa64925f39d23c1b23eafce263aea31d1977` |
| A2 | 195 | Yes | `051999a9a3dd9609173fc00c03b6a1952d8e3fbcf5056df86f6ed563c5ea8f7f` |
| A3 | 195 | Yes | `5554e22ae1eff216a48008c2d07de7e79997d1f66177e7958749ae2ac02990ec` |

## Quality and isolation checks

| Check | Result |
|---|---|
| candidate count 195 | PASS |
| family count 39 | PASS |
| five per family | PASS |
| design balance 65 each | PASS |
| unique ids | PASS |
| exact duplicates zero | PASS |
| cross family near duplicate flags zero | PASS |
| public payload blind | PASS |
| three distinct orders | PASS |
| templates complete and blank | PASS |
| punctuation boundary present | PASS |
| generation reproducible | PASS |
| original nogo evidence unchanged | PASS |
| no human labels created | PASS |
| no new split created | PASS |

No original held-out example was parsed or reused. The audit only hashed the preserved NO-GO files against their existing checksum manifest; every checksum passed. No Decider, AWS, or Bedrock call occurred.

## Next authorized step

Give one evaluator slot or one blank CSV to each of three people. They must work independently. Do not share `design_manifest.json` or this preflight's authoring-balance section with evaluators. After all three genuine exports are collected, run the unanimous merge and review agreement, ambiguity, class quotas, and Fleiss' kappa before creating any split.
