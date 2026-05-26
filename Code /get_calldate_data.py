import earningscall
from earningscall import get_company
import pandas as pd
import time
import os

print(os.getcwd())
earningscall.api_key = "premium_bs5O2kM80MzD0HiSqtZ4HO"

df = pd.read_parquet('./ceo_transcripts_final.parquet')

calls = df.groupby(['symbol', 'year', 'quarter']).size().reset_index()[['symbol', 'year', 'quarter']]
print(f"Total calls to get dates for: {len(calls)}")

DATES_FILE = 'call_dates.csv'
MIN_INTERVAL = 60 / 18
last_call_time = 0

# Resume if file exists
if os.path.exists(DATES_FILE):
    existing = pd.read_csv(DATES_FILE)
    done = set(zip(existing['symbol'], existing['year'], existing['quarter']))
    dates = existing.to_dict('records')
    print(f"Resuming — {len(done)} already done")
else:
    done = set()
    dates = []
    print("Starting fresh")

for _, row in calls.iterrows():
    symbol  = row['symbol']
    year    = row['year']
    quarter = row['quarter']

    # Skip already done
    if (symbol, year, quarter) in done:
        continue

    # Rate limit
    elapsed = time.time() - last_call_time
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)

    try:
        company    = get_company(symbol)
        transcript = company.get_transcript(year=int(year), quarter=int(quarter), level=1)
        last_call_time = time.time()

        call_date = str(transcript.event.conference_date.date()) \
                    if transcript and transcript.event and transcript.event.conference_date \
                    else None

        dates.append({'symbol': symbol, 'year': year, 'quarter': quarter, 'call_date': call_date})
        print(f"✅ {symbol} {year} Q{quarter}: {call_date}")

    except Exception as e:
        dates.append({'symbol': symbol, 'year': year, 'quarter': quarter, 'call_date': None})
        print(f"❌ {symbol} {year} Q{quarter}: {e}")

    # Save every 50 calls
    if len(dates) % 50 == 0:
        pd.DataFrame(dates).to_csv(DATES_FILE, index=False)
        print(f"💾 Saved {len(dates)} so far")

# Final save
dates_df = pd.DataFrame(dates)
dates_df.to_csv(DATES_FILE, index=False)
print(f"\nDone! {dates_df['call_date'].notna().sum()} dates found out of {len(dates_df)}")