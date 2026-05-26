import pandas as pd
import re

# Load LM dictionary
lm = pd.read_csv('./Data/Loughran-McDonald_MasterDictionary_1993-2025.csv')
positive_words = set(lm[lm['Positive'] > 0]['Word'].str.lower())
negative_words = set(lm[lm['Negative'] > 0]['Word'].str.lower())

def compute_lm_scores(text):
    if pd.isna(text) or len(str(text).strip()) == 0:
        return None, None
    words = re.findall(r'\b[a-zA-Z]+\b', str(text).lower())
    total = len(words)
    if total == 0:
        return None, None
    pos = sum(1 for w in words if w in positive_words) / total
    neg = sum(1 for w in words if w in negative_words) / total
    return pos, neg

# Load call_text
call_text = pd.read_csv('./Data/final_scoring_data.csv')

# Compute — use whole text as Mayew & Venkatachalam do
call_text['POSWORDS'] = call_text['ceo_whole_text'].apply(
    lambda x: compute_lm_scores(x)[0]
)
call_text['NEGWORDS'] = call_text['ceo_whole_text'].apply(
    lambda x: compute_lm_scores(x)[1]
)

# Keep only merge keys + LM scores
lm_scores = call_text[['symbol', 'year', 'quarter', 'POSWORDS', 'NEGWORDS']]

print(f"LM scores computed: {len(lm_scores)}")
print(lm_scores.describe())

# Save
lm_scores.to_csv('./Data/lm_scores.csv', index=False)