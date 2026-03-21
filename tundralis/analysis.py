"""Statistical analysis: correlation, OLS regression, relative importance."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm

logger = logging.getLogger(__name__)


# ─── Result containers ────────────────────────────────────────────────────────

@dataclass
class CorrelationResults:
    pearson: pd.DataFrame       # columns: predictor, r, p_value, significant
    spearman: pd.DataFrame      # same shape


@dataclass
class RegressionResults:
    model_summary: str
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    f_p_value: float
    coefficients: pd.DataFrame  # predictor, coef, std_coef, t_stat, p_value, significant


@dataclass
class ImportanceResults:
    shapley: pd.DataFrame       # predictor, importance, importance_pct
    ranking: pd.DataFrame       # predictor, rank, importance, importance_pct, label


@dataclass
class QuadrantResults:
    quadrant_df: pd.DataFrame   # predictor, importance, performance, quadrant


@dataclass
class KDAResults:
    target: str
    predictors: list[str]
    n_obs: int
    correlations: CorrelationResults
    regression: RegressionResults
    importance: ImportanceResults
    quadrants: QuadrantResults
    meta: dict = field(default_factory=dict)


# ─── Analysis functions ───────────────────────────────────────────────────────

def compute_correlations(
    X: pd.DataFrame,
    y: pd.Series,
) -> CorrelationResults:
    """Pearson and Spearman correlations between each predictor and y."""
    pearson_rows, spearman_rows = [], []

    for col in X.columns:
        x_col = X[col]

        pr, pp = stats.pearsonr(x_col, y)
        pearson_rows.append({
            "predictor": col,
            "r": round(pr, 4),
            "p_value": round(pp, 4),
            "significant": pp < 0.05,
        })

        sr, sp = stats.spearmanr(x_col, y)
        spearman_rows.append({
            "predictor": col,
            "r": round(sr, 4),
            "p_value": round(sp, 4),
            "significant": sp < 0.05,
        })

    return CorrelationResults(
        pearson=pd.DataFrame(pearson_rows).sort_values("r", ascending=False),
        spearman=pd.DataFrame(spearman_rows).sort_values("r", ascending=False),
    )


def run_ols_regression(
    X: pd.DataFrame,
    y: pd.Series,
) -> RegressionResults:
    """OLS regression with standardized coefficients (betas)."""
    # Standardize for betas
    scaler_X = StandardScaler()
    scaler_y = StandardScaler()
    X_std = scaler_X.fit_transform(X)
    y_std = scaler_y.fit_transform(y.values.reshape(-1, 1)).ravel()

    X_std_df = pd.DataFrame(X_std, columns=X.columns)

    # statsmodels for full summary
    X_with_const = sm.add_constant(X)
    model = sm.OLS(y, X_with_const).fit()

    # statsmodels standardized model
    X_std_const = sm.add_constant(X_std_df)
    std_model = sm.OLS(y_std, X_std_const).fit()

    coef_rows = []
    for col in X.columns:
        coef_rows.append({
            "predictor": col,
            "coef": round(model.params[col], 4),
            "std_coef": round(std_model.params[col], 4),
            "t_stat": round(model.tvalues[col], 4),
            "p_value": round(model.pvalues[col], 4),
            "significant": model.pvalues[col] < 0.05,
        })

    coef_df = pd.DataFrame(coef_rows).sort_values("std_coef", ascending=False)

    return RegressionResults(
        model_summary=model.summary().as_text(),
        r_squared=round(model.rsquared, 4),
        adj_r_squared=round(model.rsquared_adj, 4),
        f_statistic=round(model.fvalue, 4),
        f_p_value=round(model.f_pvalue, 4),
        coefficients=coef_df,
    )


def _compute_shapley_importance(
    X: pd.DataFrame,
    y: pd.Series,
) -> np.ndarray:
    """
    Compute Shapley-based relative importance (Johnson's epsilon approximation).

    Uses the sequential R² decomposition averaged over all variable orderings —
    a tractable approximation for n_predictors <= ~12. For larger models,
    we use a sampling-based approach.
    """
    n = len(X.columns)
    predictors = list(X.columns)

    # For small models: exact Shapley via all permutations
    from itertools import permutations
    from sklearn.linear_model import LinearRegression

    if n <= 8:
        orderings = list(permutations(range(n)))
    else:
        # Sample 500 random permutations
        rng = np.random.default_rng(42)
        orderings = [rng.permutation(n).tolist() for _ in range(500)]

    shapley = np.zeros(n)
    X_arr = X.values
    y_arr = y.values

    def r2(cols):
        if not cols:
            return 0.0
        reg = LinearRegression().fit(X_arr[:, cols], y_arr)
        ss_res = np.sum((y_arr - reg.predict(X_arr[:, cols])) ** 2)
        ss_tot = np.sum((y_arr - y_arr.mean()) ** 2)
        if ss_tot == 0:
            return 0.0
        return max(0.0, 1 - ss_res / ss_tot)

    # Cache R² values for subsets
    cache: dict[tuple, float] = {}

    for order in orderings:
        prev_cols: list[int] = []
        for j, col_idx in enumerate(order):
            key_prev = tuple(sorted(prev_cols))
            key_curr = tuple(sorted(prev_cols + [col_idx]))

            if key_prev not in cache:
                cache[key_prev] = r2(list(key_prev))
            if key_curr not in cache:
                cache[key_curr] = r2(list(key_curr))

            marginal = cache[key_curr] - cache[key_prev]
            shapley[col_idx] += marginal
            prev_cols.append(col_idx)

    shapley /= len(orderings)

    # Clip negatives (numerical noise) and normalize to sum to R²
    shapley = np.maximum(shapley, 0)
    total = shapley.sum()
    if total > 0:
        # Scale so they sum to total R²
        full_r2 = r2(list(range(n)))
        shapley = shapley / total * full_r2

    return shapley


def compute_relative_importance(
    X: pd.DataFrame,
    y: pd.Series,
) -> ImportanceResults:
    """Compute Shapley-based relative importance values."""
    logger.info("Computing Shapley importance (this may take a moment)...")
    shapley_vals = _compute_shapley_importance(X, y)

    total = shapley_vals.sum()
    pct = (shapley_vals / total * 100) if total > 0 else np.zeros_like(shapley_vals)

    shapley_df = pd.DataFrame({
        "predictor": X.columns,
        "importance": shapley_vals.round(4),
        "importance_pct": pct.round(2),
    }).sort_values("importance", ascending=False).reset_index(drop=True)

    ranking_df = shapley_df.copy()
    ranking_df["rank"] = range(1, len(ranking_df) + 1)
    ranking_df["label"] = ranking_df["predictor"].apply(
        lambda c: c.replace("_", " ").title()
    )

    return ImportanceResults(shapley=shapley_df, ranking=ranking_df)


def build_quadrant_mapping(
    X: pd.DataFrame,
    y: pd.Series,
    importance: ImportanceResults,
) -> QuadrantResults:
    """
    Map drivers onto Importance vs Performance quadrant.

    - Importance: Shapley relative importance (derived)
    - Performance: Mean score of the predictor (stated/observed)
    Both are normalized to 0–1 scale. Quadrant cutoffs at medians.
    """
    from tundralis.utils import scale_to_range

    imp_arr = importance.ranking.set_index("predictor")["importance"].reindex(X.columns).values
    perf_arr = X.mean().values

    imp_scaled = scale_to_range(imp_arr)
    perf_scaled = scale_to_range(perf_arr)

    imp_median = np.median(imp_scaled)
    perf_median = np.median(perf_scaled)

    def _quadrant(imp, perf):
        if imp >= imp_median and perf >= perf_median:
            return "Strengths"          # High importance, high performance → keep it up
        elif imp >= imp_median and perf < perf_median:
            return "Priority Fixes"     # High importance, low performance → urgent
        elif imp < imp_median and perf >= perf_median:
            return "Nice-to-Haves"      # Low importance, high performance → overkill
        else:
            return "Low Priority"       # Low importance, low performance → monitor

    quadrant_df = pd.DataFrame({
        "predictor": X.columns,
        "label": [c.replace("_", " ").title() for c in X.columns],
        "importance": imp_scaled.round(4),
        "performance": perf_scaled.round(4),
        "importance_raw": imp_arr.round(4),
        "performance_raw": perf_arr.round(4),
        "quadrant": [_quadrant(i, p) for i, p in zip(imp_scaled, perf_scaled)],
    })

    return QuadrantResults(quadrant_df=quadrant_df)


def run_kda(
    X: pd.DataFrame,
    y: pd.Series,
    target_name: str,
) -> KDAResults:
    """Run the full KDA pipeline and return all results."""
    logger.info("=== Key Driver Analysis: '%s' ===", target_name)
    logger.info("N=%d  Predictors=%d", len(y), len(X.columns))

    correlations = compute_correlations(X, y)
    regression = run_ols_regression(X, y)
    importance = compute_relative_importance(X, y)
    quadrants = build_quadrant_mapping(X, y, importance)

    return KDAResults(
        target=target_name,
        predictors=list(X.columns),
        n_obs=len(y),
        correlations=correlations,
        regression=regression,
        importance=importance,
        quadrants=quadrants,
        meta={
            "r_squared": regression.r_squared,
            "adj_r_squared": regression.adj_r_squared,
        },
    )
