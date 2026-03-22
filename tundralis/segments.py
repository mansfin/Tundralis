from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


GROUP_KEYS = {"all", "any"}
LEAF_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "in",
    "gt",
    "gte",
    "lt",
    "lte",
    "is_null",
    "not_null",
}
NUMERIC_OPERATORS = {"gt", "gte", "lt", "lte"}


@dataclass
class SegmentPreview:
    name: str
    matched_count: int
    matched_pct: float


def _coerce_scalar(value: Any):
    if value is None or isinstance(value, (int, float, bool)):
        return value
    text = str(value).strip()
    if text == "":
        return ""
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _values_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [_coerce_scalar(v) for v in value]
    return [_coerce_scalar(v) for v in str(value).split("|") if str(v).strip()]


def _infer_column_kind(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    coerced = pd.to_numeric(series.dropna(), errors="coerce")
    if not coerced.empty and float(coerced.notna().mean()) >= 0.95:
        return "numeric"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    return "categorical"


def _normalize_leaf_rule(rule: dict[str, Any], df: pd.DataFrame) -> dict[str, Any]:
    column = rule.get("column")
    operator = rule.get("operator")
    if not column:
        raise ValueError("Segment rule is missing column")
    if column not in df.columns:
        raise ValueError(f"Segment rule column not found: {column}")
    if operator not in LEAF_OPERATORS:
        raise ValueError(f"Unsupported segment operator: {operator}")

    kind = rule.get("value_type") or _infer_column_kind(df[column])
    normalized = {"column": column, "operator": operator, "value_type": kind}
    if operator not in {"is_null", "not_null"}:
        normalized["value"] = rule.get("value")
    return normalized


def normalize_segment_tree(tree: dict[str, Any], df: pd.DataFrame) -> dict[str, Any]:
    if not isinstance(tree, dict):
        raise ValueError("Segment tree must be an object")

    group_keys = [key for key in GROUP_KEYS if key in tree]
    if group_keys:
        if len(group_keys) != 1:
            raise ValueError("Segment tree group must use exactly one of 'all' or 'any'")
        key = group_keys[0]
        children = tree.get(key) or []
        if not isinstance(children, list) or not children:
            raise ValueError(f"Segment tree group '{key}' must contain at least one child rule")
        return {key: [normalize_segment_tree(child, df) for child in children]}

    return _normalize_leaf_rule(tree, df)


def normalize_segment_definition(segment: dict[str, Any], df: pd.DataFrame) -> dict[str, Any]:
    name = (segment.get("name") or "").strip()
    if not name:
        raise ValueError("Segment definition is missing name")

    tree = segment.get("tree")
    if tree:
        normalized_tree = normalize_segment_tree(tree, df)
    else:
        rules = segment.get("rules") or []
        logic = str(segment.get("logic") or "AND").upper()
        key = "all" if logic == "AND" else "any"
        normalized_tree = {key: [normalize_segment_tree(rule, df) for rule in rules]}
    return {"name": name, "tree": normalized_tree}


def normalize_segment_definitions(segment_definitions: list[dict] | None, df: pd.DataFrame) -> list[dict]:
    return [normalize_segment_definition(segment, df) for segment in (segment_definitions or [])]


def _evaluate_leaf(rule: dict[str, Any], df: pd.DataFrame) -> pd.Series:
    series = df[rule["column"]]
    operator = rule["operator"]
    kind = rule.get("value_type") or _infer_column_kind(series)

    if operator == "is_null":
        return series.isna()
    if operator == "not_null":
        return series.notna()

    if operator in NUMERIC_OPERATORS or kind == "numeric":
        left = pd.to_numeric(series, errors="coerce")
    else:
        left = series

    value = rule.get("value")
    if operator == "equals":
        return left == _coerce_scalar(value)
    if operator == "not_equals":
        return left != _coerce_scalar(value)
    if operator == "contains":
        return left.astype("string").str.contains(str(value), case=False, na=False)
    if operator == "in":
        return left.isin(_values_list(value))
    if operator == "gt":
        return left > _coerce_scalar(value)
    if operator == "gte":
        return left >= _coerce_scalar(value)
    if operator == "lt":
        return left < _coerce_scalar(value)
    if operator == "lte":
        return left <= _coerce_scalar(value)
    raise ValueError(f"Unsupported segment operator: {operator}")


def evaluate_segment_tree(tree: dict[str, Any], df: pd.DataFrame) -> pd.Series:
    if "all" in tree:
        parts = [evaluate_segment_tree(child, df) for child in tree["all"]]
        mask = pd.Series(True, index=df.index)
        for part in parts:
            mask &= part
        return mask
    if "any" in tree:
        parts = [evaluate_segment_tree(child, df) for child in tree["any"]]
        mask = pd.Series(False, index=df.index)
        for part in parts:
            mask |= part
        return mask
    return _evaluate_leaf(tree, df)


def preview_segments(df: pd.DataFrame, segment_definitions: list[dict] | None) -> list[dict]:
    previews: list[dict] = []
    normalized = normalize_segment_definitions(segment_definitions, df)
    total = len(df)
    for segment in normalized:
        matched = int(evaluate_segment_tree(segment["tree"], df).fillna(False).sum())
        previews.append(
            {
                "name": segment["name"],
                "matched_count": matched,
                "matched_pct": round((matched / total) * 100, 1) if total else 0.0,
                "tree": segment["tree"],
            }
        )
    return previews
