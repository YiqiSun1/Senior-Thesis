import pandas as pd

# ─── LOAD ───
new_car_1 = pd.read_csv('Data/new_CAR_1.csv')
new_car_2180  = pd.read_csv('Data/new_CAR_01_280.csv')
master    = pd.read_csv('Data/master_final.csv')

new_car_1['call_date']    = pd.to_datetime(new_car_1['call_date'])
new_car_2180['call_date'] = pd.to_datetime(new_car_2180['call_date'])
master['call_date']       = pd.to_datetime(master['call_date'])

fundamental_cols = ['symbol', 'call_date', 'vol', 'mom', 'POSWORDS', 'NEGWORDS', 'lnmve', 'bm', 'atq', 'UE', 'actual_eps', 'median_forecast', 'numest']

master_subset = master[fundamental_cols].drop_duplicates(
    subset=['symbol', 'call_date']
)

# ─── MERGE INTO SHORT RUN ───
short_final = new_car_1.merge(
    master_subset,
    on=['symbol', 'call_date'],
    how='left'
)

print(f"Short run: {new_car_1.shape} → {short_final.shape}")
print(f"Missing UE:    {short_final['UE'].isna().sum()}")
print(f"Missing lnmve: {short_final['lnmve'].isna().sum()}")

# ─── MERGE INTO LONG RUN ───
long_final = new_car_2180.merge(
    master_subset,
    on=['symbol', 'call_date'],
    how='left'
)

print(f"\nLong run: {new_car_2180.shape} → {long_final.shape}")
print(f"Missing UE:    {long_final['UE'].isna().sum()}")
print(f"Missing lnmve: {long_final['lnmve'].isna().sum()}")

# ─── SAVE ───
short_final.to_csv('Data/new_car_1_with_fundamental.csv',         index=False)
long_final.to_csv('Data/new_car_2180_with_fundamental.csv',         index=False)

print("\n✅ Saved short_final and long_final")