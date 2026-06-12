def _stage_parameters(prefix: str, category: str) -> list[dict]:
    return [
        {
            "code": f"{prefix}_spray_flow",
            "name": f"{category}喷涂流量",
            "category": category,
            "unit": "ml/min",
        },
        {
            "code": f"{prefix}_bell_speed",
            "name": f"{category}旋杯转速",
            "category": category,
            "unit": "rpm",
        },
        {
            "code": f"{prefix}_outer_air",
            "name": f"{category}外成型空气流量",
            "category": category,
            "unit": "Nl/min",
        },
        {
            "code": f"{prefix}_inner_air",
            "name": f"{category}内成型空气流量",
            "category": category,
            "unit": "Nl/min",
        },
        {
            "code": f"{prefix}_voltage",
            "name": f"{category}静电高压",
            "category": category,
            "unit": "kV",
        },
    ]


PARAMETER_CATALOG: list[dict] = [
    *_stage_parameters("midcoat", "中涂外喷"),
    *_stage_parameters("basecoat_1", "色漆一站"),
    *_stage_parameters("basecoat_2", "色漆二站"),
    *_stage_parameters("clearcoat_1", "清漆一站"),
    *_stage_parameters("clearcoat_2", "清漆二站"),
    {
        "code": "basecoat_pass_ratio",
        "name": "色漆一二站比例",
        "category": "色漆",
        "unit": "%",
    },
    {
        "code": "clearcoat_pass_ratio",
        "name": "清漆一二站比例",
        "category": "清漆",
        "unit": "%",
    },
    *[
        {
            "code": f"{prefix}_{suffix}",
            "name": f"{name}{label}",
            "category": name,
            "unit": unit,
        }
        for prefix, name in (("midcoat", "中涂"), ("basecoat", "色漆"), ("clearcoat", "清漆"))
        for suffix, label, unit in (
            ("gun_distance", "喷枪距离", "mm"),
            ("gun_spacing", "喷枪间距", "mm"),
            ("spray_speed", "喷涂速度", "mm/s"),
        )
    ],
    *[
        {
            "code": f"{prefix}_{suffix}",
            "name": f"{name}{label}",
            "category": f"{name}材料",
            "unit": unit,
            "is_recommendable": False,
        }
        for prefix, name in (("midcoat", "中涂"), ("basecoat", "色漆"), ("clearcoat", "清漆"))
        for suffix, label, unit in (
            ("viscosity", "粘度", "s"),
            ("solid_ratio", "固含比", "%"),
        )
    ],
]

for parameter in PARAMETER_CATALOG:
    parameter.setdefault("aggregation_method", "WEIGHTED_AVERAGE")
    # Factory-specific hard boundaries must be configured before recommendations are enabled.
    parameter.setdefault("is_recommendable", False)
