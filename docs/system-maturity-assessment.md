# PQ-AI System Maturity Assessment

Assessment date: 2026-06-13. This is an engineering assessment against the approved domain boundary, not a production certification.

## Executive Conclusion

PQ-AI is a functional, connected demonstration and a useful foundation for factory-data onboarding. Measurement provenance and reliability gating now protect AI/SPC ingress, but the system is not yet ready for production process recommendations because real instrument-file validation, trajectory/device data, governed material data, leakage-safe model validation, and approved recommendation constraints remain incomplete.

Estimated overall maturity: **59% - demonstrable prototype / factory-data onboarding preparation**.

## Scores And Evidence

| Area | Maturity | Current strength | Critical gap |
| --- | ---: | --- | --- |
| Scope/domain model | 80% | Approved quality/process scope is enforced from API and integration ingress through v2 feature snapshots and models | Explicit coating-system route, governed feature registry, and full legacy-data administration remain |
| Program/robot/application | 58% | Program versions, brushes, parameters, point contributions | No robot/atomizer identity, controller/bell-cup, path segment/TCP/orientation/trigger/checksum model |
| Materials | 40% | Batch, viscosity, solids, generic COA | Missing governed test methods, units, density/rheology/effect fields, limits, and lineage |
| Quality/instruments | 72% | Governed BYK/Fischer instruments, methods, references, calibrations, import profiles, repeats and automatic reliability gate | Real device-file validation, explicit probe master, uncertainty/MSA and measurement-plan execution remain |
| Data lineage/flow | 72% | Production run/point backbone and verified-measurement AI gate | Generic process/material JSON bypasses governance; contribution semantics are not target-family specific |
| AI modeling | 42% | Persisted ridge baseline, measurement-gated prediction/diagnosis/recommendation and drift | Training metrics only, no grouped/temporal holdout, applicability scope, OOD, governed artifacts, or causal evidence |
| Workflow/UX | 63% | Real CRUD, measurement-governance workspace and closed-loop operations | Missing instrument import wizard, measurement-plan execution, trajectory/contribution visualization, controlled-trial workspace |
| Integration/operations | 50% | Integration task framework, auth, audit, local MySQL | Real device/MES/QMS mappings, SSO, backup/DR, observability, and factory acceptance remain |

## High-Priority Findings

### Completed Baseline - Scope And Training Integrity

- Catalog, API, integrations, seed data, feature aggregation, UI, and tests now enforce the approved boundary.
- New approved snapshots use `point-features-v2-scope`; production-event context is retained for traceability but does not enter AI features.
- Existing `point-features-v1` models are retained for lineage and retired; local demo data is safely converted and retrained.
- Runtime model guards prevent legacy or out-of-scope models from activation, prediction, diagnosis, and recommendation.
- Residual work: add an administrator-facing legacy-data inventory and replace generic allowed JSON fields with a governed feature registry.

### Completed Baseline - Measurement Reliability

- BYK/Fischer instrument identity, serial/firmware, governed method, reference, calibration, direction, raw-file/import-profile version and repeat-reading provenance are now persisted.
- The reliability service automatically classifies each measurement as `VERIFIED`, `UNVERIFIED`, or `FAILED`; only valid `VERIFIED` measurements can enter SPC, feature labels, model training, diagnosis, recommendation verification, and closed-loop evaluation.
- Governance changes re-evaluate linked measurements, and the UI exposes real CRUD and reliability issues.
- Residual work: implement real BYK/Fischer file adapters and field-profile validation, an explicit probe master, measurement uncertainty/MSA, measurement-plan execution, and plant-approved calibration procedures.

### P0 - AI Acceptance

- Current ridge training uses all snapshots and reports training-set metrics. Point rows from the same run can be treated as independent samples.
- Production acceptance requires temporal holdout, grouped validation by run/body/batch, per-scope metrics, uncertainty/OOD handling, and formal model acceptance.

### P1 - Dürr Robot And Point Deposition

- Brush contribution is a useful start but robot path and applicator identity are not represented.
- Add robot, atomizer/controller, bell-cup, trajectory program/checksum, TCP/path segment, speed, orientation, trigger, and target-family contribution versions.

### P1 - Material Governance

- Viscosity and solid ratio are present, but method/units/test context and structured COA definitions are missing.
- Add governed material characteristic definitions, batch test results, approved limits, source lineage, and material-to-stage applicability.

## Completeness By System Layer

### Frontend And User Interaction

The current frontend supports real CRUD and a demonstrable closed loop, but the interaction model is still data-table oriented. Production use requires:

- A 3C2B context selector that always shows coating system, execution stage, factory/model/color, program/path version, material batch, and device.
- Real device-file import wizard, field-profile preview, measurement-plan execution, uncertainty/MSA review, and expired-calibration work queue.
- Dürr robot/path and target-family point-contribution visualization instead of only brush tables.
- A quality-engineer review queue that separates measurement/data-quality failures from process failures.
- A process-engineer controlled-trial workspace with hypothesis, coupled changes, constraints, rollback, approval, and sustained verification.
- Model acceptance views that show independent holdout metrics, scope, uncertainty/OOD, drift, and unsupported-use warnings.

### Backend Services

The API has generic CRUD, aggregation, modeling, audit, and integration foundations. Required domain services are:

- Administrator-facing scope-policy inventory and quarantine management.
- Extend the implemented instrument/calibration/reference/import-profile validation service with file parsing, MSA and plant procedures.
- Robot/atomizer/trajectory version and contribution service.
- Governed material-characteristic and COA mapping service.
- Dataset snapshot service with grouped/temporal splits and leakage checks.
- Controlled-trial, constraint-source, rollback, and sustained-verification workflow.

### Domain Model And MySQL

Keep the current production-run and measurement-point backbone. Add versioned entities for:

- `coating_system`, factory process-route/bake definition, and execution-stage mapping.
- `robot`, `atomizer`, `controller`, `bell_cup`, `trajectory_program`, `path_segment`, and executed path facts.
- Target-family `point_contribution_version` and contribution evidence.
- Extend the implemented `measurement_instrument`, `measurement_method`, `measurement_calibration_record`, `measurement_reference_standard`, `measurement_import_profile`, and repeated raw readings with explicit probes, MSA and device-file ingestion.
- `material_characteristic_definition`, batch test results, methods, units, limits, and source lineage.
- `dataset_snapshot`, split/group membership, model applicability scope, acceptance decision, OOD/drift policy, and model artifact.
- `controlled_trial`, constraint source/version, change proposal, rollback version, and sustained verification.

Generic JSON columns may remain as raw ingestion payloads, but approved feature generation must use governed values.

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
2. Completed baseline: add instrument/method, calibration/reference, repeat-reading, import-profile models, reliability gate, API and UI; next extend with explicit probes, MSA and real device-file adapters.
3. Add Dürr robot/atomizer/controller and trajectory/path-version models; version point contribution by target family.
4. Replace generic material COA training fields with governed material characteristic definitions/results.
5. Build leakage-safe dataset snapshots and grouped/temporal model evaluation with acceptance gates.
6. Add engineer-controlled trials, constraint sources, rollback, and sustained verification.
7. Complete real integrations, SSO, backup/DR, observability, and factory acceptance.
