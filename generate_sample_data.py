#!/usr/bin/env python3
"""Generate synthetic customer satisfaction survey data for testing."""

import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
N = 500

# ── Latent factors ─────────────────────────────────────────────────────────────
# Underlying true utilities on 0–1 scale before scaling to 1–7

product_quality_latent    = rng.beta(5, 2, N)       # Skew high (strength)
ease_of_use_latent        = rng.beta(4, 2, N)       # Pretty good
customer_support_latent   = rng.beta(2, 3, N)       # Skew low (priority fix)
price_value_latent        = rng.beta(3, 3, N)       # Average
onboarding_experience_latent = rng.beta(3, 2.5, N)  # Middling
reliability_latent        = rng.beta(4.5, 2, N)     # Good
mobile_app_latent         = rng.beta(2.5, 3, N)     # Below average
account_management_latent = rng.beta(3, 3.5, N)     # Slightly below average
reporting_analytics_latent = rng.beta(2, 3, N)      # Weak
integration_ease_latent   = rng.beta(3.5, 2.5, N)   # OK

def to_likert(x, lo=1, hi=7):
    """Scale 0–1 latent to Likert with some noise."""
    scaled = lo + x * (hi - lo)
    noisy = scaled + rng.normal(0, 0.35, len(x))
    return np.clip(np.round(noisy).astype(int), lo, hi)

product_quality     = to_likert(product_quality_latent)
ease_of_use         = to_likert(ease_of_use_latent)
customer_support    = to_likert(customer_support_latent)
price_value         = to_likert(price_value_latent)
onboarding          = to_likert(onboarding_experience_latent)
reliability         = to_likert(reliability_latent)
mobile_app          = to_likert(mobile_app_latent)
account_management  = to_likert(account_management_latent)
reporting_analytics = to_likert(reporting_analytics_latent)
integration_ease    = to_likert(integration_ease_latent)

# ── Outcome: overall_satisfaction ─────────────────────────────────────────────
# True DGP: weighted combination of drivers + noise
overall_satisfaction_raw = (
    0.30 * product_quality_latent      # Strongest driver
    + 0.20 * customer_support_latent   # Second — priority fix (low perf)
    + 0.15 * ease_of_use_latent
    + 0.10 * reliability_latent
    + 0.08 * price_value_latent
    + 0.07 * onboarding_experience_latent
    + 0.04 * mobile_app_latent
    + 0.03 * account_management_latent
    + 0.02 * reporting_analytics_latent
    + 0.01 * integration_ease_latent
    + rng.normal(0, 0.08, N)
)
overall_satisfaction = to_likert(
    np.clip((overall_satisfaction_raw - overall_satisfaction_raw.min()) /
            (overall_satisfaction_raw.max() - overall_satisfaction_raw.min()), 0, 1)
)

# ── Build DataFrame ────────────────────────────────────────────────────────────
df = pd.DataFrame({
    "respondent_id": range(1, N + 1),
    "overall_satisfaction": overall_satisfaction,
    "product_quality": product_quality,
    "ease_of_use": ease_of_use,
    "customer_support": customer_support,
    "price_value": price_value,
    "onboarding_experience": onboarding,
    "reliability": reliability,
    "mobile_app": mobile_app,
    "account_management": account_management,
    "reporting_analytics": reporting_analytics,
    "integration_ease": integration_ease,
})

# Add ~2% missing values to a couple of columns (realistic)
for col in ["mobile_app", "reporting_analytics"]:
    mask = rng.random(N) < 0.02
    df.loc[mask, col] = np.nan

out = Path(__file__).parent / "data" / "sample_survey.csv"
out.parent.mkdir(exist_ok=True)
df.to_csv(out, index=False)
print(f"Generated {N} rows → {out}")
print(df.describe().round(2))
