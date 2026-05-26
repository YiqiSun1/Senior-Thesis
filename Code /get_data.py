import earningscall
from earningscall import get_company
import pandas as pd
import time
import logging
import os

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────
earningscall.api_key = "premium_bs5O2kM80MzD0HiSqtZ4HO"

LOG_FILE         = "pull_progress.log"
PROGRESS_FILE    = "ceo_transcripts_progress.parquet"
FINAL_FILE       = "ceo_transcripts_final.parquet"
FAILED_FILE      = "failed_calls.csv"
TICKERS_FILE     = "sp500_tickers_used.csv"
YEARS            = range(2020, 2026)
QUARTERS         = range(1, 5)
CALLS_PER_MINUTE = 18
MIN_INTERVAL     = 60 / CALLS_PER_MINUTE

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

def log(msg):
    logging.info(msg)
    print(msg)

# ─────────────────────────────────────────
# RATE LIMITER WITH RETRY
# ─────────────────────────────────────────
last_call_time = 0

def rate_limited_fetch(company, year, quarter, level=2):
    global last_call_time
    elapsed = time.time() - last_call_time
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)

    for attempt in range(3):
        try:
            result = company.get_transcript(year=year, quarter=quarter, level=level)
            last_call_time = time.time()
            return result
        except Exception as e:
            if attempt < 2:
                log(f"    ⚠️ Retry {attempt+1}/3: {e}")
                time.sleep(10)
            else:
                raise

# ─────────────────────────────────────────
# TICKERS
# ─────────────────────────────────────────
sp500 = [
    'MMM', 'AOS', 'ABT', 'ABBV', 'ACN', 'ADBE', 'AMD', 'AES', 'AFL', 'A',
    'APD', 'ABNB', 'AKAM', 'ALB', 'ARE', 'ALGN', 'ALLE', 'LNT', 'ALL', 'GOOGL',
    'GOOG', 'MO', 'AMZN', 'AMCR', 'AEE', 'AAL', 'AEP', 'AXP', 'AIG', 'AMT',
    'AWK', 'AMP', 'AME', 'AMGN', 'APH', 'ADI', 'ANSS', 'AON', 'APA', 'AAPL',
    'AMAT', 'APTV', 'ACGL', 'ADM', 'ANET', 'AJG', 'AIZ', 'T', 'ATO', 'ADSK',
    'AZO', 'AVB', 'AVY', 'AXON', 'BKR', 'BALL', 'BAC', 'BK', 'BBWI', 'BAX',
    'BDX', 'BRK-B', 'BBY', 'BIO', 'TECH', 'BIIB', 'BLK', 'BX', 'BA', 'BMY',
    'AVGO', 'BR', 'BRO', 'BF-B', 'BLDR', 'BSX', 'BWA', 'BXP', 'CHRW', 'CDNS',
    'CZR', 'CPT', 'CPB', 'COF', 'CAH', 'KMX', 'CCL', 'CARR', 'CAT', 'CBOE',
    'CBRE', 'CDW', 'CE', 'COR', 'CNC', 'CF', 'CRL', 'SCHW', 'CHTR', 'CVX',
    'CMG', 'CB', 'CHD', 'CI', 'CINF', 'CTAS', 'CSCO', 'C', 'CFG', 'CLX',
    'CME', 'CMS', 'KO', 'CTSH', 'CL', 'CMCSA', 'CAG', 'COP', 'ED', 'STZ',
    'CEG', 'COO', 'CPRT', 'GLW', 'CTVA', 'CSGP', 'COST', 'CTRA', 'CCI', 'CSX',
    'CMI', 'CVS', 'DHI', 'DHR', 'DRI', 'DVA', 'DAY', 'DECK', 'DE', 'DAL',
    'DVN', 'DXCM', 'FANG', 'DLR', 'DFS', 'DG', 'DLTR', 'D', 'DPZ', 'DOV',
    'DOW', 'DTE', 'DUK', 'DD', 'EMN', 'ETN', 'EBAY', 'ECL', 'EIX', 'EW',
    'EA', 'ELV', 'LLY', 'EMR', 'ENPH', 'ETR', 'EOG', 'EPAM', 'EQT', 'EFX',
    'EQIX', 'EQR', 'ESS', 'EL', 'ETSY', 'EG', 'EVRG', 'ES', 'EXC', 'EXPE',
    'EXPD', 'EXR', 'XOM', 'FFIV', 'FDS', 'FICO', 'FAST', 'FRT', 'FDX', 'FIS',
    'FITB', 'FSLR', 'FE', 'FI', 'FMC', 'F', 'FTNT', 'FTV', 'FOXA', 'FOX',
    'BEN', 'FCX', 'GRMN', 'IT', 'GE', 'GEHC', 'GEV', 'GEN', 'GNRC', 'GD',
    'GIS', 'GM', 'GPC', 'GILD', 'GPN', 'GL', 'GDDY', 'GS', 'HAL', 'HIG',
    'HAS', 'HCA', 'DOC', 'HSIC', 'HSY', 'HES', 'HPE', 'HLT', 'HOLX', 'HD',
    'HON', 'HRL', 'HST', 'HWM', 'HPQ', 'HUBB', 'HUM', 'HBAN', 'HII', 'IBM',
    'IEX', 'IDXX', 'ITW', 'INCY', 'IR', 'PODD', 'INTC', 'ICE', 'IFF', 'IP',
    'IPG', 'INTU', 'ISRG', 'IVZ', 'INVH', 'IQV', 'IRM', 'JKHY', 'J', 'JNJ',
    'JCI', 'JPM', 'JNPR', 'K', 'KVUE', 'KDP', 'KEY', 'KEYS', 'KMB', 'KIM',
    'KMI', 'KLAC', 'KHC', 'KR', 'LHX', 'LH', 'LRCX', 'LW', 'LVS', 'LDOS',
    'LEN', 'LIN', 'LYV', 'LKQ', 'LMT', 'L', 'LOW', 'LULU', 'LYB', 'MTB',
    'MRO', 'MPC', 'MKTX', 'MAR', 'MMC', 'MLM', 'MAS', 'MA', 'MTCH', 'MKC',
    'MCD', 'MCK', 'MDT', 'MRK', 'META', 'MET', 'MTD', 'MGM', 'MCHP', 'MU',
    'MSFT', 'MAA', 'MRNA', 'MHK', 'MOH', 'TAP', 'MDLZ', 'MPWR', 'MNST', 'MCO',
    'MS', 'MOS', 'MSI', 'MSCI', 'NDAQ', 'NTAP', 'NFLX', 'NEM', 'NWSA', 'NWS',
    'NEE', 'NKE', 'NI', 'NDSN', 'NSC', 'NTRS', 'NOC', 'NCLH', 'NRG', 'NUE',
    'NVDA', 'NVR', 'NXPI', 'ORLY', 'OXY', 'ODFL', 'OMC', 'ON', 'OKE', 'ORCL',
    'OTIS', 'PCAR', 'PKG', 'PANW', 'PARA', 'PH', 'PAYX', 'PAYC', 'PYPL', 'PNR',
    'PEP', 'PFE', 'PCG', 'PM', 'PSX', 'PNW', 'PNC', 'POOL', 'PPG', 'PPL',
    'PFG', 'PG', 'PGR', 'PLD', 'PRU', 'PEG', 'PTC', 'PSA', 'PHM', 'QRVO',
    'PWR', 'QCOM', 'DGX', 'RL', 'RJF', 'RTX', 'O', 'REG', 'REGN', 'RF',
    'RSG', 'RMD', 'RVTY', 'ROK', 'ROL', 'ROP', 'ROST', 'RCL', 'SPGI', 'CRM',
    'SBAC', 'SLB', 'STX', 'SRE', 'NOW', 'SHW', 'SPG', 'SWKS', 'SJM', 'SNA',
    'SOLV', 'SO', 'LUV', 'SWK', 'SBUX', 'STT', 'STLD', 'STE', 'SYK', 'SMCI',
    'SYF', 'SNPS', 'SYY', 'TMUS', 'TROW', 'TTWO', 'TPR', 'TRGP', 'TGT', 'TEL',
    'TDY', 'TFX', 'TER', 'TSLA', 'TXN', 'TXT', 'TMO', 'TJX', 'TSCO', 'TT',
    'TDG', 'TRV', 'TRMB', 'TFC', 'TYL', 'TSN', 'USB', 'UBER', 'UDR', 'ULTA',
    'UNP', 'UAL', 'UPS', 'URI', 'UNH', 'UHS', 'VLO', 'VTR', 'VLTO', 'VRSN',
    'VRSK', 'VZ', 'VRTX', 'VTRS', 'VICI', 'V', 'VMC', 'WRB', 'GWW', 'WAB',
    'WBA', 'WMT', 'DIS', 'WBD', 'WM', 'WAT', 'WEC', 'WFC', 'WELL', 'WST',
    'WDC', 'WY', 'WHR', 'WMB', 'WTW', 'WYNN', 'XEL', 'XYL', 'YUM', 'ZBRA',
    'ZBH', 'ZTS', 'APP', 'DDOG', 'DOCU', 'HOOD', 'DASH', 'TKO', 'WSM', 'EME'
]

pd.DataFrame({'Symbol': sp500}).to_csv(TICKERS_FILE, index=False)

# ─────────────────────────────────────────
# RESUME — find already completed symbols
# ─────────────────────────────────────────
if os.path.exists("ceo_transcripts_progress.parquet"):
    existing_df = pd.read_parquet("ceo_transcripts_progress.parquet")
    completed_symbols = set(existing_df['symbol'].unique())
    results = [existing_df]  # start with existing data
    log(f"Resuming — {len(completed_symbols)} companies already done, "
        f"{len(sp500) - len(completed_symbols)} remaining")
else:
    completed_symbols = set()
    results = []
    log(f"Starting fresh — {len(sp500)} companies to pull")

# ─────────────────────────────────────────
# LOAD EXISTING FAILED CALLS IF ANY
# ─────────────────────────────────────────
if os.path.exists(FAILED_FILE):
    existing_failed = pd.read_csv(FAILED_FILE).to_dict('records')
    failed = existing_failed
    log(f"Loaded {len(failed)} existing failed calls")
else:
    failed = []

# ─────────────────────────────────────────
# PULL — skip already completed symbols
# ─────────────────────────────────────────
remaining = [s for s in sp500 if s not in completed_symbols]
log(f"Pulling {len(remaining)} remaining companies...")

for i, symbol in enumerate(remaining):
    log(f"[{i+1}/{len(remaining)}] Processing {symbol}...")

    try:
        
        company = get_company(symbol)

        for year in YEARS:
            for quarter in QUARTERS:
                try:
                    transcript = rate_limited_fetch(company, year, quarter)

                    if transcript is None:
                        continue

                    rows = []
                    for speaker in transcript.speakers:
                        if speaker.speaker_info is None:
                            continue

                        rows.append({
                            "symbol":           symbol,
                            "year":             year,
                            "quarter":          quarter,
                            "speaker_name":     speaker.speaker_info.name or "UNKNOWN",
                            "speaker_title":    speaker.speaker_info.title or "",
                            "text":             speaker.text or "",
                            "prepared_remarks": transcript.prepared_remarks,
                            "qa":               transcript.questions_and_answers,
                        })

                    if rows:
                        df_call = pd.DataFrame(rows)

                        df_call["is_ceo"] = df_call["speaker_title"].str.contains(
                            "CEO|Chief Executive", na=False, case=False
                        )

                        internal_keywords = "CEO|CFO|COO|President|Vice President|Director|Chief|IR"
                        operator_keywords = "Operator|Conference|Moderator"

                        df_call["is_internal"] = (
                            df_call["speaker_title"].str.contains(
                                internal_keywords, na=False, case=False) |
                            df_call["speaker_name"].str.contains(
                                internal_keywords, na=False, case=False)
                        )
                        df_call["is_operator"] = (
                            df_call["speaker_title"].str.contains(
                                operator_keywords, na=False, case=False) |
                            df_call["speaker_name"].str.contains(
                                operator_keywords, na=False, case=False)
                        )
                        df_call["is_analyst"] = (
                            ~df_call["is_internal"] &
                            ~df_call["is_operator"] &
                            df_call["speaker_title"].notna() &
                            df_call["speaker_title"].str.strip().ne("") &
                            df_call["speaker_name"].notna() &
                            df_call["speaker_name"].str.strip().ne("UNKNOWN")
                        )
                        df_call["is_qa"] = df_call["is_analyst"].cummax()

                        results.append(df_call)
                        log(f"  ✅ {symbol} {year} Q{quarter} — "
                            f"{len(df_call)} rows | "
                            f"{df_call['is_ceo'].sum()} CEO turns | "
                            f"{(df_call['is_ceo'] & df_call['is_qa']).sum()} CEO Q&A turns")

                except Exception as e:
                    failed.append({
                        "symbol":  symbol,
                        "year":    year,
                        "quarter": quarter,
                        "error":   str(e)
                    })
                    log(f"  ❌ {symbol} {year} Q{quarter}: {e}")
                    continue

    except Exception as e:
        log(f"  ⚠️ Skipping {symbol} entirely: {e}")
        continue

    # Save progress after every company
    if results:
        pd.concat(results, ignore_index=True).to_parquet(
            "ceo_transcripts_progress.parquet", index=False
        )
        log(f"  💾 Progress saved after {symbol} [{i+1}/{len(remaining)}]")

# ─────────────────────────────────────────
# FINAL SAVE
# ─────────────────────────────────────────
if results:
    final_df = pd.concat(results, ignore_index=True)
    final_df.to_parquet("ceo_transcripts_final.parquet", index=False)

    log("=" * 50)
    log("🎉 PULL COMPLETE")
    log(f"   Total rows:       {len(final_df)}")
    log(f"   Companies:        {final_df['symbol'].nunique()}")
    log(f"   CEO rows:         {final_df['is_ceo'].sum()}")
    log(f"   CEO Q&A rows:     {(final_df['is_ceo'] & final_df['is_qa']).sum()}")
    log(f"   Saved to:         {FINAL_FILE}")
    log("=" * 50)
else:
    log("⚠️ No data collected — check API key and connection")

if failed:
    pd.DataFrame(failed).to_csv("failed_calls.csv", index=False)
    log(f"   Failed calls: {len(failed)} — saved to failed_calls.csv")