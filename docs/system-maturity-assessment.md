# PQ-AI System Maturity Assessment

Assessment date: 2026-06-16. This is an engineering assessment against the approved domain boundary, not a production certification.

## Executive Conclusion

PQ-AI is a functional, connected demonstration and a useful foundation for factory-data onboarding. Application-layer referential integrity, measurement reliability, explicit probes/MSA, 3C3B route governance, engineering issue tasks, Dürr trajectory/device lineage, governed material-result gates, supplier material submissions, contribution validation, model explanations, leakage-safe model acceptance, multi-axis validation evidence, model artifact registration, controlled-trial gating, approved constraint-source versions, rollback execution records, complete user authentication, CSV import wizard, model comparison, and program version diff tooling now protect the AI lifecycle, but the system is not yet ready for production process recommendations because real device/material file validation, validated deposition contribution, factory-specific configuration, automatic program rollback publishing, and sustained verification remain incomplete.

Estimated overall maturity: **90% - governed engineering prototype / factory-data onboarding preparation**.

## Scores And Evidence

| Area | Maturity | Current strength | Critical gap |
| --- | ---: | --- | --- |
| Scope/domain model | 90% | Approved quality/process scope is enforced from API and integration ingress through 3C3B route versions, engineering tasks, v4 target-family feature snapshots and models | Broader governed feature registry and full legacy-data administration remain |
| Program/robot/application | 82% | Governed robot/controller/atomizer identity, program-device configurations, trajectory checksums, path segments, actual executions, trajectory geometry records, target-family contribution versions/validations, program version diff, and rollback execution records | Real DXQ/PLC file adapters, real coordinates/orientation/trigger facts, deposition validation, trajectory/contribution visualization, and automatic program rollback publishing remain |
| Materials | 76% | Governed characteristic definitions, method versions, units, specifications/effective periods, stage/target applicability, batch results, supplier submissions/issues, reliability, integration, UI, and feature lineage | Replace demo methods/units/specifications with approved factory/TDS/COA facts; add real pigment/effect/levelling fields and file adapters |
| Quality/instruments | 80% | Governed BYK/Fischer instruments, explicit probes, methods, references, calibrations, import profiles, repeats, MSA/GRR records, CSV batch import wizard and automatic reliability gate | Real device-file validation, uncertainty propagation and measurement-plan execution remain |
| Data lineage/flow | 87% | Production run/point backbone, verified measurement/material gates, target-family contribution, trajectory execution, material result/specification lineage, and application-layer FK integrity on write endpoints | Real external-file lineage and validated contribution evidence remain |
| AI modeling | 84% | Immutable datasets, independent validation, multi-axis grouped validation folds, registered model artifact hashes, versioned factory acceptance policies, exact applicability, statistical OOD blocking, model comparison, persisted inference evidence, prediction/diagnosis/recommendation and drift | Real factory policy configuration, richer uncertainty, stronger models, governed external artifact storage, and causal evidence |
| Workflow/UX | 90% | Real CRUD, engineering issue center, measurement/material/Dürr governance, supplier collaboration records, login/register/profile/security-admin, CSV import wizard, factory acceptance-policy maintenance, model acceptance/applicability/OOD governance, pre-inference checks, controlled-trial plans, approved constraint-source evidence, recommendation approval gating, execution, verification, and rollback record | Missing instrument/material import wizard, measurement-plan execution, trajectory/contribution visualization, automatic program-version rollback publishing, and sustained verification dashboard |
| Integration/operations | 65% | Integration task framework plus robot actual/trajectory and governed material-result ingestion, auth, audit, database error classification, local MySQL, and manual database-change control | Real device/MES/QMS/material mappings, SSO, backup/DR, observability, factory acceptance, and executed DBA ticket evidence remain |

## High-Priority Findings

### Completed Baseline - Scope And Training Integrity

- Catalog, API, integrations, seed data, feature aggregation, UI, and tests now enforce the approved boundary.
- New approved snapshots use `point-features-v4-material-governed`; production-event context is retained for traceability but does not enter AI features.
- Existing `point-features-v1` models are retained for lineage and retired; local demo data is safely converted and retrained.
- Runtime model guards prevent legacy or out-of-scope models from activation, prediction, diagnosis, and recommendation.
- Residual work: add an administrator-facing legacy-data inventory and replace generic allowed JSON fields with a governed feature registry.

### Completed Baseline - Measurement Reliability

- BYK/Fischer instrument identity, serial/firmware, explicit probe master, governed method, reference, calibration, direction, raw-file/import-profile version, MSA/GRR record and repeat-reading provenance are now persisted.
- The reliability service automatically classifies each measurement as `VERIFIED`, `UNVERIFIED`, or `FAILED`; only valid `VERIFIED` measurements can enter SPC, feature labels, model training, diagnosis, recommendation verification, and closed-loop evaluation.
- Governance changes re-evaluate linked measurements, and the UI exposes real CRUD and reliability issues.
- Residual work: implement real BYK/Fischer file adapters and field-profile validation, uncertainty propagation, measurement-plan execution, and plant-approved calibration procedures.

### Completed Baseline - AI Acceptance

- Immutable dataset snapshots freeze feature values, target values, source quality-measurement IDs, body/run group membership, temporal split, feature list, cutoff, and leakage-check result.
- All point rows for the same body/run remain in one split; the newest independent groups form the validation holdout. Models fit only `TRAIN`, report separate training and validation metrics, and use validation RMSE as the online effect-drift baseline.
- New models remain `DRAFT`; activation is blocked until a human records an accepted decision after reviewing independent-validation evidence.
- Training derives exact factory/model/color applicability contexts from the governed dataset and creates a statistical OOD blocking policy. Both remain pending until human acceptance; activation requires approved scope and policy.
- Factory acceptance policies are versioned and source-backed. Acceptance and activation require every applicable factory to have an active target-metric policy and require the model to satisfy validation RMSE, validation R², and independent-group thresholds. Demo policies can authorize only demo models.
- Prediction and recommendation are blocked for unsupported contexts, missing model features, or excessive standardized feature shifts. Accepted predictions persist applicability and OOD evidence for diagnosis and audit.
- Residual work: configure real factory-approved policies, add richer uncertainty, governed external artifact storage, stronger model families, and real factory-run acceptance.

### Completed Baseline - Dürr Robot And Point Deposition

- Robot, application controller, rotary atomizer/bell-cup identity, program-device configurations, trajectory program/checksum, path segments, configured speed/TCP/trigger, production execution, and actual path-segment facts are represented.
- Point contribution is versioned and approved separately for thickness, color/effect, and orange peel. Contributions can reference a brush or path segment, and checksum mismatch blocks approved feature generation.
- Residual work: validate real DXQ/PLC export files, populate real coordinates/orientation/trigger and actual values, validate contribution with geometry/simulation/DOE/deposition evidence, and add visual comparison/review.

### Completed Baseline - Application-Layer Referential Integrity

- A dedicated `referential_integrity` module provides `check_fk()` and `check_delete_safe()` utilities for validating referential integrity at the application layer without database-enforced physical foreign keys.
- All 12 route handler files (140 write endpoints) now include FK existence checks on POST/PATCH operations and downstream reference checks on DELETE operations.
- Database errors are now classified into 6 distinct types (FK conflict, unique conflict, not-null, deadlock, timeout, connection failure) with appropriate HTTP status codes and Chinese-language error messages.
- Residual work: add `ForeignKey()` annotations to domain.py for ORM relationship mapping; create integration tests for FK violation scenarios; add batch-delete cascade patterns.

### Completed Baseline - Controlled Trial Workspace

- A dedicated `/controlled-trials` page provides full lifecycle management: trial list with status filtering, detail panel showing hypothesis/risk/rollback/observation plans, state timeline, and action buttons (approve/start/rollback).
- The workspace is integrated into the main navigation and uses consistent visual patterns with the rest of the application.
- Residual work: connect trial creation to recommendation workflow in AI workbench; add rollback execution recording; implement sustained observation dashboards.

### Completed Baseline - CSV Import Wizard & Model Comparison

- The `/import-wizard` page provides CSV file upload with preview, field mapping guide, and batch import of quality measurement data via `POST /quality/measurements/import-csv`.
- The AI workbench now includes a `comparison` tab with a sortable model metrics table (training/validation R², RMSE) with color-coded cells and summary statistics.
- The program workspace includes a `version-diff` tab that compares two program versions' brush parameters, showing changed/added/removed values with percentage deltas.
- Residual work: expand CSV import to support material batch results and production events; add drift trend line charts; implement batch-comparison export.

- Characteristic definitions, method versions, canonical units, material specifications/effective periods, material-type/stage/target-family applicability, batch results, source lineage, and derived reliability are represented.
- Only `VERIFIED` results measured no later than production start can enter approved features; missing required results block snapshot generation. Legacy viscosity/solids/free-form COA fields remain compatible but no longer bypass governance.
- Residual work: replace demo placeholder methods, units, and specifications with approved factory/TDS/COA facts; add real pigment/effect/levelling characteristic mappings and material-system file adapters.

## Completeness By System Layer

### Frontend And User Interaction

The current frontend supports real CRUD and a demonstrable closed loop, but the interaction model is still data-table oriented. Production use requires:

- A 3C2B context selector that always shows coating system, execution stage, factory/model/color, program/path version, material batch, and device.
- Real device-file import wizard, field-profile preview, measurement-plan execution, uncertainty/MSA review, and expired-calibration work queue.
- Extend the implemented Dürr governance workspace with path geometry, contribution heatmap, version comparison, execution-deviation review, and rollback views.
- A quality-engineer review queue that separates measurement/data-quality failures from process failures.
- Extend the implemented process-engineer controlled-trial workflow with coupled-change groups, automatic program-version rollback publishing, and sustained-verification dashboards.
- Extend the implemented model-acceptance-policy/applicability/OOD/validation-artifact view with reviewer roles, scope-expansion approval detail, and richer uncertainty.

### Backend Services

The API has generic CRUD, aggregation, modeling, audit, and integration foundations. Required domain services are:

- Administrator-facing scope-policy inventory and quarantine management.
- Extend the implemented instrument/probe/calibration/reference/import-profile/MSA validation service with file parsing, uncertainty propagation and plant procedures.
- Extend the implemented robot/atomizer/trajectory/contribution service with real file parsing, geometry validation, and deviation workflows.
- Extend the implemented material-characteristic service with real TDS/COA parsing, field-profile validation, approved method/unit masters, and supplier/factory mappings.
- Extend the implemented dataset snapshot, validation fold, artifact, factory acceptance policy, applicability, and OOD services with richer uncertainty, external artifact storage, and factory approval roles.
- Extend the implemented controlled-trial workflow with PLC/program publishing for rollback execution and sustained-verification workflow.

### Domain Model And MySQL

Keep the current production-run and measurement-point backbone. Add versioned entities for:

- `coating_system`, factory process-route/bake definition, and execution-stage mapping.
- Extend implemented `durr_robot`, `durr_rotary_atomizer`, `durr_application_controller`, `trajectory_program`, `trajectory_path_segment`, `production_device_execution`, and target-family contribution entities with real file/import metadata, geometry, validation evidence, and factory applicability.
- Extend the implemented `measurement_instrument`, `measurement_probe`, `measurement_method`, `measurement_calibration_record`, `measurement_reference_standard`, `measurement_import_profile`, `measurement_msa_study`, and repeated raw readings with real device-file ingestion and uncertainty propagation.
- Extend implemented material characteristic definitions, batch results, methods, units, specifications, applicability, reliability, and source lineage with real import profiles and approved factory facts.
- Extend implemented `dataset_snapshot`, split/group membership, target-measurement lineage, validation fold, model artifact, acceptance decision, model applicability scope, OOD policy, and persisted inference evidence with richer uncertainty.
- Extend implemented `controlled_trial`, `parameter_constraint_source`, and `program_rollback_execution` with change proposal grouping, automatic rollback publishing, and sustained verification.

Generic JSON columns may remain as raw ingestion payloads, but approved feature generation must use governed values.

Database operations rule: MySQL schema changes are not executed by the application, Docker, local scripts, CI, Alembic, or SQLAlchemy metadata calls. Physical foreign keys are not used; logical references are enforced in the application. Runtime physical deletes and application-authored structural SQL are forbidden. Every structure change requires approved manual SQL, rollback evidence, and DBA execution record. Test-only schema creation is restricted to transient SQLite through the guarded test helper.

### Business And Data Flow

The mature workflow is:

```text
master data + process route + device/path/material/instrument governance
  -> production event and actual execution
  -> calibrated point measurements and validation
  -> standard/SPC/data-quality review
  -> leakage-safe dataset and approved model
  -> prediction / association diagnosis / constrained proposal
  -> engineer approval and controlled trial
  -> execution facts and post-change measurements
  -> sustained verification, rollback or promotion
```

## Required Remediation Sequence

1. Completed baseline: enforce the approved scope at catalog, validation, seed, import, feature-snapshot, UI, and test levels; quarantine legacy out-of-scope snapshots/models.
2. Completed baseline: add instrument/probe/method, calibration/reference, repeat-reading, import-profile, MSA models, reliability gate, API and UI; next extend with real device-file adapters and uncertainty propagation.
3. Completed baseline: add Dürr robot/atomizer/controller, device configuration, trajectory/path/execution models, checksum gate, target-family point contribution, API, integration event, and UI; next validate real factory files and contribution evidence.
4. Completed baseline: replace generic material COA training fields with governed material definitions, methods, specifications, applicability, batch results, reliability gate, integration, UI, and v4 feature lineage; next ingest approved factory/TDS/COA facts.
5. Completed baseline: build immutable leakage-safe dataset snapshots, grouped temporal evaluation, multi-axis validation folds, registered model artifacts, independent metrics, versioned factory acceptance policies, human acceptance, exact applicability scope, OOD blocking and activation gates; next add richer uncertainty, external artifact storage, and stronger model families.
6. Completed baseline: add engineer-controlled trial plans, approval gate, execution linkage, verification outcome status, approved constraint-source versions, and rollback execution records; next add rollback publishing and sustained verification dashboards.
7. Complete real integrations, SSO, backup/DR, observability, and factory acceptance.
