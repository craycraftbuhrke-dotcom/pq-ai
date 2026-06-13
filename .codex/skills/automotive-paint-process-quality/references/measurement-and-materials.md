# Measurement And Materials

## BYK Multi-Angle Color

BYK-mac i combines multi-angle color with effect characterization. The official BYK description lists traditional color angles at 15°, 25°, 45°, 75°, and 110°, an additional behind-gloss angle for interference pigments, plus sparkle and graininess characterization.

Data requirements:

- Instrument model, serial, firmware, export schema, calibration/reference status, standard/sample relationship, measurement direction, operator, timestamp, and repeat number.
- Preserve raw instrument fields separately from calculated differences.
- `dL`, `da`, `db`, `dC`, `dH`, and `dE` are differences against a reference, not raw L*a*b* values.
- Preserve effect metrics with their exact instrument/export semantics. Do not map ambiguous `dS`, `dSi`, `dSa`, or `dG` fields without a versioned import profile.

## BYK Orange Peel

BYK wave-scan evaluates surface waviness/structure by wavelength ranges. BYK documents LW as longer-wave waviness and SW as fine texture; wave-scan DOI extends evaluation with multiple wavelength ranges and distinctness of image.

Data requirements:

- Store instrument/export profile because Wa/Wb/Wc/Wd/We, LW, SW, DOI, dullness, and rating availability depends on model/firmware.
- Store direction, repeated readings, raw values, invalid flags, and reference/check status.
- Use a structure spectrum for diagnosis. A single score loses information needed to distinguish material levelling from application-pattern effects.

## Fischer Coating Thickness

Magnetic induction measures non-magnetic coatings such as paint on magnetic substrates such as steel. Amplitude-sensitive eddy current measures non-conductive/non-magnetic coatings on conductive non-magnetic substrates such as aluminum. Both are comparative methods that require suitable calibration.

Data requirements:

- Instrument model/serial, probe, measurement method, substrate/material, calibration/zero/reference record, curvature/geometry class, repeat number, raw/corrected value, operator, and timestamp.
- Probe placement, curvature, roughness, substrate properties, and operator technique affect results.
- A normal magnetic-induction/eddy-current total-film reading does not by itself prove individual pass/layer thickness. Every layer/pass thickness value must state its measurement or inference method.
- Exclude e-coat thickness from PQ-AI. Total thickness may include underlying layers physically, but the target definition and interpretation must be documented.

## Paint Material Features

Only capture material characteristics plausibly related to thickness, color, or orange peel:

| Feature | Required metadata | Main relationships |
| --- | --- | --- |
| Viscosity/rheology result | Test method, spindle/cup, shear condition, test temperature if supplied by the source, time, unit | Atomization, flow/levelling, film build, orange peel |
| Solids content | Test method, unit, sample time | Deposited dry-film relationship and hiding/build |
| Density | Method, unit, sample time | Flow-to-mass/film conversion |
| Pigment/effect identity and batch values | Supplier, material code, batch, COA field semantics | Multi-angle color/effect response |
| Surface-tension/levelling-related COA value | Method and source semantics | Orange peel/levelling diagnosis |

Do not accept an unversioned free-form COA JSON as production-grade training data. Promote approved fields into governed definitions with units, methods, ranges, and source lineage.

## Governed Material Contract

An approved material feature is the result of five linked facts:

1. Characteristic definition: stable code, meaning, canonical unit, allowed quality target families, and model-feature flag.
2. Test method: characteristic, method code/version, method type, result unit, conditions, procedure source, and lifecycle status.
3. Material specification: material code, characteristic, method, version, optional lower/upper limits, source, effective period, approval, and lifecycle status.
4. Applicability: characteristic × material type × execution stage × quality target family, including whether the feature is required.
5. Batch test result: batch, characteristic, method, value/unit, test time/operator, source/raw values, matched specification, and derived reliability.

Reliability is derived, not manually asserted:

- `FAILED`: inactive/mismatched definition or method, inconsistent unit, or value outside an approved numeric specification.
- `UNVERIFIED`: no time-valid active specification or no result source.
- `VERIFIED`: no failed or unresolved governance checks.

Only a `VERIFIED` result tested at or before the linked production run start can enter an approved point feature. A missing required result blocks snapshot generation. Legacy batch viscosity, solids, and free-form COA values remain traceability fields and do not bypass this contract.
