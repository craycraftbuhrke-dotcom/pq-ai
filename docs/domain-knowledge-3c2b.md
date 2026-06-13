# PQ-AI 3C2B Domain Knowledge Baseline

## 1. Process Model

PQ-AI uses a strict three-layer/five-execution-stage model:

```text
Midcoat system
  -> Midcoat external spray
Basecoat system
  -> Basecoat pass 1
  -> Basecoat pass 2
Clearcoat system
  -> Clearcoat pass 1
  -> Clearcoat pass 2
Quality inspection
  -> Thickness / color / orange peel
```

The “two bake” placement is a factory process definition and must be versioned during onboarding. Basecoat and clearcoat passes are separate spray contributions, not four additional coating systems.

## 2. Process-To-Quality Mechanism

The point-level result is created by coupled application, material, geometry, and measurement effects:

```text
program/path version + brush/path geometry + actual rotary-bell parameters
  + material batch characteristics
  + approved point contribution
  -> local deposited/formed film
  -> instrument measurement with its own uncertainty
```

Key application variables are paint flow, bell speed, inner/outer shaping air, electrostatic voltage/current, TCP distance, path speed, path spacing/orientation, trigger timing, and overlap. Their effects are nonlinear and equipment/material specific. Numeric limits must come from approved Dürr/factory documentation and trials.

For data governance, distinguish four facts: approved device combination, approved trajectory file/version/checksum, configured path-segment values, and actual production execution. A matching program name is insufficient evidence that the approved file ran. A checksum mismatch is a data-integrity failure and must block approved AI feature generation until reviewed.

## 3. Material-To-Quality Mechanism

- Viscosity/rheology influences atomization, flow, levelling, film build, and orange peel.
- Solids content and density influence the relationship between delivered material and dry film.
- Pigment/effect batch characteristics influence multi-angle color/effect response.
- Surface-tension/levelling-related characteristics may influence appearance.

Every material result needs a method, unit, sample time, batch, supplier, source, and approved field definition. Free-form COA fields cannot be trusted as stable AI features until governed.

## 4. Measurement Principles And Data Meaning

### BYK Color

BYK-mac i measures multi-angle color and effect characteristics. Difference values such as `dL`, `da`, `db`, `dC`, `dH`, and `dE` depend on a reference standard; they are not raw color coordinates. Store the reference/seal standard and exact export profile.

### BYK Orange Peel

Wave-scan data represents surface structure across wavelength ranges. LW, SW, Wa-We, DOI, dullness, and ratings must keep their instrument/firmware/export semantics. Preserve the structure spectrum instead of only a total score.

### Fischer Thickness

Magnetic induction is suitable for non-magnetic paint on magnetic substrates such as steel. Amplitude-sensitive eddy current is suitable for non-conductive/non-magnetic coatings on conductive non-magnetic substrates such as aluminum. Calibration, substrate, probe, geometry, roughness, repeats, and operator technique affect results.

A normal total-thickness reading cannot automatically be assigned to individual passes. Each layer/pass thickness value must state whether it is measured, inferred, or produced by another method.

## 5. Engineer Closed Loop

```text
measurement plan and calibration
  -> production actuals and quality results
  -> data-quality/standard/SPC review
  -> hypothesis and evidence
  -> constrained change proposal
  -> approval and controlled trial
  -> actual execution capture
  -> post-change measurement
  -> sustained-effect review and program decision
```

The quality engineer owns measurement reliability and conformity evidence. The process engineer owns program/path/material/process change hypotheses and controlled trials. PQ-AI coordinates evidence and audit; it does not replace engineering accountability.

## 6. AI Modeling Baseline

- Independent sample unit: production body/run or controlled trial, not each point row.
- Feature matrix: production event × measurement point, with point-weighted actual stage parameters, governed material values, program/path/device versions, and scope identifiers.
- Target families: thickness, color, and orange peel are trained and evaluated separately.
- Validation: grouped by run/body/batch and held out by time to prevent leakage.
- Initial models: regularized linear/PLS and boosted trees; deep learning only after enough independent runs and stable labels.
- Diagnosis: SHAP/importance indicates association, not causality.
- Recommendation: constrained optimization with human approval and post-change verification.

## 7. Source Baseline

The maintained source list is in
[the project skill](../.codex/skills/automotive-paint-process-quality/references/sources.md).
