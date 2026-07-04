---
name: automotive-paint-process-quality
description: Apply the approved PQ-AI automotive paint domain boundary and engineering rules when designing, implementing, reviewing, testing, or documenting 3C3B/3C2B spray execution, Dürr rotary-bell/robot, paint-material, BYK color/orange-peel, Fischer thickness, point aggregation, quality diagnosis, prediction, recommendation, and engineer closed-loop task features.
---

# PQ-AI Automotive Paint Process Quality

Use this skill for every change that touches process stages, parameters, materials, measurement data, feature engineering, AI models, recommendations, or engineer workflows.

## Mandatory Scope

- Include only midcoat, basecoat, clearcoat, paint-surface inspection, Dürr electrostatic rotary-bell application, relevant material characteristics, and BYK/Fischer measurements.
- Model three coating systems: midcoat, basecoat, and clearcoat.
- Model five approved spray execution stages: midcoat external spray, basecoat pass 1/2, and clearcoat pass 1/2. Passes are not separate coating systems.
- Model factory-level 3C3B process-route versions and route steps for traceability, but keep oven temperature, booth humidity/temperature, pretreatment, e-coat, sealing, and paint-mix-room data outside the approved AI feature scope unless the project boundary is formally changed.
- Target only film thickness, color difference/effect, and orange peel.
- Exclude pretreatment, e-coat, sealing, booth temperature/humidity, oven temperature, paint-mix-room data, and gloss from the approved product/model scope.
- Never invent Dürr limits, TDS limits, instrument semantics, or quality standards. Store factory-approved values with source/version/effective period.

## Required Design Checks

1. Identify the coating system, execution stage, production run/body, program version, robot/atomizer, material batch, part, and measurement point.
2. Distinguish configured setpoints, actual executed values, material test results, measurement results, and derived features.
3. Preserve measurement traceability: instrument model/serial, firmware/export schema, method/probe, calibration/reference status, operator, timestamp, repetitions, and raw/corrected values.
4. Aggregate point features from approved brush/path contribution versions. Do not treat simple averages as physical truth.
5. Require the production-stage device configuration and executed trajectory checksum to match an approved trajectory before using the stage in an approved feature snapshot.
6. Admit a material value to AI only through an active characteristic definition, matching active test method, time-valid approved specification, active material-type/stage/target-family applicability, and a `VERIFIED` batch result tested no later than production start.
7. Keep legacy viscosity, solids, and free-form COA fields only for compatibility and traceability; never promote them directly into approved feature snapshots.
8. Train separate model families for thickness, color, and orange peel. Split data by time and production event/body/batch to prevent leakage.
9. Freeze every acceptance dataset with feature values, target values, quality-measurement IDs, group/split membership, temporal cutoff, and leakage checks. Fit only on `TRAIN`; evaluate only on independent `VALIDATION`.
10. Never activate a model from training metrics. Require recorded independent-validation metrics and a human acceptance decision before activation.
11. Derive initial factory/model/color applicability from the governed dataset, keep it pending until human acceptance, and require an approved statistical OOD blocking policy before activation.
12. Generate multi-axis validation evidence for candidate models: primary temporal holdout, production-group leave-one-out, and factory/model/color axes where diversity exists. If an axis has only one value, record insufficiency instead of claiming cross-domain validation.
13. Register a model artifact hash covering model payload, evaluation metrics, dataset reference, and training sample count. Acceptance and activation must reject missing or mismatched artifacts.
14. Require an active factory-approved acceptance-policy version for every applicable factory and target metric. Allow explicitly marked demo policies only for demo models.
15. Block prediction, diagnosis, and recommendation for unsupported contexts, incomplete model inputs, or distribution-outlier inputs; persist the scope/OOD evidence with each accepted prediction.
16. Treat diagnosis as association unless supported by controlled DOE or other causal evidence.
17. Constrain recommendations by approved source-versioned device, TDS, program, step-size, and interaction rules; reject recommendations that cannot persist the constraint source/version used for every action.
18. Require an approved controlled-trial plan before recommendation approval.
19. Controlled-trial plans must record hypothesis, evidence type, expected outcome, risk, rollback plan, sustained observation plan, execution linkage, and post-change measurement outcome.
20. Ineffective trials must be reversible: record rollback execution, target program/version when known, execution note, and action snapshot before treating the loop as closed.
21. Engineer issue tasks must preserve abnormality discovery, measurement reliability review, material batch review, Dürr execution review, hypothesis, evidence, recommendation/trial linkage, conclusion, and causality level. Mark conclusions as association unless controlled DOE/trial evidence exists.
22. Real-file ingestion must use approved import profiles, preview, validation, error reports, replay records, and checksums. Imports must never trigger schema creation or structural mutation.
23. Do not use Alembic or automatic MySQL schema mutation. Database-structure changes require an approved manual SQL ticket and human execution record.
24. SQLAlchemy `Base.metadata.create_all/drop_all` is forbidden outside the guarded SQLite-only test helper.
25. Apply the company MySQL standards: lowercase underscore names, <=32 character project names, comments on tables/fields, `uk_`/`idx_` naming, <=50 fields per table, <=5 indexes per table, InnoDB/utf8mb4, no unsupported field types, and no large binary/file storage.
26. Never add physical foreign keys. Use `logical_fk` metadata and application-layer reference checks.
27. Runtime MySQL operations must not perform physical `DELETE`, `CREATE`, `DROP`, `ALTER`, `TRUNCATE`, `REPLACE`, or application-authored `SET`. Use disable/archive/status/version workflows.
28. Web users authenticate through personal username/password sessions stored as HttpOnly cookies. API Keys are reserved for system integration and server-side automation and must never be exposed to browser JavaScript.
29. Reject or quarantine out-of-scope features before snapshot creation and training.

## Reference Loading

- Read [process-and-spray.md](references/process-and-spray.md) for 3C2B, rotary-bell parameters, robot paths, and point contribution.
- Read [measurement-and-materials.md](references/measurement-and-materials.md) for BYK/Fischer data and material characteristics.
- Read [engineering-workflow-and-ai.md](references/engineering-workflow-and-ai.md) for engineer workflows, AI datasets, evaluation, diagnosis, and closed-loop recommendation.
- Read [sources.md](references/sources.md) when validating a domain claim or adding a new source.

## Definition Of Done

- Scope and exclusions are explicit in UI, API, schema, seed data, tests, and documentation.
- Every model result is traceable to feature set, training data, model version, applicability scope, and measurement provenance.
- Every recommendation shows evidence, source-versioned constraints, uncertainty, approval, execution values, verification results, and rollback record when ineffective.
- Tests cover scope filtering, traceability, grouped/temporal evaluation, and closed-loop audit behavior.
- Database changes include an approved manual SQL workflow reference; code, scripts, Docker, and CI contain no automatic MySQL DDL or migration command, no physical foreign keys, and no runtime physical deletes.
- Robot/trajectory changes cover device identity, program/path version, checksum matching, target-family contribution, actual execution, and rollback traceability.
- Material changes cover characteristic semantics, canonical unit, method version, specification source/effective period, stage/target-family applicability, batch result reliability, production-time gate, and feature lineage.
