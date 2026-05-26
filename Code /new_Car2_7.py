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

# ─── COMPUTE CAR(0,1), VOL, MOM ───
results = []
dropped = 0
for idx, row in pivoted.iterrows():
    symbol    = row['symbol']
    call_date = row['call_date']

    firm = crsp[crsp['TICKER'] == symbol].sort_values('date').reset_index(drop=True)

    if firm.empty:
        continue

    # Find day 0
    day0_candidates = firm[firm['date'] >= call_date]
    if day0_candidates.empty:
        continue

    day0_idx = day0_candidates.index[0]
    day0     = firm.loc[day0_idx, 'date']

    # ── CAR(0,1) ──
    after_day0  = firm[firm['date'] > day0].reset_index(drop=True)
    day2 = after_day0.iloc[1]['date']   # second trading day after day 0
    day7 = after_day0.iloc[6]['date']   # seventh trading day after day 0

    window_27 = firm[(firm['date'] >= day2) & (firm['date'] <= day7)]

    if len(window_27) < 6:  # should have ~6 trading days
        dropped += 1
        continue

    stock_27  = compound_return(window_27['RET'])
    market_27 = compound_return(window_27['vwretd'])
    car_27    = stock_27 - market_27

    results.append({
        'symbol':       symbol,
        'year':         row['year'],
        'quarter':      row['quarter'],
        'call_date':    call_date,
        'stress_pr':    row['stress_pr'],
        'stress_qa':    row['stress_qa'],
        'stress_whole': row['stress_whole'],
        'car_27':       car_27,
    })
    
    # day7       = after_day0.iloc[6]['date']
    # window_07   = firm[(firm['date'] >= day0) & (firm['date'] <= day7)]
    # if len(window_07) < 7: 
    #     dropped += 1
    #     continue
    # stock_07    = compound_return(window_07['RET'])
    # market_07   = compound_return(window_07['vwretd'])
    # car_07      = stock_07 - market_07

    # results.append({
    #     'symbol':       symbol,
    #     'year':         row['year'],
    #     'quarter':      row['quarter'],
    #     'call_date':    call_date,
    #     'stress_pr':    row['stress_pr'],
    #     'stress_qa':    row['stress_qa'],
    #     'stress_whole': row['stress_whole'],
    #     'car_07':       car_07,
    # })

    # if idx == 10:
    #     print(f"result: {results}")
    #     df_short = pd.DataFrame(results)
    #     print(df_short.columns)
    #     print(df_short['car_07'].isna().sum())
    #     break
    
    if idx % 500 == 0:
        print(f"Progress: {idx}/{len(pivoted)} | done: {len(results)}")

df_short = pd.DataFrame(results)
print(f"\nShort run dataset: {df_short.shape}")
print(f"Missing car_27: {df_short['car_27'].isna().sum()}")

df_short.to_csv('Data/new_CAR_27.csv', index=False)
print("✅ Saved new_CAR_27")
