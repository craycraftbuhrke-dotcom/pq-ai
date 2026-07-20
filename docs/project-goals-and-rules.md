# PQ-AI Development Goals And Project Rules

## Product Goal

Build a production-oriented, human-controlled closed loop that connects actual midcoat/basecoat/clearcoat spray execution and material batches to point-level film thickness, color, and orange-peel results, then supports prediction, diagnosis, constrained recommendation, approval, execution, and verification.

## Approved Boundary

- Three coating systems: midcoat, basecoat, clearcoat.
- Five execution stages: midcoat external spray, basecoat pass 1/2, clearcoat pass 1/2.
- Quality inspection: BYK color, BYK orange peel, Fischer coating thickness.
- Application: Dürr electrostatic rotary-bell robots, process parameters, robot paths, and point contribution.
- Material: only governed batch characteristics relevant to thickness, color, or orange peel.

Explicitly excluded: pretreatment, e-coat, sealing, booth temperature/humidity, oven temperature, paint-mix-room data, and gloss.

## Product Principles

1. A usable result must be traceable to factory, model, color, body/run, coating system, stage, program/path version, robot/atomizer, material batch, part, point, instrument, and standard.
2. A material value used by AI must also be traceable to a stable characteristic definition, canonical unit, test method/version, time-valid approved specification, stage/target-family applicability, batch test result, source, and reliability decision.
3. The database stores facts and lineage; generic JSON is an ingestion bridge, not the final governed model.
4. AI starts with leakage-safe baselines and earns complexity through measured improvement.
5. Diagnosis distinguishes association from verified causality.
6. Recommendations are constrained by approved source versions, explainable, tied to an approved controlled-trial plan, reversible, executed as a trial, verified with quality data, and recorded with rollback evidence when ineffective.
7. No model is production-ready until validated with real independent factory runs and accepted by process and quality engineers.
8. A configured robot program is not proof of execution. Approved AI input requires the production-stage device configuration, executed trajectory checksum, and target-family point contribution lineage.
9. Legacy material viscosity/solids and free-form COA fields are compatibility facts only. A required material result that is absent, unverified, failed, or measured after production start blocks approved feature generation.
10. A model can be activated only after an immutable dataset snapshot passes grouped temporal leakage checks, the model is evaluated on its independent validation split, and a human acceptance decision is recorded.
11. A model's factory/model/color applicability and statistical OOD blocking policy are governed acceptance facts. Unsupported, incomplete, or distribution-outlier inputs must never reach prediction, diagnosis, or recommendation.
12. Statistical OOD policy does not replace approved device, material, TDS, program, or process safety constraints.
13. Every production model must satisfy a versioned, source-backed, active factory acceptance policy for every applicable factory and target metric. Demo thresholds never qualify as factory approval.
14. MySQL schema changes are controlled production operations. Code, scripts, Docker entrypoints, and CI must not create, migrate, alter, or drop MySQL schema objects automatically.
15. Every database-structure change requires an approval ticket, forward SQL, rollback SQL or rollback limitation, risk assessment, database-owner approval, manual execution, and execution record.
16. Physical foreign keys are forbidden. All references must be represented as logical `*_id` fields and enforced in application logic.
17. Runtime application SQL must not execute physical `DELETE`, `CREATE`, `DROP`, `ALTER`, `TRUNCATE`, `REPLACE`, or application-authored `SET` statements against MySQL.
18. Business removal must be implemented as disable, archive, status transition, or version replacement; official HTTP `DELETE` requests remain rejected.
19. Human users authenticate with personal username/password sessions stored as HttpOnly cookies; external systems use API Keys. Never expose session tokens or API Keys to browser JavaScript.
20. Every domain CRUD surface must support governed Excel/CSV template download, bulk export, and bulk import where the underlying resource is editable. Templates are the contract for field names, data types, required fields, and business keys.
21. Bulk import must call existing application services/routes, enforce the same logical reference checks as manual CRUD, and use create/upsert semantics only. Import files must never trigger schema creation, schema migration, unsafe SQL, or physical deletion.
22. Frontend information architecture is organized around user tasks and decisions, not database tables. Each page must state its purpose, primary action, required prerequisites, result, and next step in plain business language.
23. Complexity belongs in governed backend services. The frontend may guide and progressively disclose details, but must not weaken domain validation, approval, lineage, reliability, or safety constraints to make a workflow appear simpler.
24. User-visible labels must use workshop language understood by process engineers, quality engineers, suppliers, and new operators. Internal IDs, JSON, hashes, enum codes, and database field names belong in traceability details, not primary forms.
25. Empty, loading, blocked, error, and success states are part of the business workflow. Every state must explain what happened, what is affected, and what the user should do next.
26. Production point-feature snapshots and separately uploaded training-wide samples are equal model-training sources. Neither source receives hidden priority or weighting; both must pass the same feature-scope, grouped temporal split, leakage, validation, lineage, and acceptance rules.
27. Human training uploads must use Chinese-column Excel/CSV templates. Users provide sample number, independent group, occurrence time, target value, and governed feature values; internal feature keys and JSON conversion remain backend responsibilities.
28. Every robot-parameter edit creates a new complete draft program version, even when only one brush parameter changes. The service must copy every brush, parameter, applicability relation, and point contribution before applying edits; it must never mutate the approved/current version in place.
29. Remote upper-computer operation is deny-by-default and isolated. A cloud draft, submitted request, or approved request alone must never change the remote station. Remote application requires approved connection, separate release approval, successful staging, local upper-computer confirmation, explicit commit, and readback verification.
30. Remote parameter transport must use mutual TLS over TCP/IP, bounded length-prefixed messages, target-agent identity, replay protection, full-package hashes, immutable release events, and runtime-injected certificate/private-key locations. Plain TCP and database-stored secrets are forbidden.
31. The cloud, virtual line, and upper computer are independent versioned sources. Reconciliation is read-only; resolving a difference must create/capture an approved version or follow the remote-release workflow, never directly overwrite a source from the comparison table.
32. Direct undocumented robot writes are forbidden. Production adapters must be approved by the factory and Dürr/upper-computer owner and pass FAT/SAT. Simulator and file-drop modes may support development and governed handoff but must not claim that a robot changed without matching readback.

## Development Gate

Every new feature must pass:

- Scope check: no excluded fields or processes.
- Traceability check: source, version, applicability, and audit are present.
- Domain check: coating system, execution stage, measurement semantics, and units are correct.
- Data check: validation, missingness, repetition, and lineage are handled.
- AI check: grouped/temporal evaluation, uncertainty, applicability, and drift are handled.
- Workflow check: engineer decision, approval, rollback, and verification are represented.
- Robot execution check: approved configuration/trajectory, actual checksum, path-segment facts, target-family contribution version, and mismatch blocking are represented.
- Material governance check: definition, canonical unit, method, specification source/effective period, stage/target-family applicability, production-time gate, reliability, and lineage are represented.
- Database governance check: no automatic MySQL DDL; schema changes have an approved manual SQL ticket and are documented in release evidence.
- MySQL standards check: no physical foreign keys, no runtime physical deletes, no unsupported data types, compliant table/field/index naming, and DBA-reviewed DDL only.
- Authentication check: user sessions, API Keys, RBAC permission checks, and write-operation audit evidence are present for protected workflows.
- Bulk data check: editable domain resources provide templates, export, import validation, row-level errors, idempotent upsert behavior, and post-import UI refresh.
- Remote execution check: complete-version derivation, connection approval, segregation of duties, staging isolation, local confirmation, mutual TLS, bounded protocol, readback hash, failure evidence, and rollback version are present.

## Execution Discipline

1. Development is plan-driven. Before implementing or changing a non-trivial feature, update `docs/development-plan.md` with scope, acceptance criteria, execution order, and completion status.
2. Work strictly in small sequential steps. Do not start a later step until the current step is implemented, reviewed, tested, verified, and marked complete in the development plan.
3. Foundation-first order is mandatory: master data, process-stage parameter capture, equipment/device parameter capture, quality data capture, point-level aggregation and business workflow usability come before AI model and closed-loop optimization work.
4. After every completed development step, perform a self-review against product rules, database governance rules, workflow correctness, and UI usability expectations before moving on.
5. After every completed development step, run focused tests and verification suitable for the change scope. At minimum this includes relevant automated tests; when UI or workflow behavior changes, add manual/browser verification evidence.
6. A step is not considered complete until implementation, review, testing, verification evidence, and plan status update are all finished.
7. Any new page, form, import flow, or CRUD surface must be checked for dead controls, misleading placeholders, layout overlap, overflow, stacking conflicts, and missing empty/error/success states as part of the same step, not as a later cleanup.
8. All changes must continue to respect project database rules: no automatic MySQL DDL, no physical foreign keys, no runtime physical deletes, no unsafe SQL, and no schema mutation outside approved manual SQL workflow.
9. Code review candidates are tracked in `docs/coderabbit-remediation-plan.md`. A candidate may be fixed, invalidated, deduplicated, or accepted with documented risk, but must never disappear without a recorded disposition.
