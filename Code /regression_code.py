print("Running regression code...")

import statsmodels.formula.api as smf
import pandas as pd
import numpy as np

# Load master data
master = pd.read_parquet('Data/master_final.parquet')

# ─── CLEAN FOR REGRESSION ───
# Winsorize at 1% and 99% to handle outliers
# def winsorize(series, lower=0.01, upper=0.99):
#     low  = series.quantile(lower)
#     high = series.quantile(upper)
#     return series.clip(lower=low, upper=high)

reg_df = master.copy()

# for col in ['car_01', 'car_0180', 'vol', 'mom', 
#             'lnmve', 'bm', 'UE', 'POSWORDS', 'NEGWORDS']:
#     reg_df[col] = winsorize(reg_df[col])

# ─── REGRESSION VARIABLES ───
controls = 'vol + mom + lnmve + bm + UE + POSWORDS + NEGWORDS'

# Drop rows missing any regression variable
reg_vars = ['car_01', 'stress_qa', 'stress_pr', 'stress_whole',
            'vol', 'mom', 'lnmve', 'bm', 'UE', 'POSWORDS', 'NEGWORDS']

reg_df = reg_df.dropna(subset=reg_vars).copy()
print(f"Regression sample: {len(reg_df)} observations")
print(f"Unique firms: {reg_df['symbol'].nunique()}")

# ─── MODEL 1 — QA STRESS → CAR(0,1) ───
m1 = smf.ols(
    f'car_01 ~ stress_qa + {controls}',
    data=reg_df
).fit(cov_type='HC3')

print("\n=== Model 1: QA Stress → CAR(0,1) ===")
print(m1.summary2().tables[1].round(4))

# ─── MODEL 2 — PR STRESS → CAR(0,1) ───
reg_df2 = reg_df.dropna(subset=['stress_pr'])
m2 = smf.ols(
    f'car_01 ~ stress_pr + {controls}',
    data=reg_df2
).fit(cov_type='HC3')

print("\n=== Model 2: PR Stress → CAR(0,1) ===")
print(m2.summary2().tables[1].round(4))

# ─── MODEL 3 — WHOLE TEXT STRESS → CAR(0,1) ───
m3 = smf.ols(
    f'car_01 ~ stress_whole + {controls}',
    data=reg_df
).fit(cov_type='HC3')

print("\n=== Model 3: Whole Text Stress → CAR(0,1) ===")
print(m3.summary2().tables[1].round(4))

# ─── MODEL 4 — QA STRESS → CAR(0,180) ───
m4 = smf.ols(
    f'car_0180 ~ stress_qa + {controls}',
    data=reg_df
).fit(cov_type='HC3')

print("\n=== Model 4: QA Stress → CAR(0,180) ===")
print(m4.summary2().tables[1].round(4))

# ─── MODEL 5 — ALL THREE STRESS SCORES TOGETHER ───
reg_df5 = reg_df.dropna(subset=['stress_pr'])
m5 = smf.ols(
    f'car_01 ~ stress_qa + stress_pr + stress_whole + {controls}',
    data=reg_df5
).fit(cov_type='HC3')

print("\n=== Model 5: All Stress Scores → CAR(0,1) ===")
print(m5.summary2().tables[1].round(4))

# ─── SUMMARY TABLE ───
print("\n=== SUMMARY ===")
print(f"{'Model':<10} {'N':>6} {'R²':>8} {'stress coef':>12} {'p-value':>10}")
print("-" * 50)
for label, model, n in [
    ('M1 QA→01',    m1, len(reg_df)),
    ('M2 PR→01',    m2, len(reg_df2)),
    ('M3 Whole→01', m3, len(reg_df)),
    ('M4 QA→180',   m4, len(reg_df)),
]:
    stress_var = [v for v in model.params.index 
                  if 'stress' in v][0]
    coef  = model.params[stress_var]
    pval  = model.pvalues[stress_var]
    r2    = model.rsquared
    print(f"{label:<10} {n:>6} {r2:>8.4f} {coef:>12.4f} {pval:>10.4f}")