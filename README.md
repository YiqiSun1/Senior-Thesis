# CEO Linguistic Stress & Stock Returns

A senior thesis project using NLP and financial econometrics to test whether linguistic stress indicators in CEO earnings call communications predict short- and long-term stock market abnormal returns.

---

## Research Question

Can the **linguistic stress evident in CEO communication** — measured through psycholinguistic markers in earnings call transcripts — predict **Cumulative Abnormal Returns (CAR)** over different time windows?

---

## Methodology Overview

```
Earnings Call Transcripts
        ↓
Extract CEO speech (Prepared Remarks + Q&A)
        ↓
Score linguistic stress via Claude (1–5 scale)
        ↓
Merge with CRSP returns, Compustat fundamentals, IBES forecasts
        ↓
Compute Cumulative Abnormal Returns (CAR)
        ↓
Regression analysis (OLS + Fixed Effects)
```

---

## Data Sources

| Source | Description | File |
|--------|-------------|------|
| earningscall API | S&P 500 earnings call transcripts (2020–2026) | `Data/ceo_transcripts_final.parquet` |
| CRSP | Daily stock returns and value-weighted market returns | `Data/crsp_daily.csv` |
| Compustat | Quarterly firm-level financial fundamentals | `Data/fundamental .csv` |
| IBES | Analyst EPS forecasts and actuals | `Data/actual_EPS.csv`, `Data/summarystatistics.csv` |
| Loughran-McDonald | Financial sentiment dictionary (1993–2025) | Used via `Code /add_lm.py` |

---

## Project Structure

```
├── Code /                          # Data pipeline scripts
│   ├── get_data.py                 # Pull transcripts from earningscall API
│   ├── stress_scoring.py           # Score CEO stress via Claude API
│   ├── CRSP_merge.py               # Merge stress scores with CRSP returns
│   ├── Car_0_1_2_180.py            # Compute CAR windows (0→1, 0→180 days)
│   ├── Car2_180.py                 # CAR window robustness: days 2–180
│   ├── Car_2_7.py                  # CAR window robustness: days 2–7
│   ├── merging_everything.py       # Master merge: stress + CRSP + fundamentals
│   ├── merging_fundamental.py      # Compustat integration
│   ├── merging_IBES.py             # IBES analyst forecast integration
│   ├── add_lm.py                   # Add Loughran-McDonald sentiment scores
│   └── ...
├── regression/                     # Regression analysis scripts
│   ├── ROA.py                      # Regressions on Return on Assets
│   └── ...
├── Data/                           # Raw and processed datasets
│   ├── ceo_transcripts_final.parquet   # All transcripts (285 MB)
│   ├── new_car_1_with_fundamental.csv  # Main analysis dataset (1.5 MB)
│   ├── master_final.csv                # Full merged master dataset
│   └── ...
├── data_testing_storage/
│   └── pivoted_stress_scores.csv   # Stress scores for 3,000+ company-quarters
├── regression_result/              # Regression output logs
├── Documentation/                  # Project notes
└── archive/                        # Legacy/exploratory scripts
```

---

## Key Variables

### Dependent Variables
| Variable | Description |
|----------|-------------|
| `car_01` | Cumulative Abnormal Return, days 0 to +1 (2-day) |
| `car_0180` | Cumulative Abnormal Return, days 0 to +180 (6-month) |
| Future ROA | Return on Assets 2 quarters forward |
| Future OCF | Operating Cash Flow 2 quarters forward |

### Independent Variables — Stress Scores
| Variable | Description |
|----------|-------------|
| `stress_pr` | CEO linguistic stress in Prepared Remarks (1–5 scale) |
| `stress_qa` | CEO linguistic stress in Q&A session (1–5 scale) |
| `stress_whole` | CEO linguistic stress across the full call (1–5 scale) |

### Control Variables
| Variable | Description |
|----------|-------------|
| `vol` | Historical volatility (std of returns, 125 trading days prior) |
| `mom` | Momentum (abnormal return, days −127 to −2) |
| `lnmve` | Log market value of equity (size) |
| `bm` | Book-to-market ratio (value factor) |
| `UE` | Unexpected earnings (Actual EPS − Analyst Median Forecast) |
| `POSWORDS` | Count of Loughran-McDonald positive words |
| `NEGWORDS` | Count of Loughran-McDonald negative words |

---

## Stress Scoring via LLM

Stress scores are generated using **Claude Sonnet** (Anthropic API) applied to CEO speech segments. The model rates stress on an integer scale of **1–5**, calibrated to reflect typical CEO communication patterns.

**Psycholinguistic markers analyzed:**
1. Hedging language ("I think", "perhaps", "roughly")
2. Pronoun distancing (I → we, passive voice shifts)
3. Negative affect (expressions of concern, uncertainty, challenge)
4. Vagueness (avoidance of specific numbers or commitments)
5. Excessive qualification and caveats
6. Disfluency (restarts, fillers, repetition)
7. Temporal orientation (dwelling on past problems vs. forward guidance)

Each earnings call is scored in three segments:
- **Prepared Remarks (PR)**: CEO's scripted opening statement
- **Q&A**: CEO responses to analyst questions
- **Whole Call**: Aggregate of the full transcript

---

## Abnormal Returns Calculation

Abnormal Return (AR) for each trading day is computed as:

```
AR_t = R_t - R_market_t
```

where `R_market_t` is the CRSP value-weighted market return.

Cumulative Abnormal Returns:

```
CAR(t1, t2) = Σ AR_t  for t = t1 to t2
```

Event windows computed: `(0,1)`, `(0,7)`, `(0,27)`, `(0,180)`, `(2,7)`, `(2,180)`

---

## Regression Specifications

Four specifications are estimated for each dependent variable:

| Model | Specification |
|-------|--------------|
| No FE | OLS with two-way clustered standard errors (firm × time) |
| Firm FE | Fixed effects by company |
| Time FE | Fixed effects by quarter |
| Firm + Time FE | Both firm and time fixed effects (most stringent) |

Implemented using [`pyfixest`](https://github.com/py-econometrics/pyfixest).

### Selected Results (CAR 0→1, stress_qa)

| Variable | Coefficient | p-value |
|----------|-------------|---------|
| `stress_qa` | −0.008 | < 0.001 |
| `stress_pr` | −0.014 | < 0.001 |
| `UE` | +0.040 | < 0.001 |
| `POSWORDS` | +0.430 | 0.023 |
| `NEGWORDS` | −1.387 | < 0.001 |

**Sample**: ~5,342 observations, 429 firms, 2020–2025.

Higher CEO linguistic stress is associated with significantly lower 2-day abnormal returns, even after controlling for earnings surprises, sentiment, size, value, volatility, and momentum.

---

## Setup & Dependencies

```bash
pip install anthropic earningscall pandas numpy pyfixest python-dotenv
```

Additional dependencies for video analysis (exploratory):
```bash
pip install mediapipe opencv-python yt-dlp
```

API credentials required:
- Anthropic API key (for Claude stress scoring)
- earningscall API key (for transcript access)
- WRDS access (for CRSP, Compustat, IBES data)

Store credentials in a `.env` file (never commit this file):
```
ANTHROPIC_API_KEY=your_key_here
EARNINGSCALL_API_KEY=your_key_here
```

---

## Pipeline Execution Order

1. `Code /get_data.py` — fetch earnings call transcripts
2. `Code /stress_scoring.py` — score CEO stress via Claude
3. `Code /CRSP_merge.py` — merge with CRSP stock data
4. `Code /Car_0_1_2_180.py` — compute CAR at all event windows
5. `Code /merging_fundamental.py` — merge Compustat fundamentals
6. `Code /merging_IBES.py` — merge IBES analyst forecasts
7. `Code /merging_everything.py` — produce master dataset
8. `Code /add_lm.py` — append Loughran-McDonald sentiment scores
9. `regression/` scripts — estimate regression models

---

## Sample Coverage

- **Universe**: S&P 500 companies
- **Period**: 2020 Q1 – 2026 Q1
- **Quarters per firm**: Up to 4 per year
- **Company-quarters scored**: 3,000+
- **Final regression sample**: ~5,342 observations across 429 firms
