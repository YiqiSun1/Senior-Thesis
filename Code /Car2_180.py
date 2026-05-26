print("Runnnnnnnning")

import pandas as pd
import numpy as np

# ─── LOAD DATA ───
master = pd.read_csv('Data/master_final.csv')
crsp   = pd.read_csv('Data/crsp_daily.csv', dtype={'RET': str, 'vwretd': str})

# ─── PREP CRSP ───
crsp['date']   = pd.to_datetime(crsp['date'])
crsp['RET']    = pd.to_numeric(crsp['RET'],    errors='coerce')
crsp['vwretd'] = pd.to_numeric(crsp['vwretd'], errors='coerce')
crsp['ar']     = crsp['RET'] - crsp['vwretd']

master['call_date'] = pd.to_datetime(master['call_date'])

def compound_return(series):
    clean = series.dropna()
    if len(clean) == 0:
        return np.nan
    return (1 + clean).prod() - 1

# ─── COMPUTE CAR(2,180) ───
results = []

for idx, row in master.iterrows():
    symbol    = row['symbol']
    call_date = row['call_date']
    
    firm = crsp[crsp['TICKER'] == symbol].sort_values('date').reset_index(drop=True)

    if firm.empty:
        results.append({'symbol': symbol, 'call_date': call_date, 'car_2180': np.nan})
        continue

    # Find day 0
    day0_candidates = firm[firm['date'] >= call_date]
    if day0_candidates.empty:
        results.append({'symbol': symbol, 'call_date': call_date, 'car_2180': np.nan})
        continue

    day0_idx = day0_candidates.index[0]
    day0     = firm.loc[day0_idx, 'date']

    # Find day 2 — second trading day after day 0
    after_day0 = firm[firm['date'] > day0].reset_index(drop=True)
    if len(after_day0) < 2:
        results.append({'symbol': symbol, 'call_date': call_date, 'car_2180': np.nan})
        continue   

    day2 = after_day0.iloc[1]['date']
    # Find day 180 — 179 trading days after day 2
    after_day2 = firm[firm['date'] >= day2].reset_index(drop=True)

    if len(after_day2) >= 179:
        day180 = after_day2.iloc[178]['date']
    else: # if there are fewer than 179 trading days after day 2, use the last available trading day
        day180 = after_day2.iloc[-1]['date'] if not after_day2.empty else None

    if day180 is None:
        results.append({'symbol': symbol, 'call_date': call_date, 'car_2180': np.nan})
        continue

    # Get window
    window = firm[(firm['date'] >= day2) & (firm['date'] <= day180)]

    if window.empty:
        results.append({'symbol': symbol, 'call_date': call_date, 'car_2180': np.nan})
        continue

    # Compound stock return and market return separately
    stock_compound  = compound_return(window['RET'])
    market_compound = compound_return(window['vwretd'])

    # CAR = compounded stock return - compounded market return
    car_2180 = stock_compound - market_compound

    results.append({
        'symbol':    symbol,
        'call_date': call_date,
        'car_2180':  car_2180
    })

    if idx % 500 == 0:
        print(f"Progress: {idx}/{len(master)} | done: {len(results)}")

# ─── MERGE AND SAVE ───
car_df = pd.DataFrame(results)
master = master.merge(car_df, on=['symbol', 'call_date'], how='left')

print(f"\nMissing car_2180: {master['car_2180'].isna().sum()}")
print(f"\nCAR(2,180) summary:")
print(master['car_2180'].describe())
master.to_csv('Data/master_final_car2180.csv',      index=False)
print("\n✅ Saved")