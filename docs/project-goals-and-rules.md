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
2. The database stores facts and lineage; generic JSON is an ingestion bridge, not the final governed model.
3. AI starts with leakage-safe baselines and earns complexity through measured improvement.
4. Diagnosis distinguishes association from verified causality.
5. Recommendations are constrained, explainable, approved, reversible, executed as a trial, and verified with quality data.
6. No model is production-ready until validated with real independent factory runs and accepted by process and quality engineers.

## Development Gate

Every new feature must pass:

- Scope check: no excluded fields or processes.
- Traceability check: source, version, applicability, and audit are present.
- Domain check: coating system, execution stage, measurement semantics, and units are correct.
- Data check: validation, missingness, repetition, and lineage are handled.
- AI check: grouped/temporal evaluation, uncertainty, applicability, and drift are handled.
- Workflow check: engineer decision, approval, rollback, and verification are represented.
