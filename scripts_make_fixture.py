from pathlib import Path
import numpy as np
import pandas as pd

src = Path('/home/nick/.openclaw/workspace/tundralis/data/sample_survey.csv')
out = Path('/home/nick/.openclaw/workspace/tundralis/data/fixtures/client_style_kda.csv')

rng = np.random.default_rng(123)
df = pd.read_csv(src)

renamed = df.rename(columns={
    'respondent_id': 'response_id',
    'overall_satisfaction': 'overall_sat',
    'product_quality': 'product_quality_score',
    'ease_of_use': 'ease_use_score',
    'customer_support': 'support_experience',
    'price_value': 'value_for_money',
    'onboarding_experience': 'onboarding_score',
    'reliability': 'service_reliability',
    'mobile_app': 'mobile_app_score',
    'account_management': 'acct_mgmt_score',
    'reporting_analytics': 'reporting_tools',
    'integration_ease': 'integration_setup',
})
renamed['segment'] = rng.choice(['SMB', 'Mid-Market', 'Enterprise'], size=len(renamed), p=[0.45, 0.35, 0.20])
renamed['region'] = rng.choice(['North America', 'EMEA', 'APAC'], size=len(renamed), p=[0.6, 0.25, 0.15])
renamed['survey_wave'] = '2026-Q1'
renamed['free_text_comment'] = rng.choice(['', 'good', 'slow onboarding', 'love support', 'pricing concerns'], size=len(renamed))

# Add realistic sparse missingness across predictors and some DV missingness
predictor_cols = [
    'product_quality_score', 'ease_use_score', 'support_experience', 'value_for_money',
    'onboarding_score', 'service_reliability', 'mobile_app_score', 'acct_mgmt_score',
    'reporting_tools', 'integration_setup'
]
for col, rate in {
    'mobile_app_score': 0.12,
    'reporting_tools': 0.10,
    'acct_mgmt_score': 0.08,
    'integration_setup': 0.06,
    'support_experience': 0.05,
}.items():
    mask = rng.random(len(renamed)) < rate
    renamed.loc[mask, col] = np.nan

dv_mask = rng.random(len(renamed)) < 0.03
renamed.loc[dv_mask, 'overall_sat'] = np.nan

# ensure a few rows have only one predictor populated but valid DV
sample_rows = renamed.sample(8, random_state=7).index
for idx in sample_rows:
    keep = rng.choice(predictor_cols)
    for col in predictor_cols:
        if col != keep:
            renamed.loc[idx, col] = np.nan

out.parent.mkdir(parents=True, exist_ok=True)
renamed.to_csv(out, index=False)
print(out)
print(renamed.head())
