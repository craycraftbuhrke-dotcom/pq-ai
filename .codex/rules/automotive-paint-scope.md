# PQ-AI Automotive Paint Scope Rules

These rules are mandatory for code, schema, APIs, UI, seed data, tests, analytics, and AI features.

## In Scope

- Coating systems: midcoat, basecoat, clearcoat.
- Execution stages: midcoat external spray, basecoat pass 1/2, clearcoat pass 1/2.
- Dürr robot, electrostatic rotary-bell, process setpoints/actuals, and trajectory/contribution data.
- Material batch characteristics affecting film thickness, color, or orange peel.
- BYK color/orange-peel and Fischer thickness measurements.
- Quality targets: thickness, color difference/effect, orange peel.

## Out Of Scope

- Pretreatment, e-coat, sealing, booth temperature/humidity, oven temperature, paint-mix-room data, and gloss.
- Out-of-scope fields must not appear in approved feature snapshots, training data, diagnosis, or recommendations.
- Legacy/out-of-scope persisted data must be quarantined or explicitly marked legacy; do not silently delete it.

## Domain And AI Guardrails

- Three coating systems are not the same as five execution stages.
- Actual values and configured values are separate facts.
- Measurements require instrument/method/calibration provenance.
- Individual pass/layer thickness requires a documented measurement or inference method.
- Point contribution is versioned and approved; it may differ by target family.
- Approved point features require an approved target-family contribution version. A production trajectory checksum mismatch blocks feature generation and AI use.
- Device configuration, trajectory program, path segment, and actual execution are separate versioned facts. Never infer actual execution from the configured program alone.
- Material definition, test method, specification, applicability, batch result, and production use are separate facts. Never infer an approved material feature from a legacy batch field or free-form COA JSON.
- Approved material features require an active stage/target-family applicability and a `VERIFIED` batch result tested no later than production start. A missing required result blocks feature generation and AI use.
- Random point-row train/test splits are prohibited.
- An approved dataset snapshot must freeze feature values, target values, source quality-measurement IDs, group membership, temporal split, and leakage-check result.
- Models are trained only on the training split. Training metrics are never acceptance evidence; activation requires independent validation plus a recorded human acceptance decision.
- Candidate models must generate multi-axis validation evidence: primary temporal holdout, production-group leave-one-out, and factory/model/color axes when the dataset has diversity. Single-value axes must be recorded as insufficient diversity, not treated as validated.
- Candidate models must register a model artifact hash that covers payload, evaluation metrics, dataset reference, and training sample count. Acceptance and activation require a registered, hash-matching artifact.
- Every model must have explicitly approved factory/model/color applicability scopes and an approved statistical OOD blocking policy. Training-data-derived scopes start pending and do not authorize inference until human acceptance.
- Every non-demo model must satisfy an active `FACTORY_APPROVED` acceptance-policy version for every applicable factory and target metric. Demo policies are permitted only for demo models and must never be represented as factory-approved thresholds.
- Prediction, diagnosis, and recommendation must block out-of-scope, incomplete, or out-of-distribution inputs and persist the governance evidence. OOD thresholds are statistical policies, never substitutes for device, material, or process safety limits.
- Model explanations are associations unless supported by controlled causal evidence.
- Recommendations require approved constraints, an approved controlled-trial plan, human approval, execution capture, verification, rollback plan, and sustained observation.
- Never invent factory limits, TDS values, device semantics, instrument fields, or standards.
