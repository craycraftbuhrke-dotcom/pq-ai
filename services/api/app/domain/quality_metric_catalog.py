def _metric(
    quality_type: str,
    code: str,
    name: str | None = None,
    unit: str | None = None,
    primary: bool = False,
) -> dict:
    return {
        "quality_type": quality_type,
        "code": code,
        "name": name or code,
        "unit": unit,
        "is_primary": primary,
    }


ORANGE_PEEL_METRICS = [
    _metric("ORANGE_PEEL", code, code.upper(), primary=code in {"doi", "lw", "sw"})
    for code in ("du", "wa", "wb", "wc", "wd", "we", "sw", "lw", "r", "doi", "b", "score")
]

COLOR_DIFFERENCE_CODES = [
    "det",
    *[f"de{angle}" for angle in (15, 25, 45, 75, 110)],
    *[f"dl{angle}" for angle in (15, 25, 45, 75, 110)],
    *[f"da{angle}" for angle in (15, 25, 45, 75, 110)],
    *[f"db{angle}" for angle in (15, 25, 45, 75, 110)],
    *[f"dc{angle}" for angle in (15, 25, 45, 75, 110)],
    *[f"dh{angle}" for angle in (15, 25, 45, 75, 110)],
    "a45",
    "dst",
    "ds",
    "ds15",
    "ds45",
    "ds75",
    "dsi15",
    "dsi45",
    "dsi75",
    "dsa15",
    "dsa45",
    "dsa75",
    "dg",
]

COLOR_DIFFERENCE_METRICS = [
    _metric(
        "COLOR_DIFFERENCE",
        code,
        code,
        None,
        primary=code in {"det", "de45"},
    )
    for code in COLOR_DIFFERENCE_CODES
]

THICKNESS_METRICS = [
    _metric("THICKNESS", code, name, "μm", code == "thickness_total")
    for code, name in (
        ("thickness_midcoat", "中涂膜厚"),
        ("thickness_basecoat_pass1", "色漆一站膜厚"),
        ("thickness_basecoat_pass2", "色漆二站膜厚"),
        ("thickness_clearcoat_pass1", "清漆一站膜厚"),
        ("thickness_clearcoat_pass2", "清漆二站膜厚"),
        ("thickness_total", "总膜厚"),
    )
]

QUALITY_METRIC_CATALOG = [
    *ORANGE_PEEL_METRICS,
    *COLOR_DIFFERENCE_METRICS,
    *THICKNESS_METRICS,
]

for order, metric in enumerate(QUALITY_METRIC_CATALOG, start=1):
    metric["display_order"] = order
