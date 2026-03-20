"""Publication-quality chart generation for KDA reports."""

from __future__ import annotations

import io
import logging
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ─── Brand palette ────────────────────────────────────────────────────────────
DARK_BLUE = "#1B2A4A"
TEAL = "#2EC4B6"
WHITE = "#FFFFFF"
LIGHT_GRAY = "#F4F6F8"
MID_GRAY = "#8C9BB2"
ACCENT_ORANGE = "#FF6B35"
ACCENT_YELLOW = "#FFD166"

QUADRANT_COLORS = {
    "Priority Fixes": "#E63946",
    "Strengths": "#2EC4B6",
    "Nice-to-Haves": "#A8DADC",
    "Low Priority": "#8C9BB2",
}


def _brand_fig(fig, ax=None):
    """Apply brand styling to a figure."""
    fig.patch.set_facecolor(WHITE)
    if ax is not None:
        axs = [ax] if not hasattr(ax, "__iter__") else ax
        for a in axs:
            a.set_facecolor(WHITE)
            a.spines["top"].set_visible(False)
            a.spines["right"].set_visible(False)
            a.spines["left"].set_color("#D0D5DD")
            a.spines["bottom"].set_color("#D0D5DD")
            a.tick_params(colors=DARK_BLUE, labelsize=9)
            a.xaxis.label.set_color(DARK_BLUE)
            a.yaxis.label.set_color(DARK_BLUE)
            a.title.set_color(DARK_BLUE)


def _fig_to_bytes(fig) -> bytes:
    """Render figure to PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def chart_importance_bar(ranking_df: pd.DataFrame, title: str = "Key Drivers of Satisfaction") -> bytes:
    """Horizontal bar chart of relative importance values."""
    df = ranking_df.sort_values("importance", ascending=True)
    n = len(df)

    fig, ax = plt.subplots(figsize=(9, max(4, n * 0.55)))
    _brand_fig(fig, ax)

    # Color gradient: top drivers are darker teal
    colors = [TEAL if i >= n - 3 else MID_GRAY for i in range(n)]

    bars = ax.barh(
        df["label"],
        df["importance_pct"],
        color=colors,
        height=0.6,
        zorder=3,
    )

    # Value labels
    for bar, val in zip(bars, df["importance_pct"]):
        ax.text(
            bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color=DARK_BLUE,
            fontweight="bold",
        )

    ax.set_xlabel("Relative Importance (% of Explained Variance)", fontsize=10, color=DARK_BLUE)
    ax.set_title(title, fontsize=13, fontweight="bold", color=DARK_BLUE, pad=12)
    ax.grid(axis="x", alpha=0.3, color=MID_GRAY, zorder=0)
    ax.set_xlim(0, df["importance_pct"].max() * 1.18)
    ax.tick_params(axis="y", labelsize=10)

    # Subtle rank numbers on left
    ax.set_yticks(range(n))
    ax.set_yticklabels(df["label"].tolist(), fontsize=10, color=DARK_BLUE)

    fig.tight_layout()
    return _fig_to_bytes(fig)


def chart_quadrant(quadrant_df: pd.DataFrame, title: str = "Priority Matrix") -> bytes:
    """2×2 quadrant scatter chart (Importance vs Performance)."""
    fig, ax = plt.subplots(figsize=(9, 7))
    _brand_fig(fig, ax)

    imp_mid = 0.5
    perf_mid = 0.5

    # Quadrant background shading
    ax.axvspan(0, perf_mid, ymin=0.5, ymax=1.0, alpha=0.04, color=ACCENT_ORANGE, zorder=0)   # Priority Fix
    ax.axvspan(perf_mid, 1, ymin=0.5, ymax=1.0, alpha=0.04, color=TEAL, zorder=0)             # Strengths
    ax.axvspan(0, perf_mid, ymin=0.0, ymax=0.5, alpha=0.04, color=MID_GRAY, zorder=0)         # Low Priority
    ax.axvspan(perf_mid, 1, ymin=0.0, ymax=0.5, alpha=0.04, color="#A8DADC", zorder=0)        # Nice-to-Have

    # Quadrant labels
    label_props = dict(fontsize=8, alpha=0.55, fontweight="bold")
    ax.text(0.02, 0.98, "PRIORITY FIXES", transform=ax.transAxes, va="top",
            color=ACCENT_ORANGE, **label_props)
    ax.text(0.52, 0.98, "STRENGTHS", transform=ax.transAxes, va="top",
            color=TEAL, **label_props)
    ax.text(0.02, 0.02, "LOW PRIORITY", transform=ax.transAxes, va="bottom",
            color=MID_GRAY, **label_props)
    ax.text(0.52, 0.02, "NICE-TO-HAVES", transform=ax.transAxes, va="bottom",
            color="#5ABFC0", **label_props)

    # Dividers
    ax.axhline(imp_mid, color=DARK_BLUE, linewidth=1, linestyle="--", alpha=0.25)
    ax.axvline(perf_mid, color=DARK_BLUE, linewidth=1, linestyle="--", alpha=0.25)

    # Points
    for _, row in quadrant_df.iterrows():
        color = QUADRANT_COLORS.get(row["quadrant"], MID_GRAY)
        ax.scatter(
            row["performance"], row["importance"],
            s=120, color=color, zorder=5, edgecolors=WHITE, linewidths=1.5,
        )
        # Label offset to avoid overlap
        x_off = 0.015 if row["performance"] < 0.85 else -0.015
        ha = "left" if row["performance"] < 0.85 else "right"
        ax.annotate(
            row["label"],
            xy=(row["performance"], row["importance"]),
            xytext=(row["performance"] + x_off, row["importance"] + 0.015),
            fontsize=8.5, color=DARK_BLUE, ha=ha,
            fontweight="medium",
        )

    ax.set_xlabel("Performance (Mean Score, Normalized)", fontsize=11, color=DARK_BLUE, labelpad=8)
    ax.set_ylabel("Relative Importance (Normalized)", fontsize=11, color=DARK_BLUE, labelpad=8)
    ax.set_title(title, fontsize=13, fontweight="bold", color=DARK_BLUE, pad=12)
    ax.set_xlim(-0.05, 1.1)
    ax.set_ylim(-0.05, 1.1)

    # Legend
    legend_handles = [
        mpatches.Patch(color=v, label=k)
        for k, v in QUADRANT_COLORS.items()
    ]
    ax.legend(
        handles=legend_handles,
        loc="lower right",
        fontsize=8,
        framealpha=0.8,
        edgecolor="#D0D5DD",
    )

    fig.tight_layout()
    return _fig_to_bytes(fig)


def chart_correlation_heatmap(pearson_df: pd.DataFrame, title: str = "Correlation with Outcome") -> bytes:
    """Horizontal bar chart of Pearson correlations."""
    df = pearson_df.sort_values("r", ascending=True)
    n = len(df)

    fig, ax = plt.subplots(figsize=(8, max(3.5, n * 0.5)))
    _brand_fig(fig, ax)

    colors = [TEAL if r >= 0 else ACCENT_ORANGE for r in df["r"]]
    ax.barh(
        df["predictor"].apply(lambda x: x.replace("_", " ").title()),
        df["r"],
        color=colors,
        height=0.6,
        zorder=3,
    )

    for i, (r, sig) in enumerate(zip(df["r"], df["significant"])):
        marker = "**" if sig else ""
        ax.text(
            r + (0.005 if r >= 0 else -0.005),
            i,
            f"{r:.3f}{marker}",
            va="center",
            ha="left" if r >= 0 else "right",
            fontsize=9,
            color=DARK_BLUE,
        )

    ax.axvline(0, color=DARK_BLUE, linewidth=0.8)
    ax.set_xlabel("Pearson r  (** p<0.05)", fontsize=10, color=DARK_BLUE)
    ax.set_title(title, fontsize=13, fontweight="bold", color=DARK_BLUE, pad=12)
    ax.grid(axis="x", alpha=0.3, zorder=0)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def chart_model_fit(r_squared: float, adj_r_squared: float) -> bytes:
    """Simple gauge-style model fit visualization."""
    fig, axes = plt.subplots(1, 2, figsize=(7, 3.5))
    _brand_fig(fig, axes)

    for ax, value, label in zip(
        axes,
        [r_squared, adj_r_squared],
        ["R² (Model Fit)", "Adj. R²"],
    ):
        # Arc gauge
        theta = np.linspace(np.pi, 0, 200)
        ax.plot(np.cos(theta), np.sin(theta), color=LIGHT_GRAY, linewidth=12, solid_capstyle="round")

        fill_theta = np.linspace(np.pi, np.pi - value * np.pi, 200)
        ax.plot(np.cos(fill_theta), np.sin(fill_theta), color=TEAL, linewidth=12, solid_capstyle="round")

        ax.text(0, 0.15, f"{value:.1%}", ha="center", va="center",
                fontsize=20, fontweight="bold", color=DARK_BLUE)
        ax.text(0, -0.15, label, ha="center", va="center",
                fontsize=10, color=MID_GRAY)

        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-0.4, 1.2)
        ax.set_aspect("equal")
        ax.axis("off")

    fig.suptitle("Model Fit Summary", fontsize=13, fontweight="bold", color=DARK_BLUE, y=1.02)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def chart_driver_detail(predictor: str, results) -> bytes:
    """Mini dashboard for a single driver: importance rank + performance."""
    row = results.importance.ranking[results.importance.ranking["predictor"] == predictor].iloc[0]
    qrow = results.quadrants.quadrant_df[results.quadrants.quadrant_df["predictor"] == predictor].iloc[0]
    rrow = results.regression.coefficients[results.regression.coefficients["predictor"] == predictor].iloc[0]
    crow = results.correlations.pearson[results.correlations.pearson["predictor"] == predictor].iloc[0]

    fig, axes = plt.subplots(1, 3, figsize=(10, 2.8))
    _brand_fig(fig, axes)

    metrics = [
        ("Relative\nImportance", f"{row['importance_pct']:.1f}%", TEAL),
        ("Pearson r", f"{crow['r']:.3f}", DARK_BLUE),
        ("Std. β", f"{rrow['std_coef']:.3f}", ACCENT_ORANGE if rrow['std_coef'] >= 0 else ACCENT_ORANGE),
    ]

    for ax, (label, value, color) in zip(axes, metrics):
        ax.text(0.5, 0.6, value, ha="center", va="center",
                fontsize=22, fontweight="bold", color=color,
                transform=ax.transAxes)
        ax.text(0.5, 0.2, label, ha="center", va="center",
                fontsize=9, color=MID_GRAY, transform=ax.transAxes)
        ax.set_facecolor(LIGHT_GRAY)
        ax.axis("off")
        for spine in ax.spines.values():
            spine.set_visible(False)

    qcolor = QUADRANT_COLORS.get(qrow["quadrant"], MID_GRAY)
    fig.suptitle(
        f"{row['label']}  ·  {qrow['quadrant']}",
        fontsize=12, fontweight="bold", color=DARK_BLUE, y=1.05,
    )
    fig.patch.set_facecolor(WHITE)
    fig.tight_layout()
    return _fig_to_bytes(fig)
