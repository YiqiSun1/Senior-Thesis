# ============================================================
# CEO Stress Scoring from Earnings Call Transcripts
# Sample code for thesis project
# ============================================================
# Install dependencies first:
# pip install transformers torch vaderSentiment openai pandas
from transformers import pipeline
import pandas as pd

# ============================================================
# APPROACH 1: VADER (simplest baseline, dictionary-based)
# ============================================================
# from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# def score_vader(text):
#     analyzer = SentimentIntensityAnalyzer()
#     scores = analyzer.polarity_scores(text)
#     # compound score ranges from -1 (most negative) to +1 (most positive)
#     # we invert it so higher = more stressed
#     stress_score = 1 - ((scores['compound'] + 1) / 2)  # normalize to 0-1
#     return round(stress_score, 4)

# Example
sample_text = """
We are cautiously navigating a very challenging macro environment. 
There is significant uncertainty ahead and we remain concerned 
about headwinds in our core markets going forward. 
"""

# print("=== VADER ===")
# print(f"Stress score: {score_vader(sample_text)}")
# Higher score = more stressed/negative


# ============================================================
# APPROACH 2: FinBERT (finance-specific sentiment)
# ============================================================
# from transformers import pipeline

# def load_finbert():
#     return pipeline(
#         "text-classification",
#         model="ProsusAI/finbert",
#         return_all_scores=True
#     )

# def score_finbert(text, classifier):
#     results = classifier(text[:512])[0]  # FinBERT max 512 tokens
#     # returns [positive, negative, neutral] scores
#     scores = {r['label']: r['score'] for r in results}
#     # use negative score as stress proxy
#     return round(scores.get('negative', 0), 4)

# print("\n=== FinBERT ===")
# finbert = load_finbert()
# print(f"Stress score: {score_finbert(sample_text, finbert)}")


# ============================================================
# APPROACH 3: Mental-RoBERTa (mental health focused)
# ============================================================
def load_mental_roberta():
    return pipeline(
        "text-classification",
        model="mental/mental-roberta-base",
        return_all_scores=True
    )

def score_mental_roberta(text, classifier):
    results = classifier(text[:512])[0]
    scores = {r['label']: r['score'] for r in results}
    # model outputs stress-related labels
    # check model card on HuggingFace for exact label names
    stress_score = scores.get('stress', scores.get('LABEL_1', 0))
    return round(stress_score, 4)

print("\n=== Mental-RoBERTa ===")
mental_roberta = load_mental_roberta()
print(f"Stress score: {score_mental_roberta(sample_text, mental_roberta)}")


# ============================================================
# APPROACH 4: GPT-4o via API (most powerful)
# ============================================================
from openai import OpenAI

def score_gpt4o(text, api_key):
    client = OpenAI(api_key=api_key)
    
    prompt = f"""You are an expert psychologist analyzing executive speech patterns.
    
Read the following excerpt from a CEO earnings call and rate the CEO's psychological 
stress level on a scale from 0 to 10, where:
- 0 = completely calm, confident, no stress indicators
- 5 = moderate stress, some uncertainty or hedging language
- 10 = severe stress, high anxiety, evasiveness, emotional distress

Consider these stress markers:
- Hedging language (maybe, perhaps, cautiously, potentially)
- Uncertainty expressions (unclear, uncertain, challenging, difficult)
- Negative affect words (concerned, worried, struggling)
- Evasiveness or vague answers
- Defensive tone

Return ONLY a JSON object like this: {{"stress_score": 7.5, "reasoning": "brief explanation"}}

CEO transcript excerpt:
# {text}"""

#     response = client.chat.completions.create(
#         model="gpt-4o",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0  # deterministic output
#     )
    
#     import json
#     result = json.loads(response.choices[0].message.content)
#     return result

# print("\n=== GPT-4o ===")
# Uncomment and add your API key to run:
# result = score_gpt4o(sample_text, api_key="your-api-key-here")
# print(f"Stress score: {result['stress_score']}")
# print(f"Reasoning: {result['reasoning']}")
# print("(Add your OpenAI API key to run this)")


# ============================================================
# PUTTING IT ALL TOGETHER: Score a dataset of transcripts
# ============================================================

# def score_all_models(transcripts_df, text_col='transcript'):
#     """
#     transcripts_df: DataFrame with columns like:
#         - company: company ticker (e.g. AAPL)
#         - date: earnings call date
#         - transcript: the CEO's text
#         - stock_return_30d: 30-day return after call (your outcome variable)
#     """
#     print("Loading models...")
#     finbert_clf = load_finbert()
#     mental_clf = load_mental_roberta()
    
#     results = []
#     for _, row in transcripts_df.iterrows():
#         text = row[text_col]
#         results.append({
#             'company': row['company'],
#             'date': row['date'],
#             'vader_stress': score_vader(text),
#             'finbert_stress': score_finbert(text, finbert_clf),
#             'mental_roberta_stress': score_mental_roberta(text, mental_clf),
#             'stock_return_30d': row.get('stock_return_30d', None)
#         })
    
#     return pd.DataFrame(results)


# ============================================================
# SIMPLE REGRESSION: Stress score -> Stock return
# ============================================================
# import statsmodels.api as sm

# def run_regression(scored_df, stress_col='mental_roberta_stress'):
#     """
#     Basic OLS regression: stock_return ~ stress_score
#     In your actual thesis you'd add controls:
#     - earnings surprise
#     - firm size
#     - industry fixed effects
#     - time fixed effects
#     """
#     df = scored_df.dropna(subset=[stress_col, 'stock_return_30d'])
    
#     X = sm.add_constant(df[stress_col])
#     y = df['stock_return_30d']
    
#     model = sm.OLS(y, X).fit()
#     print(model.summary())
#     return model

# Example usage:
# scored_df = score_all_models(your_transcripts_df)
# model = run_regression(scored_df, stress_col='mental_roberta_stress')


# ============================================================
# NOTES FOR YOUR THESIS
# ============================================================
"""
Key methodological decisions to document:

1. TEXT SEGMENTATION: Do you score the full transcript or just CEO portions?
   - Recommend: isolate CEO speaking turns only, exclude analyst questions

2. CHUNKING: Models have token limits (512 for BERT-based models)
   - For long transcripts, score in chunks and average

3. STOCK RETURN WINDOW: Which return window to use?
   - Same-day: tests immediate market reaction
   - 30-day: tests whether stress predicts future drift
   - 60-day: longer term prediction

4. CONTROLS to include in regression:
   - Earnings surprise (actual vs expected EPS)
   - Firm size (log market cap)
   - Book-to-market ratio
   - Industry fixed effects
   - Quarter fixed effects

5. ROBUSTNESS CHECKS:
   - Compare results across all four models
   - Split sample by industry
   - Test different return windows
"""
