import pandas as pd
import numpy as np

# ─── LOAD DATA ───
crsp = pd.read_csv('Data/crsp_daily.csv', dtype={'RET': str, 'vwretd': str})
pivoted = pd.read_csv('data_testing_storage/pivoted_stress_scores.csv')
crsp['date']   = pd.to_datetime(crsp['date'])
crsp['RET']    = pd.to_numeric(crsp['RET'],    errors='coerce')
crsp['vwretd'] = pd.to_numeric(crsp['vwretd'], errors='coerce')
crsp['ar']     = crsp['RET'] - crsp['vwretd']

pivoted['call_date'] = pd.to_datetime(pivoted['call_date'])

print(f"CRSP shape:   {crsp.shape}")
print(f"Pivoted shape: {pivoted.shape}")

# ─── HELPER — compound returns ───
def compound_returns(series):
    """Compound a series of returns: (1+r1)*(1+r2)*...-1"""
    clean = series.dropna()
    if len(clean) == 0:
        return np.nan
    return (1 + clean).prod() - 1

# ─── MAIN LOOP ───
results  = []
no_match = []

for idx, call in pivoted.iterrows():
    symbol    = call['symbol']
    call_date = call['call_date']

    # Get firm trading data
    firm = crsp[crsp['TICKER'] == symbol].sort_values('date').reset_index(drop=True)

    if firm.empty:
        no_match.append(symbol)
        continue

    # ── Find day 0 — call date or next trading day ──
    day0_candidates = firm[firm['date'] >= call_date]
    if day0_candidates.empty:
        continue
    day0_idx = day0_candidates.index[0]
    day0     = firm.loc[day0_idx, 'date']

    # ── CAR(0,1) — day 0 and day +1 ──
    end_idx_01 = min(day0_idx + 1, len(firm) - 1)
    car_01     = compound_returns(firm.loc[day0_idx:end_idx_01, 'ar'])

    # ── CAR(0,180) — 180 trading days after call ──
    after_day0 = firm[firm['date'] > day0].reset_index(drop=True)
    if len(after_day0) >= 180:
        day180      = after_day0.iloc[179]['date']
        window_0180 = firm[(firm['date'] >= day0) & (firm['date'] <= day180)]
        car_0180    = compound_returns(window_0180['ar'])
    elif len(after_day0) > 0:
        # use whatever trading days are available
        window_0180 = firm[firm['date'] >= day0]
        car_0180    = compound_returns(window_0180['ar'])
    else:
        car_0180 = np.nan

    # ── VOL — std of daily returns, 125 trading days prior ──
    before_day0 = firm[firm['date'] < day0].reset_index(drop=True)
    if len(before_day0) >= 25:
        vol_window = before_day0.tail(125)
        vol        = vol_window['RET'].std()
    else:
        vol = np.nan

    # ── MOM — compounded abnormal return [-127, -2] ──
    # exclude day -1 to avoid pre-announcement leakage
    n = len(before_day0)
    if n >= 2:
        start_idx  = max(0, n - 127)
        end_idx    = n - 1          # exclude last row (day -1)
        mom_window = before_day0.iloc[start_idx:end_idx]
        mom        = compound_returns(mom_window['ar'])
    else:
        mom = np.nan

    results.append({
        'symbol':       symbol,
        'year':         call['year'],
        'quarter':      call['quarter'],
        'call_date':    call_date,
        'stress_pr':    call['stress_pr'],
        'stress_qa':    call['stress_qa'],
        'stress_whole': call['stress_whole'],
        'car_01':       car_01,
        'car_0180':     car_0180,
        'vol':          vol,
        'mom':          mom,
    })

    if idx % 500 == 0:
        print(f"Progress: {idx}/{len(pivoted)} | "
              f"Processed: {len(results)} | "
              f"No match: {len(no_match)}")

# ─── SAVE ───
results_df = pd.DataFrame(results)

print(f"\n{'='*40}")
print(f"Total calls processed: {len(results_df)}")
print(f"No CRSP match:         {len(set(no_match))}")
print(f"\nMissing values:")
print(results_df[['car_01','car_0180','vol','mom']].isna().sum())
print(f"\nSummary stats:")
print(results_df[['car_01','car_0180','vol','mom']].describe())

results_df.to_parquet('Data/master_data.parquet', index=False)
results_df.to_csv('Data/master_data.csv',     index=False)
print("\n✅ Saved to Data/master_data")
