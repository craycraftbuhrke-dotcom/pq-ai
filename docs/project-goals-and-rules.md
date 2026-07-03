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
