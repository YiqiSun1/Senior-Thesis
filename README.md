<!-- # CEO Linguistic Stress & Stock Returns

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
- **Final regression sample**: ~5,342 observations across 429 firms -->

## Motivation: 

Stress is hard to examine. Usually, we gave out a survey and ask people to rate their stress level. This is to some extent a good proxy but with the rise of large language model, it's made possible to quantify stress that's otherwise hard to measure.

Intuitively, CEO stress can be tied to a company performance due to two reasons. First, a stressed CEO might not have a mental capacity to guide company's operation. On the other hand, a stressed CEO could also be a signal of dedication and hard work, which could be good for the company.

This thesis is exploratory in nature and seeks to see if the stress level of CEOs could generate "abnormal" return beyond the market return. I measured CEO stress through the text data of the earning call that they participate in usally quarterly using a psychology-backed prompt given to Claude. The stress level is scored on a scale of 1 to 5, with 5 being the most stressed.


## Main results: 
1. 1 unit increase in stress level exibited in the Q&A session is associated with a 0.9% decrease in the 2-day cumulative abnormal return holding common control variables including firm fundamentals, earnings surprise, and traditional dictionary-based sentiment measures. This means the market immediately react to the LLM stress signal. 

**Dependent variable:** `car_01` · **Estimation:** OLS · **Inference:** clustered (CRV1) · **N:** 7,491 · **R²:** 0.045 · **RMSE:** 0.057

| Coefficient | Estimate | Std. Error | t value | Pr(>\|t\|) |   2.5% |  97.5% |
|:------------|---------:|-----------:|--------:|----------:|-------:|-------:|
| Intercept   |    0.042 |      0.012 |   3.617 |     0.002 |  0.018 |  0.067 |
| **stress_qa** | **−0.009** |  **0.001** | **−6.277** | **0.000** | **−0.012** | **−0.006** |
| vol         |    0.351 |      0.099 |   3.562 |     0.002 |  0.147 |  0.556 |
| mom         |   −0.005 |      0.005 |  −1.114 |     0.277 | −0.016 |  0.005 |
| lnmve       |   −0.002 |      0.001 |  −2.395 |     0.026 | −0.004 | −0.000 |
| bm          |   −0.001 |      0.003 |  −0.403 |     0.691 | −0.008 |  0.005 |
| UE          |    0.031 |      0.004 |   8.048 |     0.000 |  0.023 |  0.039 |
| POSWORDS    |   −0.013 |      0.143 |  −0.089 |     0.930 | −0.309 |  0.283 |
| NEGWORDS    |   −0.764 |      0.237 |  −3.228 |     0.004 | −1.255 | −0.273 |

2. Stress exibited in the prepared remarks has a higher magnitude of effect on the 2-day cumulative abnormal return that the Q&A session. This is unexpected given my prior is that people would pay more attention to the Q&A session since CEO can't prepare the answer to spontaneous questions. 

**Dependent variable:** `car_01` · **Estimation:** OLS · **Inference:** clustered (CRV1) · **N:** 5,342 · **R²:** 0.062 · **RMSE:** 0.056

| Coefficient | Estimate | Std. Error | t value | Pr(>\|t\|) |   2.5% |  97.5% |
|:------------|---------:|-----------:|--------:|----------:|-------:|-------:|
| Intercept   |    0.058 |      0.014 |   3.977 |     0.001 |  0.028 |  0.088 |
| **stress_qa** | **-0.006** | **0.002** | **-3.757** | **0.001** | **-0.010** | **-0.003** |
| **stress_pr** | **-0.013** | **0.002** | **-6.870** | **0.000** | **-0.016** | **-0.009** |
| vol         |    0.472 |      0.109 |   4.352 |     0.000 |  0.247 |  0.697 |
| mom         |   -0.014 |      0.007 |  -1.880 |     0.073 | -0.029 |  0.001 |
| lnmve       |   -0.002 |      0.001 |  -1.951 |     0.064 | -0.005 |  0.000 |
| bm          |    0.000 |      0.004 |   0.003 |     0.997 | -0.009 |  0.009 |
| UE          |    0.031 |      0.004 |   7.676 |     0.000 |  0.023 |  0.040 |
| POSWORDS    |    0.025 |      0.135 |   0.187 |     0.853 | -0.255 |  0.305 |
| NEGWORDS    |   -0.322 |      0.310 |  -1.039 |     0.310 | -0.966 |  0.321 |

* one thing to note: This has a different sample size that the first regressio result since in the initial data cleaning process, some prepared remarks are missing due to the quality of the transcript.


3. Stress signal has no predictive power on both the [2,7] and [2,180] CAR. This means the market adjust to the stress signal very quickly. 


## Work in Progress: 
I am currently working on backtesting this strategy with live market data account for transaction cost. 

Originally, I wanted to incorporate facial image of CEO or even specific characteristics of CEO face such as dark circles for proxy of stress. However, I had some difficulty thinking about how to get quality image of CEOs with universal lightings and angles. Furtherm, audio could be another useful things to add, but some research has done that already. 

## Caveat: 
You can access a paper version of this project in here. The paper does not include backtesting. (https://scholarship.claremont.edu/cmc_theses/4150/)

If you have questions or are interested in the code and methodology, contact me at ysun26@cmc.edu.

I am open to suggestions to improve this project or collaboration on other things. 



