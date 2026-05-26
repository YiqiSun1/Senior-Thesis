import pyfixest as pf
import pandas as pd

# ─── LOAD ───
df = pd.read_csv('./Data/new_car_2180_with_fundamental.csv')
df['call_date'] = pd.to_datetime(df['call_date'])
df['time'] = df['year'] * 10 + df['quarter']
print(f"Original data: {len(df)} obs | {df['symbol'].nunique()} firms")

# ─── WINSORIZE ───
def winsorize(series, lower=0.01, upper=0.99):
    low  = series.quantile(lower)
    high = series.quantile(upper)
    return series.clip(lower=low, upper=high)

# part 1, using only stress_qa to maximize sample size
# for col in ['car_2180', 'vol', 'mom', 'lnmve', 'bm', 'UE', 'POSWORDS', 'NEGWORDS']:
#     df[col] = winsorize(df[col])

# # ─── DROP MISSING ───
# reg_vars = ['car_2180', 'stress_qa', 'vol', 'mom',
#             'lnmve', 'bm', 'UE', 'POSWORDS', 'NEGWORDS']

# # drop rows where there are n/a for any columns above
# df = df.dropna(subset=reg_vars).copy()
# print(f"after dropping N/A: {len(df)} obs | {df['symbol'].nunique()} firms")

# # dropping singleton
# # Find firms appearing more than once
# # FIXED — chain the filters
# firm_counts = df['symbol'].value_counts()
# df_clean = df[
#     df['symbol'].isin(firm_counts[firm_counts > 1].index)
# ].copy()

# time_counts = df_clean['time'].value_counts()  # ← filter from df_clean not df
# df_clean = df_clean[
#     df_clean['time'].isin(time_counts[time_counts > 1].index)
# ].copy()

# print(f"Final sample: {len(df_clean)}")
# # ─── RUN MODELS ───

# # Model 1 — No FE, two-way clustered SE
# m1 = pf.feols(
#     'car_2180 ~ stress_qa + vol + mom + lnmve + bm + UE + POSWORDS + NEGWORDS',
#     data=df_clean,
#     vcov={'CRV1': 'symbol + time'}
# )
# print(f"model 1 cluster no FE result {m1.summary()}")   

# # Model 2 — Firm FE only
# m2 = pf.feols(
#     'car_2180 ~ stress_qa + vol + mom + lnmve + bm + UE + POSWORDS + NEGWORDS | symbol',
#     data=df_clean,
#     vcov={'CRV1': 'symbol + time'}
# )
# print(f"model 2 firm FE result {m2.summary()}")

# # Model 3 — Time FE only
# m3 = pf.feols(
#     'car_2180 ~ stress_qa + vol + mom + lnmve + bm + UE + POSWORDS + NEGWORDS | time',
#     data=df_clean,
#     vcov={'CRV1': 'symbol + time'}
# )
# print(f"model 3 time FE result {m3.summary()}")
# # Model 4 — Firm + Time FE
# m4 = pf.feols(
#     'car_2180 ~ stress_qa + vol + mom + lnmve + bm + UE + POSWORDS + NEGWORDS | symbol + time',
#     data=df_clean,
#     vcov={'CRV1': 'symbol + time'}
# )
# print(f"model 4 firm + time FE result {m4.summary()}")



# part 2: using stress_pr and stress_qa, comparing significance.

for col in ['car_2180', 'vol', 'mom', 'lnmve', 'bm', 'UE', 'POSWORDS', 'NEGWORDS']:
    df[col] = winsorize(df[col])

# ─── DROP MISSING ───
reg_vars = ['car_2180', 'stress_qa', 'stress_pr', 'vol', 'mom',
            'lnmve', 'bm', 'UE', 'POSWORDS', 'NEGWORDS']

# drop rows where there are n/a for any columns above
df = df.dropna(subset=reg_vars).copy()
print(f"after dropping N/A: {len(df)} obs | {df['symbol'].nunique()} firms")

# dropping singleton
# Find firms appearing more than once
# FIXED — chain the filters
firm_counts = df['symbol'].value_counts()
df_clean = df[
    df['symbol'].isin(firm_counts[firm_counts > 1].index)
].copy()

time_counts = df_clean['time'].value_counts()  # ← filter from df_clean not df
df_clean = df_clean[
    df_clean['time'].isin(time_counts[time_counts > 1].index)
].copy()

print(f"Final sample: {len(df_clean)}")
# ─── RUN MODELS ───

# Model 1 — No FE, two-way clustered SE
m1 = pf.feols(
    'car_2180 ~ stress_qa + stress_pr + vol + mom + lnmve + bm + UE + POSWORDS + NEGWORDS',
    data=df_clean,
    vcov={'CRV1': 'symbol + time'}
)
print(f"model 1 cluster no FE result {m1.summary()}")   

# Model 2 — Firm FE only
m2 = pf.feols(
    'car_2180 ~ stress_qa + stress_pr + vol + mom + lnmve + bm + UE + POSWORDS + NEGWORDS | symbol',
    data=df_clean,
    vcov={'CRV1': 'symbol + time'}
)
print(f"model 2 firm FE result {m2.summary()}")

# Model 3 — Time FE only
m3 = pf.feols(
    'car_2180 ~ stress_qa + stress_pr + vol + mom + lnmve + bm + UE + POSWORDS + NEGWORDS | time',
    data=df_clean,
    vcov={'CRV1': 'symbol + time'}
)
print(f"model 3 time FE result {m3.summary()}")
# Model 4 — Firm + Time FE
m4 = pf.feols(
    'car_2180 ~ stress_qa + stress_pr + vol + mom + lnmve + bm + UE + POSWORDS + NEGWORDS | symbol + time',
    data=df_clean,
    vcov={'CRV1': 'symbol + time'}
)
print(f"model 4 firm + time FE result {m4.summary()}")

