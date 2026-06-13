---
name: automotive-paint-process-quality
description: Apply the approved PQ-AI automotive paint domain boundary and engineering rules when designing, implementing, reviewing, testing, or documenting 3C2B process, Dürr rotary-bell/robot, paint-material, BYK color/orange-peel, Fischer thickness, point aggregation, quality diagnosis, prediction, and recommendation features.
---

# PQ-AI Automotive Paint Process Quality

Use this skill for every change that touches process stages, parameters, materials, measurement data, feature engineering, AI models, recommendations, or engineer workflows.

## Mandatory Scope

- Include only midcoat, basecoat, clearcoat, paint-surface inspection, Dürr electrostatic rotary-bell application, relevant material characteristics, and BYK/Fischer measurements.
- Model three coating systems: midcoat, basecoat, and clearcoat.
- Model five execution stages: midcoat external spray, basecoat pass 1/2, and clearcoat pass 1/2. Passes are not separate coating systems.
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
9. Treat diagnosis as association unless supported by controlled DOE or other causal evidence.
10. Constrain recommendations by approved device, TDS, program, step-size, and interaction rules; require human approval and post-change measurement.
11. Reject or quarantine out-of-scope features before snapshot creation and training.

## Reference Loading

- Read [process-and-spray.md](references/process-and-spray.md) for 3C2B, rotary-bell parameters, robot paths, and point contribution.
- Read [measurement-and-materials.md](references/measurement-and-materials.md) for BYK/Fischer data and material characteristics.
- Read [engineering-workflow-and-ai.md](references/engineering-workflow-and-ai.md) for engineer workflows, AI datasets, evaluation, diagnosis, and closed-loop recommendation.
- Read [sources.md](references/sources.md) when validating a domain claim or adding a new source.

## Definition Of Done

- Scope and exclusions are explicit in UI, API, schema, seed data, tests, and documentation.
- Every model result is traceable to feature set, training data, model version, applicability scope, and measurement provenance.
- Every recommendation shows evidence, constraints, uncertainty, approval, execution values, and verification results.
- Tests cover scope filtering, traceability, grouped/temporal evaluation, and closed-loop audit behavior.
- Robot/trajectory changes cover device identity, program/path version, checksum matching, target-family contribution, actual execution, and rollback traceability.
- Material changes cover characteristic semantics, canonical unit, method version, specification source/effective period, stage/target-family applicability, batch result reliability, production-time gate, and feature lineage.
