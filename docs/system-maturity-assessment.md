# PQ-AI System Maturity Assessment

Assessment date: 2026-06-11. This is an engineering assessment against the approved domain boundary, not a production certification.

## Executive Conclusion

PQ-AI is a functional, connected demonstration and a useful foundation for factory-data onboarding. It is not yet ready for production process recommendations because measurement provenance, trajectory/device data, governed material data, leakage-safe model validation, and approved recommendation constraints are incomplete.

Estimated overall maturity: **52% - demonstrable prototype / factory-data onboarding preparation**.

## Scores And Evidence

| Area | Maturity | Current strength | Critical gap |
| --- | ---: | --- | --- |
| Scope/domain model | 55% | Five execution stages and core entities exist | Gloss, e-coat thickness, booth temperature/humidity, and instrument temperatures conflict with the approved scope |
| Program/robot/application | 58% | Program versions, brushes, parameters, point contributions | No robot/atomizer identity, controller/bell-cup, path segment/TCP/orientation/trigger/checksum model |
| Materials | 40% | Batch, viscosity, solids, generic COA | Missing governed test methods, units, density/rheology/effect fields, limits, and lineage |
| Quality/instruments | 48% | Generic metric values, standards, SPC, point traceability | Missing instrument master, serial/firmware, probe/method, calibration, repeats, reference and import profile |
| Data lineage/flow | 68% | Production run and point aggregation are the correct backbone | Generic JSON bypasses governance; contribution semantics are not target-family specific |
| AI modeling | 38% | Persisted ridge baseline, prediction, diagnosis, recommendation, drift | Training metrics only, no grouped/temporal holdout, applicability scope, OOD, governed artifacts, or causal evidence |
| Workflow/UX | 55% | Real CRUD and closed-loop operations exist | Missing measurement-plan execution, calibration gate, instrument import wizard, trajectory/contribution visualization, controlled-trial workspace |
| Integration/operations | 50% | Integration task framework, auth, audit, local MySQL | Real device/MES/QMS mappings, SSO, backup/DR, observability, and factory acceptance remain |

## High-Priority Findings

### P0 - Scope And Training Integrity

- `ProductionRun.context_values`, stage JSON, seed data, and tests currently allow/use booth temperature and humidity.
- Quality catalog includes `thickness_ed`, `tempc`, `tempf`, and gloss.
- These fields can enter feature snapshots or user workflows despite the approved exclusion boundary.
- Existing persisted snapshots/models trained with excluded features must be marked legacy/quarantined and retrained after scope filtering.

### P0 - Measurement Reliability

- `QualityMeasurement.device_code` is insufficient for BYK/Fischer traceability.
- There is no instrument model/serial/firmware, probe/method, calibration/reference status, repeats, direction, raw-file/import-profile version, or measurement uncertainty model.
- A process diagnosis is unsafe until instrument error and invalid measurement conditions can be ruled out.

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
- Instrument onboarding, calibration status, reference/seal selection, repeat-reading review, and BYK/Fischer import-profile wizards.
- Dürr robot/path and target-family point-contribution visualization instead of only brush tables.
- A quality-engineer review queue that separates measurement/data-quality failures from process failures.
- A process-engineer controlled-trial workspace with hypothesis, coupled changes, constraints, rollback, approval, and sustained verification.
- Model acceptance views that show independent holdout metrics, scope, uncertainty/OOD, drift, and unsupported-use warnings.

### Backend Services

The API has generic CRUD, aggregation, modeling, audit, and integration foundations. Required domain services are:

- Scope-policy validation and quarantine service.
- Instrument/calibration/reference/import-profile validation service.
- Robot/atomizer/trajectory version and contribution service.
- Governed material-characteristic and COA mapping service.
- Dataset snapshot service with grouped/temporal splits and leakage checks.
- Controlled-trial, constraint-source, rollback, and sustained-verification workflow.

### Domain Model And MySQL

Keep the current production-run and measurement-point backbone. Add versioned entities for:

- `coating_system`, factory process-route/bake definition, and execution-stage mapping.
- `robot`, `atomizer`, `controller`, `bell_cup`, `trajectory_program`, `path_segment`, and executed path facts.
- Target-family `point_contribution_version` and contribution evidence.
- `instrument`, `probe`, `measurement_method`, `calibration_record`, `reference_standard`, `import_profile`, and repeated raw readings.
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

1. Enforce the approved scope at catalog, validation, seed, import, feature-snapshot, UI, and test levels; quarantine legacy out-of-scope snapshots/models.
2. Add instrument, probe/method, calibration/reference, repeat-reading, and import-profile models and workflows.
3. Add Dürr robot/atomizer/controller and trajectory/path-version models; version point contribution by target family.
4. Replace generic material COA training fields with governed material characteristic definitions/results.
5. Build leakage-safe dataset snapshots and grouped/temporal model evaluation with acceptance gates.
6. Add engineer-controlled trials, constraint sources, rollback, and sustained verification.
7. Complete real integrations, SSO, backup/DR, observability, and factory acceptance.
