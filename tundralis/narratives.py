"""AI narrative generation via OpenAI API (optional)."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _build_stats_summary(results) -> str:
    """Build a compact text summary of KDA results for the AI prompt."""
    r = results

    top_drivers = r.importance.ranking.head(5)
    driver_lines = "\n".join(
        f"  {i+1}. {row['predictor'].replace('_', ' ').title()} — "
        f"{row['importance_pct']:.1f}% of explained variance"
        for i, row in top_drivers.iterrows()
    )

    quadrant_lines = "\n".join(
        f"  - {row['label']}: {row['quadrant']}"
        for _, row in r.quadrants.quadrant_df.iterrows()
    )

    sig_predictors = r.regression.coefficients[r.regression.coefficients["significant"]]
    sig_lines = ", ".join(
        f"{row['predictor'].replace('_',' ').title()} (β={row['std_coef']:.2f})"
        for _, row in sig_predictors.iterrows()
    )

    return f"""
Key Driver Analysis Results for: {r.target.replace('_', ' ').title()}
Sample size: {r.n_obs} respondents
Model R² = {r.meta['r_squared']:.3f} (adj. R² = {r.meta['adj_r_squared']:.3f})

Top drivers by relative importance (Shapley):
{driver_lines}

Regression significance (statistically significant predictors):
{sig_lines if sig_lines else 'None at p<0.05'}

Priority quadrant mapping:
{quadrant_lines}
""".strip()


def _call_openai(prompt: str, model: str = "gpt-4o", max_tokens: int = 600) -> str:
    """Make a single OpenAI API call and return the text response."""
    try:
        import openai
    except ImportError:
        logger.warning("openai package not installed. Skipping narrative.")
        return ""

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set. Skipping narrative.")
        return ""

    client = openai.OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert market research analyst at a top consulting firm. "
                        "Write clear, concise, executive-ready insights from survey analysis results. "
                        "Use professional but accessible language. Be specific and actionable. "
                        "Avoid jargon. Write in third person."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("OpenAI API call failed: %s", e)
        return ""


def generate_executive_summary(results, model: str = "gpt-4o") -> str:
    """Generate a 3–5 sentence executive summary."""
    stats = _build_stats_summary(results)
    prompt = f"""
Based on the following Key Driver Analysis results, write a 3–5 sentence executive summary 
suitable for a C-suite audience. Focus on the most important findings and their business implications.

{stats}

Executive Summary:
"""
    text = _call_openai(prompt, model=model, max_tokens=300)
    if not text:
        # Fallback: template-based summary
        top = results.importance.ranking.iloc[0]
        text = (
            f"Analysis of {results.n_obs} survey responses reveals that "
            f"{top['predictor'].replace('_',' ').title()} is the strongest driver of "
            f"{results.target.replace('_',' ').title()}, accounting for "
            f"{top['importance_pct']:.1f}% of explained variance. "
            f"The overall model explains {results.meta['r_squared']*100:.1f}% of variance in the outcome. "
            "Priority should be given to improving drivers that score high on importance but low on performance."
        )
    return text


def generate_recommendations(results, model: str = "gpt-4o") -> list[str]:
    """Generate 4–6 actionable recommendations."""
    stats = _build_stats_summary(results)

    # Identify priority fixes
    pf = results.quadrants.quadrant_df[
        results.quadrants.quadrant_df["quadrant"] == "Priority Fixes"
    ]["label"].tolist()
    strengths = results.quadrants.quadrant_df[
        results.quadrants.quadrant_df["quadrant"] == "Strengths"
    ]["label"].tolist()

    prompt = f"""
Based on this Key Driver Analysis, write 4–6 specific, actionable recommendations.
Each recommendation should be 1–2 sentences. Format as a JSON array of strings.

Priority Fix areas (high importance, underperforming): {', '.join(pf) if pf else 'None identified'}
Strength areas (high importance, strong performance): {', '.join(strengths) if strengths else 'None identified'}

Full analysis:
{stats}

Respond ONLY with a JSON array like: ["Recommendation 1.", "Recommendation 2.", ...]
"""
    text = _call_openai(prompt, model=model, max_tokens=500)
    if text:
        try:
            # Strip markdown code fences if present
            clean = text.strip()
            if clean.startswith("```"):
                clean = "\n".join(clean.split("\n")[1:])
                clean = clean.rstrip("`").strip()
            recs = json.loads(clean)
            if isinstance(recs, list) and recs:
                return [str(r) for r in recs]
        except (json.JSONDecodeError, ValueError):
            # Try to extract lines
            lines = [l.strip().lstrip("•-0123456789. ") for l in text.split("\n") if l.strip()]
            if lines:
                return lines[:6]

    # Fallback recommendations
    recs = []
    pf_df = results.quadrants.quadrant_df[results.quadrants.quadrant_df["quadrant"] == "Priority Fixes"]
    for _, row in pf_df.iterrows():
        recs.append(
            f"Prioritize improving {row['label']}: this driver has high impact on satisfaction "
            "but is currently underperforming relative to other dimensions."
        )

    strengths_df = results.quadrants.quadrant_df[results.quadrants.quadrant_df["quadrant"] == "Strengths"]
    for _, row in strengths_df.iterrows():
        recs.append(
            f"Protect and promote {row['label']} as a competitive differentiator — "
            "customers value it highly and current performance is strong."
        )

    if not recs:
        top_driver = results.importance.ranking.iloc[0]["label"]
        recs.append(
            f"Focus investment on {top_driver}, the highest-impact driver of overall satisfaction."
        )

    return recs[:6]


def generate_driver_insight(predictor: str, results, model: str = "gpt-4o") -> str:
    """Generate a 2–3 sentence insight for a specific driver."""
    row = results.importance.ranking[
        results.importance.ranking["predictor"] == predictor
    ].iloc[0]

    corr_row = results.correlations.pearson[
        results.correlations.pearson["predictor"] == predictor
    ].iloc[0]

    reg_row = results.regression.coefficients[
        results.regression.coefficients["predictor"] == predictor
    ].iloc[0]

    quadrant_row = results.quadrants.quadrant_df[
        results.quadrants.quadrant_df["predictor"] == predictor
    ].iloc[0]

    prompt = f"""
Write a 2–3 sentence insight for the following survey driver in a Key Driver Analysis report:

Driver: {row['label']}
Relative Importance: {row['importance_pct']:.1f}% of explained variance (rank #{row['rank']} of {len(results.predictors)})
Pearson correlation with outcome: r = {corr_row['r']:.3f} (p = {corr_row['p_value']:.3f})
Standardized regression coefficient: β = {reg_row['std_coef']:.3f}
Quadrant: {quadrant_row['quadrant']}
Performance score (mean): {quadrant_row['performance_raw']:.2f}

Keep it professional, specific, and actionable. Do not use the word "driver" excessively.
"""
    text = _call_openai(prompt, model=model, max_tokens=200)
    if not text:
        sig = "significantly" if reg_row["significant"] else "marginally"
        text = (
            f"{row['label']} ranks #{row['rank']} in relative importance, "
            f"accounting for {row['importance_pct']:.1f}% of explained variance. "
            f"It is {sig} associated with overall satisfaction (β={reg_row['std_coef']:.2f}, "
            f"r={corr_row['r']:.2f}). "
            f"This dimension falls in the '{quadrant_row['quadrant']}' quadrant, "
            f"suggesting {'targeted improvement is needed' if quadrant_row['quadrant'] == 'Priority Fixes' else 'current strategy should be maintained'}."
        )
    return text


class NarrativeEngine:
    """Orchestrates all narrative generation."""

    def __init__(self, model: str = "gpt-4o", enabled: bool = True):
        self.model = model
        self.enabled = enabled and bool(os.environ.get("OPENAI_API_KEY"))
        if not self.enabled:
            logger.info("Narrative generation disabled (no OPENAI_API_KEY or explicitly off).")

    def executive_summary(self, results) -> str:
        if not self.enabled:
            return self._fallback_summary(results)
        return generate_executive_summary(results, model=self.model)

    def recommendations(self, results) -> list[str]:
        if not self.enabled:
            return self._fallback_recommendations(results)
        return generate_recommendations(results, model=self.model)

    def driver_insight(self, predictor: str, results) -> str:
        if not self.enabled:
            return self._fallback_driver_insight(predictor, results)
        return generate_driver_insight(predictor, results, model=self.model)

    # ── Fallbacks ─────────────────────────────────────────────────────────────

    @staticmethod
    def _fallback_summary(results) -> str:
        top = results.importance.ranking.iloc[0]
        n_sig = results.regression.coefficients["significant"].sum()
        return (
            f"This analysis examined {results.n_obs} survey respondents across "
            f"{len(results.predictors)} experience dimensions. "
            f"The model explains {results.meta['r_squared']*100:.1f}% of variance in "
            f"{results.target.replace('_', ' ').title()} (adj. R²={results.meta['adj_r_squared']:.3f}). "
            f"{top['predictor'].replace('_',' ').title()} emerges as the top driver, "
            f"contributing {top['importance_pct']:.1f}% of explained variance. "
            f"{n_sig} of {len(results.predictors)} predictors reach statistical significance (p<0.05). "
            "Immediate attention should be directed toward high-importance, underperforming dimensions."
        )

    @staticmethod
    def _fallback_recommendations(results) -> list[str]:
        recs = []
        pf = results.quadrants.quadrant_df[results.quadrants.quadrant_df["quadrant"] == "Priority Fixes"]
        for _, row in pf.iterrows():
            recs.append(
                f"Improve {row['label']}: high impact on overall satisfaction but currently underperforming."
            )
        strengths = results.quadrants.quadrant_df[results.quadrants.quadrant_df["quadrant"] == "Strengths"]
        for _, row in strengths.iterrows():
            recs.append(
                f"Sustain {row['label']}: a proven strength with high importance — protect this advantage."
            )
        if len(recs) < 3:
            top3 = results.importance.ranking.head(3)
            for _, row in top3.iterrows():
                label = row["label"]
                if not any(label in r for r in recs):
                    recs.append(f"Monitor {label} closely — it is among the top drivers of satisfaction.")
        return recs[:6]

    @staticmethod
    def _fallback_driver_insight(predictor: str, results) -> str:
        row = results.importance.ranking[results.importance.ranking["predictor"] == predictor].iloc[0]
        qrow = results.quadrants.quadrant_df[results.quadrants.quadrant_df["predictor"] == predictor].iloc[0]
        rrow = results.regression.coefficients[results.regression.coefficients["predictor"] == predictor].iloc[0]
        sig_txt = "a statistically significant" if rrow["significant"] else "a non-significant"
        return (
            f"{row['label']} is the #{row['rank']} driver of overall satisfaction, "
            f"explaining {row['importance_pct']:.1f}% of variance. "
            f"It shows {sig_txt} relationship with the outcome (β={rrow['std_coef']:.2f}). "
            f"Classified as '{qrow['quadrant']}', this dimension "
            f"{'warrants priority investment' if qrow['quadrant'] == 'Priority Fixes' else 'should be monitored and maintained'}."
        )
