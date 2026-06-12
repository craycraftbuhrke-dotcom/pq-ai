# 3C2B Process And Spray Application

## Business Definition

For PQ-AI, 3C2B means three coating systems and two bake cycles. The product scope starts at midcoat and ends at paint-surface quality inspection.

| Coating system | Execution stages represented in PQ-AI | Primary quality relationships |
| --- | --- | --- |
| Midcoat | Midcoat external spray | Midcoat/total thickness, substrate levelling contribution, downstream orange peel |
| Basecoat | Basecoat pass 1, basecoat pass 2 | Basecoat thickness distribution, hiding, multi-angle color/effect orientation |
| Clearcoat | Clearcoat pass 1, clearcoat pass 2 | Clearcoat/total thickness, levelling, orange peel, DOI |

The exact bake placement and wet-on-wet schedule are factory process definitions. Persist them as versioned factory rules instead of assuming one universal sequence.

## Rotary-Bell Parameter Semantics

Treat parameter effects as interacting, nonlinear, and equipment/material specific.

| Parameter | Physical role | Typical modeled outcomes |
| --- | --- | --- |
| Paint flow | Material delivered per time | Wet/deposited film, pass contribution, sag/coverage risk |
| Bell speed | Atomization energy and droplet-size distribution | Transfer/deposition distribution and appearance; never assume monotonic improvement |
| Inner/outer shaping air | Spray-pattern shape and width | Edge/center distribution, overlap, point contribution |
| Electrostatic voltage/current | Electrostatic attraction and transfer behavior | Transfer efficiency, wrap and distribution; safety/current limits are hard constraints |
| Gun/TCP distance | Flight distance and deposition footprint | Point deposition, pattern width, quality variability |
| TCP/path speed | Dwell per unit area | Film deposition and uniformity |
| Path spacing/orientation | Geometric coverage and overlap | Contribution matrix and local film distribution |
| Trigger timing | Start/stop material delivery relative to path | Edge build and missed/overlap regions |

Store atomizer identity, bell-cup type, controller version, robot identity, program checksum, path version, TCP, path segment, speed, orientation, trigger state, and setpoint/actual values. Do not reduce trajectory programming to one text spray position.

## Point Contribution

The point-level feature matrix is based on approved brush/path contribution versions:

`point feature = aggregate(actual brush/path parameter × contribution weight)`

Contribution weights may come from expert mapping, geometry/simulation, DOE, or fitted deposition models. Store source, method, version, applicability scope, approval, and validation evidence. The weights for different outcomes may differ; thickness contribution is not automatically the same as color-effect or orange-peel contribution.

## Hard Rules

- Never recommend a parameter independently of coupled parameters and device/material limits.
- Use actual executed values when available; preserve configured values for comparison and change control.
- Treat pass ratios as derived, versioned definitions with a documented denominator.
- Require controlled trial and post-change measurement before marking a recommendation effective.
