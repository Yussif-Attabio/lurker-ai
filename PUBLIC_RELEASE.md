# Public release boundary

This repository publishes the Lurker AI implementation, tests, aggregate
evaluation results, redacted deployment evidence, and reproducible demo
materials. The public history intentionally excludes a small set of local
artifacts:

- the original locked M5 held-out rows and per-case predictions;
- the 105-scenario recovery reserve and evaluator source sheets;
- private evaluator ordering and split metadata;
- the unredacted AWS `AccessDeniedException` record from the first M6 run; and
- a historical public IP for a terminated M3 host.

These exclusions protect evaluation integrity and account privacy. They do not
change the published aggregate findings: M5 remains technically complete with
a model-performance NO-GO, and the first M6 deployment failure remains
documented alongside the successful recovery acceptance.

No credentials, private keys, AWS account identifiers, or active infrastructure
are included. Local `.env` variants, virtual environments, caches, and runtime
logs are ignored by default.
