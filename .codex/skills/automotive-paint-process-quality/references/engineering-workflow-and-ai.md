# Engineering Workflow And AI

## Process Engineer Workflow

1. Confirm factory/model/color/part/stage scope and active program/material/device versions.
2. Review actual values, point contribution, quality trends, standards, and data quality.
3. Form a testable hypothesis. Mark evidence as association, rule, simulation, DOE, or verified causal evidence.
4. Prepare a constrained change proposal with coupled parameters, expected outcomes, risks, and rollback version.
5. Obtain approval, run a controlled trial, capture actual execution, and compare post-change measurements.
6. Promote, reject, or revise the program version with a complete audit trail.

## Quality Engineer Workflow

1. Maintain measurement plan/group/point, reference/seal standards, instruments, probes, calibration, and import profiles.
2. Execute or import repeated measurements with provenance and validation gates.
3. Review standards, SPC signals, repeatability, outliers, missing values, and instrument status before declaring a process issue.
4. Open a nonconformance/diagnosis task and collaborate on a controlled change.
5. Verify post-change results and monitor sustained performance.

## Training Unit And Matrices

The independent training unit is a production event/body or controlled trial, not an individual point row.

- Feature matrix `X`: one row per production-event × measurement-point × target-family observation, including approved point-level stage contributions, governed material-batch values, program/trajectory/device versions, and scope identifiers.
- Target matrix `Y`: separate target families for thickness, color, and orange peel. Multi-output models are allowed only within a coherent target family and with sufficient data.
- Group identifiers: body/run, batch, program version, factory, model, color, and time.

Never randomly split point rows from the same body/run between train and validation. Use temporal holdout and grouped validation to estimate performance on future production and unseen runs.

The implemented PQ-AI acceptance baseline freezes an immutable dataset snapshot containing point-feature values, target values, source quality-measurement IDs, body/run group membership, train/validation split, temporal cutoff, and leakage-check result. The model service fits only `TRAIN`, reports independent `VALIDATION` metrics, creates a `DRAFT` model, and requires a recorded human acceptance decision before activation. Factory-specific acceptance thresholds, applicability scope, OOD policy, and real factory-run evidence are still mandatory before production use.

## Model Strategy

Start with models suitable for small, correlated industrial tabular data:

- Regularized linear/PLS models for transparent baselines.
- Gradient-boosted trees for nonlinear interactions after leakage-safe validation.
- Hierarchical/mixed-effects or scoped models where factory/model/color effects are material.
- Deep neural networks only after there are enough independent production events, stable labels, and a demonstrated benefit over simpler models.

Record per-scope metrics, uncertainty, out-of-distribution status, drift, missingness, and applicability boundaries. Training-set metrics are never acceptance evidence.

## Diagnosis And Recommendation

- Feature importance/SHAP explains a model prediction, not causality.
- Promote causal claims only after DOE, controlled change, or equivalent evidence.
- Recommendations are constrained optimization proposals, not direct robot commands.
- Validate device limits, TDS/COA rules, approved program boundaries, coupled-parameter rules, maximum step size, and target tradeoffs.
- Require human approval, rollback plan, actual execution values, post-change quality measurement, and sustained-effect monitoring.
