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
- Random point-row train/test splits are prohibited.
- Model explanations are associations unless supported by controlled causal evidence.
- Recommendations require approved constraints, human approval, execution capture, verification, and rollback.
- Never invent factory limits, TDS values, device semantics, instrument fields, or standards.
