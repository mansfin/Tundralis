"""Input contract resolution and validation for Tundralis KDA."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import pandas as pd


@dataclass
class ResolvedConfig:
    target_column: str
    predictor_columns: list[str]
    respondent_id_column: str | None = None
    weight_column: str | None = None
    segment_columns: list[str] | None = None
    excluded_columns: list[str] | None = None
    scale_metadata: dict | None = None


def load_mapping_config(path: str | Path | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Mapping config not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def infer_predictors(df: pd.DataFrame, target: str, excluded: set[str] | None = None) -> list[str]:
    excluded = excluded or set()
    numerics = df.select_dtypes(include="number").columns.tolist()
    exclude_patterns = {target, "id", "respondent_id", "record_id", "row_id", "index"} | excluded
    return [
        c for c in numerics
        if c != target and c.lower() not in exclude_patterns and not c.lower().endswith("_id")
    ]


def resolve_config(df: pd.DataFrame, cli_args, mapping: dict | None = None) -> ResolvedConfig:
    mapping = mapping or {}

    target = cli_args.target or mapping.get("target_column")
    if not target:
        raise ValueError("A target column is required. Provide --target or target_column in the mapping config.")
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' was not found in the input file.")

    excluded = set(mapping.get("excluded_columns", []))
    respondent_id = mapping.get("respondent_id_column")
    weight_column = mapping.get("weight_column")
    segment_columns = mapping.get("segment_columns", [])
    scale_metadata = mapping.get("scale_metadata", {})

    if cli_args.predictors:
        predictors = cli_args.predictors
    else:
        predictors = mapping.get("predictor_columns") or infer_predictors(df, target, excluded=excluded)

    if not predictors:
        raise ValueError("No valid predictor columns were resolved.")

    return ResolvedConfig(
        target_column=target,
        predictor_columns=predictors,
        respondent_id_column=respondent_id,
        weight_column=weight_column,
        segment_columns=segment_columns,
        excluded_columns=sorted(excluded),
        scale_metadata=scale_metadata,
    )


def validate_resolved_config(df: pd.DataFrame, config: ResolvedConfig) -> None:
    missing = [c for c in [config.target_column] + config.predictor_columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in dataset: {missing}")

    if not pd.api.types.is_numeric_dtype(df[config.target_column]):
        raise ValueError(f"Target column '{config.target_column}' must be numeric.")

    invalid_predictors = [c for c in config.predictor_columns if not pd.api.types.is_numeric_dtype(df[c])]
    if invalid_predictors:
        raise ValueError(
            f"Predictor columns must be numeric in v1. Invalid columns: {invalid_predictors}"
        )

    if df[config.target_column].dropna().nunique() < 2:
        raise ValueError(f"Target column '{config.target_column}' must have at least 2 distinct non-null values.")

    valid_predictors = [c for c in config.predictor_columns if df[c].dropna().nunique() >= 2]
    if not valid_predictors:
        raise ValueError("No predictor columns have enough variance to model.")


def build_validation_summary(df: pd.DataFrame, config: ResolvedConfig) -> dict:
    rows_input = int(len(df))
    rows_with_valid_dv = int(df[config.target_column].notna().sum())
    rows_with_valid_dv_and_any_predictor = int(
        df.loc[df[config.target_column].notna(), config.predictor_columns].notna().any(axis=1).sum()
    )
    missing_by_variable = {
        col: {
            "missing_count": int(df[col].isna().sum()),
            "missing_rate": round(float(df[col].isna().mean()), 4),
        }
        for col in [config.target_column] + config.predictor_columns
    }
    return {
        "rows_input": rows_input,
        "rows_with_valid_dv": rows_with_valid_dv,
        "rows_with_valid_dv_and_any_predictor": rows_with_valid_dv_and_any_predictor,
        "predictor_count": len(config.predictor_columns),
        "missingness": {"by_variable": missing_by_variable},
    }
