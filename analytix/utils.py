"""Data loading, validation, and helper utilities."""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ─── Brand colors ────────────────────────────────────────────────────────────
BRAND_DARK_BLUE = "#1B2A4A"
BRAND_TEAL = "#2EC4B6"
BRAND_WHITE = "#FFFFFF"
BRAND_LIGHT_GRAY = "#F4F6F8"
BRAND_MID_GRAY = "#8C9BB2"
BRAND_ACCENT_ORANGE = "#FF6B35"
BRAND_ACCENT_YELLOW = "#FFD166"


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def load_survey_data(path: str | Path) -> pd.DataFrame:
    """Load CSV survey data and return a cleaned DataFrame."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    df = pd.read_csv(path)
    logger.info("Loaded %d rows × %d columns from %s", *df.shape, path.name)
    return df


def validate_columns(
    df: pd.DataFrame,
    target: str,
    predictors: list[str],
) -> None:
    """Raise ValueError if required columns are missing or invalid."""
    missing = [c for c in [target] + predictors if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in dataset: {missing}")

    # Check for numeric types
    for col in [target] + predictors:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Column '{col}' must be numeric.")

    # Warn about missing values
    nulls = df[[target] + predictors].isnull().sum()
    if nulls.any():
        logger.warning("Null values detected:\n%s", nulls[nulls > 0])


def prepare_data(
    df: pd.DataFrame,
    target: str,
    predictors: list[str],
    dropna: bool = True,
) -> tuple[pd.DataFrame, pd.Series]:
    """Return (X, y) with optional NA drop."""
    cols = [target] + predictors
    subset = df[cols]
    if dropna:
        before = len(subset)
        subset = subset.dropna()
        dropped = before - len(subset)
        if dropped:
            logger.info("Dropped %d rows with NAs.", dropped)

    X = subset[predictors]
    y = subset[target]
    return X, y


def standardize(df: pd.DataFrame) -> pd.DataFrame:
    """Z-score standardize all columns."""
    return (df - df.mean()) / df.std(ddof=1)


def scale_to_range(arr: np.ndarray, lo: float = 0, hi: float = 1) -> np.ndarray:
    """Min-max scale array to [lo, hi]."""
    mn, mx = arr.min(), arr.max()
    if mx == mn:
        return np.full_like(arr, (lo + hi) / 2, dtype=float)
    return lo + (arr - mn) / (mx - mn) * (hi - lo)


def human_label(col: str) -> str:
    """Convert snake_case column names to 'Title Case' labels."""
    return col.replace("_", " ").title()


def output_path(output_dir: str | Path, filename: str) -> Path:
    """Return full path inside output_dir, creating it if needed."""
    p = Path(output_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p / filename
