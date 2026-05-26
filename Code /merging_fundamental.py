print("runnninnnnng")
import pandas as pd
import numpy as np
from datetime import timedelta

# ─── LOAD ALL DATA ───
master       = pd.read_csv('Data/master.csv')
compustat    = pd.read_csv('Data/fundamental .csv')
# ibes_actual  = pd.read_csv('Data/actual_EPS.csv')
# ibes_summary = pd.read_csv('Data/summarystatistics.csv')

# ─── PARSE DATES ───
master['call_date']         = pd.to_datetime(master['call_date'])
compustat['datadate']       = pd.to_datetime(compustat['datadate'])
# ibes_actual['ANNDATS']      = pd.to_datetime(ibes_actual['ANNDATS'])
# ibes_actual['PENDS']        = pd.to_datetime(ibes_actual['PENDS'])
# ibes_summary['STATPERS']    = pd.to_datetime(ibes_summary['STATPERS'])
# ibes_summary['FPEDATS']     = pd.to_datetime(ibes_summary['FPEDATS'])
# ibes_summary['ANNDATS_ACT'] = pd.to_datetime(ibes_summary['ANNDATS_ACT'])

# ─── MERGE 2 — COMPUSTAT ───
# Filter compustat

compustat = compustat[
    (compustat['costat'] == 'A') &
    (compustat['datafmt'] == 'STD') &
    (compustat['indfmt'] == 'INDL') &
    (compustat['consol'] == 'C')
].copy()

# Compute LNMVE and BM
compustat['mve']   = compustat['prccq'] * compustat['cshoq']
compustat['lnmve'] = np.log(compustat['mve'].replace(0, np.nan))
compustat['bm']    = compustat['ceqq'] / compustat['mve']

compustat = compustat[
    (compustat['ceqq'] > 0) &
    (compustat['mve']  > 0)
].copy()

compustat = compustat.sort_values(['tic', 'datadate'])

# Match using call_date — find most recent quarter before call
comp_results = []

for _, row in master.iterrows():
    symbol    = row['symbol']
    call_date = row['call_date']

    firm = compustat[compustat['tic'] == symbol]
    prior = firm[firm['datadate'] < call_date]

    if prior.empty:
        comp_results.append({
            'symbol': symbol, 'call_date': call_date,
            'lnmve': np.nan, 'bm': np.nan, 'atq': np.nan
        })
    else:
        latest = prior.iloc[-1]
        comp_results.append({
            'symbol':    symbol,
            'call_date': call_date,
            'lnmve':     latest['lnmve'],
            'bm':        latest['bm'],
            'atq':       latest['atq']
        })

comp_df = pd.DataFrame(comp_results)
master  = master.merge(comp_df, on=['symbol', 'call_date'], how='left')

print(f"\nAfter Compustat merge: {master.shape}")
print(f"Missing lnmve: {master['lnmve'].isna().sum()}")
print(f"Missing bm:    {master['bm'].isna().sum()}")