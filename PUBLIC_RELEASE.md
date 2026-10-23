# Public release boundary

This repository publishes the Lurker AI implementation, tests, frozen and
aggregate evaluation results, curated redacted deployment evidence, and
reproducible demo materials. The main branch intentionally excludes a small
set of local artifacts:

- the original locked M5 held-out rows and per-case predictions;
- the 105-scenario recovery reserve and evaluator source sheets;
- private evaluator ordering and split metadata;
- the unredacted AWS `AccessDeniedException` record from the first M6 run; and
- a historical public IP for a terminated M3 host.

Superseded milestone plans and intermediate outputs are grouped under
`docs/archive/`, `data/archive/`, and `results/archive/` so they do not obscure
the current public claims. Commit `56f319f` is the complete pre-cleanup layout.

These exclusions protect evaluation integrity, account privacy, and the
readability of the submission. They do not change the published findings: M5
remains technically complete with a model-performance NO-GO, and the first M6
deployment failure remains documented alongside the successful recovery.

No credentials, private keys, AWS account identifiers, or active infrastructure
are included. Local `.env` variants, virtual environments, caches, and runtime
logs are ignored by default.
