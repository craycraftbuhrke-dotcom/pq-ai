"""Project 3D vehicle-local coordinates onto body-map orthographic views.

Coordinate frame (default Y-up, matching typical GLB exports):
  +X forward (vehicle front)
  +Y up
  +Z right (passenger side when facing forward)

Orthographic mapping onto normalized 2D body-map images (0..1, origin top-left of image):
  RIGHT — look toward -X (see passenger/right flank): u from +Z→−Z flipped to image X, v from +Y
  LEFT  — look toward +X: u from −Z→+Z, v from +Y
  TOP   — look toward -Y: u from +X, v from +Z
  REAR  — look toward +X from rear (see rear fascia): u from +X→−X along lateral? uses (x,y) on rear plane:
          u from −Z→+Z (left→right of rear), v from +Y

Bounds come from view-models.json AABB or DEFAULT_BOUNDS when missing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AxisAlignedBounds:
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float

    def span(self, axis: str) -> float:
        lo, hi = {
            "x": (self.min_x, self.max_x),
            "y": (self.min_y, self.max_y),
            "z": (self.min_z, self.max_z),
        }[axis]
        return max(hi - lo, 1e-6)


# Generic sedan-ish placeholder bounds in meters when manifest omits AABB.
DEFAULT_BOUNDS = AxisAlignedBounds(
    min_x=-2.2,
    max_x=2.2,
    min_y=0.0,
    max_y=1.6,
    min_z=-1.0,
    max_z=1.0,
)

BODY_VIEWS_3D = ("RIGHT", "LEFT", "TOP", "REAR")


def bounds_from_dict(payload: dict | None) -> AxisAlignedBounds:
    if not payload:
        return DEFAULT_BOUNDS
    try:
        return AxisAlignedBounds(
            min_x=float(payload.get("min_x", DEFAULT_BOUNDS.min_x)),
            max_x=float(payload.get("max_x", DEFAULT_BOUNDS.max_x)),
            min_y=float(payload.get("min_y", DEFAULT_BOUNDS.min_y)),
            max_y=float(payload.get("max_y", DEFAULT_BOUNDS.max_y)),
            min_z=float(payload.get("min_z", DEFAULT_BOUNDS.min_z)),
            max_z=float(payload.get("max_z", DEFAULT_BOUNDS.max_z)),
        )
    except (TypeError, ValueError):
        return DEFAULT_BOUNDS


def _norm(value: float, lo: float, hi: float) -> tuple[float, bool]:
    span = max(hi - lo, 1e-6)
    raw = (value - lo) / span
    clamped = min(1.0, max(0.0, raw))
    return clamped, clamped != raw


def project_point_to_view(
    *,
    pos_x: float,
    pos_y: float,
    pos_z: float,
    body_view: str,
    bounds: AxisAlignedBounds | None = None,
) -> tuple[float, float, bool]:
    """Return (layout_x, layout_y, clamped) in image-normalized coords (origin top-left)."""
    box = bounds or DEFAULT_BOUNDS
    view = body_view.strip().upper()
    if view == "RIGHT":
        # Looking from +X toward origin: image X = −Z (front of image = vehicle front optional),
        # use Z left→right of right-side photo as −Z→+Z flipped: u = 1 - norm(z)
        u, c1 = _norm(pos_z, box.min_z, box.max_z)
        u = 1.0 - u
        v, c2 = _norm(pos_y, box.min_y, box.max_y)
        v = 1.0 - v  # image Y grows downward
        return u, v, c1 or c2
    if view == "LEFT":
        u, c1 = _norm(pos_z, box.min_z, box.max_z)
        v, c2 = _norm(pos_y, box.min_y, box.max_y)
        v = 1.0 - v
        return u, v, c1 or c2
    if view == "TOP":
        u, c1 = _norm(pos_x, box.min_x, box.max_x)
        v, c2 = _norm(pos_z, box.min_z, box.max_z)
        v = 1.0 - v
        return u, v, c1 or c2
    if view == "REAR":
        u, c1 = _norm(pos_z, box.min_z, box.max_z)
        v, c2 = _norm(pos_y, box.min_y, box.max_y)
        v = 1.0 - v
        return u, v, c1 or c2
    raise ValueError(f"unsupported body_view for 3D projection: {body_view}")


def project_point_to_all_views(
    *,
    pos_x: float,
    pos_y: float,
    pos_z: float,
    bounds: AxisAlignedBounds | None = None,
) -> dict[str, dict[str, float | bool]]:
    result: dict[str, dict[str, float | bool]] = {}
    for view in BODY_VIEWS_3D:
        layout_x, layout_y, clamped = project_point_to_view(
            pos_x=pos_x,
            pos_y=pos_y,
            pos_z=pos_z,
            body_view=view,
            bounds=bounds,
        )
        result[view] = {
            "layout_x": layout_x,
            "layout_y": layout_y,
            "projected_clamped": clamped,
        }
    return result
