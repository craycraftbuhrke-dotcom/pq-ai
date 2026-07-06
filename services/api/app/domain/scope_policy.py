from collections.abc import Iterable, Mapping

from app.domain.quality_metric_catalog import QUALITY_METRIC_CATALOG


CURRENT_FEATURE_SET_VERSION = "point-features-v4-material-governed"

APPROVED_QUALITY_TYPES = frozenset(
    {"ORANGE_PEEL", "COLOR_DIFFERENCE", "THICKNESS"}
)
APPROVED_METRIC_KEYS = frozenset(
    (metric["quality_type"], metric["code"]) for metric in QUALITY_METRIC_CATALOG
)

OUT_OF_SCOPE_NAME_TOKENS = (
    "booth_temperature",
    "booth_humidity",
    "spray_booth_temperature",
    "spray_booth_humidity",
    "oven_temperature",
    "paint_mix_room",
    "paint_mixing_room",
    "thickness_ed",
    "electrophoresis",
    "gloss",
    "tempc",
    "tempf",
)
OUT_OF_SCOPE_BOUNDARY_TOKENS = ("e_coat", "ecoat")


class ScopeViolation(ValueError):
    pass


def _normalized(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def is_out_of_scope_name(value: str) -> bool:
    normalized = _normalized(value)
    padded = f"_{normalized}_"
    return any(f"_{token}_" in padded for token in OUT_OF_SCOPE_BOUNDARY_TOKENS) or any(
        token in normalized for token in OUT_OF_SCOPE_NAME_TOKENS
    )


def require_approved_quality_type(quality_type: str) -> None:
    if quality_type not in APPROVED_QUALITY_TYPES:
        raise ScopeViolation(
            f"质量类型 {quality_type} 超出项目范围；仅允许膜厚、色差/效应和橘皮"
        )


def require_approved_metric(quality_type: str, metric_code: str) -> None:
    require_approved_quality_type(quality_type)
    if (quality_type, metric_code) not in APPROVED_METRIC_KEYS:
        raise ScopeViolation(
            f"质量指标 {quality_type}/{metric_code} 不在当前受治理指标目录中"
        )


def require_approved_metrics(quality_type: str, metric_codes: Iterable[str]) -> None:
    for metric_code in metric_codes:
        require_approved_metric(quality_type, metric_code)


def require_approved_target_metric(metric_code: str) -> None:
    matches = [
        quality_type
        for quality_type, approved_metric_code in APPROVED_METRIC_KEYS
        if approved_metric_code == metric_code
    ]
    if len(matches) != 1:
        raise ScopeViolation(f"模型目标指标 {metric_code} 不在当前项目范围内")


def target_family_for_metric(metric_code: str) -> str:
    matches = [
        quality_type
        for quality_type, approved_metric_code in APPROVED_METRIC_KEYS
        if approved_metric_code == metric_code
    ]
    if len(matches) != 1:
        raise ScopeViolation(f"模型目标指标 {metric_code} 不在当前项目范围内")
    return matches[0]


def require_approved_quality_types(quality_types: Iterable[str]) -> None:
    for quality_type in quality_types:
        require_approved_quality_type(quality_type)


def out_of_scope_mapping_keys(values: Mapping | None) -> list[str]:
    if not values:
        return []
    return sorted(str(key) for key in values if is_out_of_scope_name(str(key)))


def require_approved_mapping(values: Mapping | None, label: str) -> None:
    rejected = out_of_scope_mapping_keys(values)
    if rejected:
        raise ScopeViolation(f"{label}包含项目范围外字段：{', '.join(rejected)}")


def approved_numeric_values(values: Mapping | None) -> dict[str, float]:
    if not values:
        return {}
    return {
        str(key): float(value)
        for key, value in values.items()
        if isinstance(value, int | float)
        and not isinstance(value, bool)
        and not is_out_of_scope_name(str(key))
    }


def require_scope_safe_model(
    target_metric: str,
    feature_set_version: str,
    feature_names: Iterable[str],
) -> None:
    require_approved_target_metric(target_metric)
    if feature_set_version != CURRENT_FEATURE_SET_VERSION:
        raise ScopeViolation(
            f"模型特征版本 {feature_set_version} 未获批准；必须使用 "
            f"{CURRENT_FEATURE_SET_VERSION} 重新训练"
        )
    rejected = sorted(name for name in feature_names if is_out_of_scope_name(name))
    if rejected:
        raise ScopeViolation(f"模型包含项目范围外特征：{', '.join(rejected)}")
