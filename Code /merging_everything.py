print("runnninnnnng")
import pandas as pd
import numpy as np
from datetime import timedelta

# ─── LOAD ALL DATA ───
master       = pd.read_csv('Data/master.csv')
compustat    = pd.read_csv('Data/fundamental .csv')
ibes_actual  = pd.read_csv('Data/actual_EPS.csv')
ibes_summary = pd.read_csv('Data/summarystatistics.csv')



# ─── PARSE DATES ───
master['call_date']         = pd.to_datetime(master['call_date'])
compustat['datadate']       = pd.to_datetime(compustat['datadate'])
ibes_actual['ANNDATS']      = pd.to_datetime(ibes_actual['ANNDATS'])
ibes_actual['PENDS']        = pd.to_datetime(ibes_actual['PENDS'])
ibes_summary['STATPERS']    = pd.to_datetime(ibes_summary['STATPERS'])
ibes_summary['FPEDATS']     = pd.to_datetime(ibes_summary['FPEDATS'])
ibes_summary['ANNDATS_ACT'] = pd.to_datetime(ibes_summary['ANNDATS_ACT'])

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
    (compustat['m'] > 0) &
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

# IBES merge below 
# ─── FILTER ───
ibes_actual = ibes_actual[
    (ibes_actual['USFIRM']  == 1) &
    (ibes_actual['MEASURE'] == 'EPS') &
    (ibes_actual['PDICITY'] == 'QTR')
].copy()

ibes_summary = ibes_summary[
    (ibes_summary['USFIRM']  == 1) &
    (ibes_summary['MEASURE'] == 'EPS') &
    (ibes_summary['FISCALP'] == 'QTR')
].copy()

# ─── GET LAST FORECAST BEFORE ANNOUNCEMENT ───
ibes_summary = ibes_summary.sort_values(['TICKER', 'FPEDATS', 'STATPERS'])
ibes_pre     = ibes_summary[
    ibes_summary['STATPERS'] < ibes_summary['ANNDATS_ACT']
].copy()

# Group by TICKER + FPEDATS, keep oftic in the result
last_forecast = ibes_pre.groupby(
    ['TICKER', 'FPEDATS']
).last().reset_index()[['TICKER', 'FPEDATS', 'MEDEST', 'NUMEST']]

# ─── MERGE ACTUALS WITH FORECASTS ───
# Both use TICKER internally for matching
ue_df = ibes_actual.merge(
    last_forecast,
    left_on=['TICKER', 'PENDS'],
    right_on=['TICKER', 'FPEDATS'],
    how='inner'
)
ue_df['UE'] = ue_df['VALUE'] - ue_df['MEDEST']

# Keep oftic as the external merge key
ue_df = ue_df.rename(columns={
    'ANNDATS': 'anndats',
    'PENDS':   'pends',
    'VALUE':   'actual_eps',
    'MEDEST':  'median_forecast',
    'NUMEST':  'numest',
})

print(f"UE computed: {len(ue_df)} firm-quarters")
print(f"oftic sample: {ue_df['oftic'].head(5).tolist()}")

# ─── REMERGE UE WITH ±2 DAY WINDOW ───
master = master.drop(
    columns=['UE', 'actual_eps', 'median_forecast', 'numest'],
    errors='ignore'
)

ue_results = []

for _, row in master.iterrows():
    symbol    = row['symbol']
    call_date = row['call_date']

    # Find matching IBES rows within ±2 days
    match = ue_df[
        (ue_df['oftic']   == symbol) &
        (ue_df['anndats'] >= call_date - timedelta(days=2)) &
        (ue_df['anndats'] <= call_date + timedelta(days=2))
    ]

    if match.empty:
        ue_results.append({
            'symbol':          symbol,
            'call_date':       call_date,
            'UE':              np.nan,
            'actual_eps':      np.nan,
            'median_forecast': np.nan,
            'numest':          np.nan
        })
    else:
        # Take closest date match
        match = match.copy()
        match['date_diff'] = (match['anndats'] - call_date).abs()
        best = match.sort_values('date_diff').iloc[0]

        ue_results.append({
            'symbol':          symbol,
            'call_date':       call_date,
            'UE':              best['UE'],
            'actual_eps':      best['actual_eps'],
            'median_forecast': best['median_forecast'],
            'numest':          best['numest']
        })

ue_matched = pd.DataFrame(ue_results)

master = master.merge(
    ue_matched,
    on=['symbol', 'call_date'],
    how='left'
)

print(f"Missing UE:  {master['UE'].isna().sum()}")
print(f"Match rate:  {master['UE'].notna().sum()/len(master)*100:.1f}%")

# Check remaining unmatched
unmatched = master[master['UE'].isna()]['symbol'].value_counts().head(20)
print(f"\nTop unmatched symbols:\n{unmatched}")

# Save
master.to_parquet('Data/master_final.parquet', index=False)
master.to_csv('Data/master_final.csv', index=False)
print("\n✅ Saved")
