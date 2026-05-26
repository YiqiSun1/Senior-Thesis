import pandas as pd
import numpy as np

# ─── LOAD ───
pivoted = pd.read_csv('data_testing_storage/pivoted_stress_scores.csv')
crsp    = pd.read_csv('Data/crsp_daily.csv', dtype={'RET': str, 'vwretd': str})

crsp['date']   = pd.to_datetime(crsp['date'])
crsp['RET']    = pd.to_numeric(crsp['RET'],    errors='coerce')
crsp['vwretd'] = pd.to_numeric(crsp['vwretd'], errors='coerce')
pivoted['call_date'] = pd.to_datetime(pivoted['call_date'])

def compound_return(series):
    clean = series.dropna()
    if len(clean) == 0:
        return np.nan
    return (1 + clean).prod() - 1

# ─── COMPUTE CAR(0,1) AND CAR(2,180) ───
results  = []
dropped  = 0

for idx, row in pivoted.iterrows():
    symbol    = row['symbol']
    call_date = row['call_date']

    firm = crsp[crsp['TICKER'] == symbol].sort_values('date').reset_index(drop=True)

    if firm.empty:
        dropped += 1
        continue

    # Find day 0
    day0_candidates = firm[firm['date'] >= call_date]
    if day0_candidates.empty:
        dropped += 1
        continue

    day0_idx = day0_candidates.index[0]
    day0     = firm.loc[day0_idx, 'date']

    after_day0 = firm[firm['date'] > day0].reset_index(drop=True)

    # ── Strict 180 day requirement ──
    # Need at least 180 trading days after day 0
    if len(after_day0) < 180:
        dropped += 1
        continue

    # ── CAR(0,1) ──
    day1      = after_day0.iloc[0]['date']
    window_01 = firm[(firm['date'] >= day0) & (firm['date'] <= day1)]
    car_01    = compound_return(window_01['RET']) - compound_return(window_01['vwretd'])

    # ── CAR(2,180) ──
    # Day 2 = second trading day after day 0
    day2       = after_day0.iloc[1]['date']
    day180     = after_day0.iloc[179]['date']
    window_2180 = firm[(firm['date'] >= day2) & (firm['date'] <= day180)]

    # Strict — must have exactly 179 trading days in window
    if len(window_2180) < 170:  # allow small gaps
        dropped += 1
        continue

    car_2180 = compound_return(window_2180['RET']) - compound_return(window_2180['vwretd'])

    results.append({
        'symbol':       symbol,
        'year':         row['year'],
        'quarter':      row['quarter'],
        'call_date':    call_date,
        'stress_pr':    row['stress_pr'],
        'stress_qa':    row['stress_qa'],
        'stress_whole': row['stress_whole'],
        'car_01':       car_01,
        'car_2180':     car_2180,
    })

    if idx % 500 == 0:
        print(f"Progress: {idx}/{len(pivoted)} | kept: {len(results)} | dropped: {dropped}")

df_long = pd.DataFrame(results)
print(f"\nLong run dataset: {df_long.shape}")
print(f"Dropped (insufficient history): {dropped}")
print(f"Missing car_01:   {df_long['car_01'].isna().sum()}")
print(f"Missing car_2180: {df_long['car_2180'].isna().sum()}")


df_long.to_csv('Data/new_CAR_01_280.csv', index=False)
print("✅ Saved new_CAR_01_280")