import anthropic
import json
import pandas as pd
import time
import re
import os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
call_text = pd.read_csv("./Data/final_scoring_data.csv")
sample = call_text.sample(10, random_state=42)

def parse_response(raw):
    clean = re.sub(r'```json\s*', '', raw)
    clean = re.sub(r'```\s*', '', clean)
    return json.loads(clean.strip())

def build_prompt_5(text, section):
    return f"""You are an expert in psycholinguistics and corporate financial communication.

Analyze the linguistic stress displayed by a CEO in the {section} of an earnings call.

Linguistic stress refers to HOW the CEO speaks, not WHAT topics are discussed. 
Calibrate your scoring relative to a typical confident CEO earnings call — not everyday conversation.

Look for these markers:
 
1. HEDGING: "I think", "perhaps", "we hope", "roughly", "it's difficult to say"
2. PRONOUN DISTANCING: Shifting from "I" to "we", passive voice when addressing bad news
3. NEGATIVE AFFECT: concern, challenge, difficult, uncertainty, headwind, pressure
4. VAGUENESS: Avoiding specific numbers, deflecting questions, non-answers
5. EXCESSIVE QUALIFICATION: Unusual caveats, disclaimers, conditional statements
6. DISFLUENCY: Restarts, repetition, filler phrases ("you know", "sort of")
7. TEMPORAL ORIENTATION: Excessive focus on past problems vs forward guidance

Score 1 to 5 (integers only):
1 = No stress. Confident, direct, specific. Strong forward guidance.
2 = Minimal stress. Mostly confident with occasional hedging.
3 = Moderate stress. Noticeable hedging, some distancing or vagueness.
4 = High stress. Multiple markers present, evasiveness, strong negative affect.
5 = Very high stress. Pervasive markers throughout, highly evasive, emotionally loaded.

CEO {section} Text:
{text[:4000]}

Return ONLY a raw JSON object, no markdown, no backticks:
{{
    "stress_score": <integer 1-5>,
    "primary_markers": ["phrase 1", "phrase 2", "phrase 3"],
    "reasoning": "2-3 sentences",
    "confidence": "high/medium/low"
}}"""

def score_batch(sample, section, text_col, prompt_fn, scale_label):
    results = []
    print(f"\n{'='*40}")
    print(f"Scoring: {section} | Scale: {scale_label}")
    print(f"{'='*40}")

    for i, (_, row) in enumerate(sample.iterrows()):
        symbol  = row['symbol']
        year    = row['year']
        quarter = row['quarter']
        text    = row[text_col]

        print(f"[{i+1}/10] {symbol} {year} Q{quarter}...", end=' ')

        if pd.isna(text) or len(str(text).strip()) < 50:
            print("⚠️ insufficient text")
            continue

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt_fn(str(text), section)
                }]
            )

            raw    = response.content[0].text.strip()
            parsed = parse_response(raw)

            results.append({
                'symbol':          symbol,
                'year':            year,
                'quarter':         quarter,
                'call_date':       row['call_date'],
                'section':         section,
                'scale':           scale_label,
                'stress_score':    parsed.get('stress_score'),
            })
            
            print(f"✅ {parsed.get('stress_score')}")
        except Exception as e:
            print(f"❌ {e}")

        time.sleep(0.5)

    return pd.DataFrame(results)

# ─── RUN FOUR SEPARATE BATCHES ───
df_pr_5  = score_batch(sample, 'Prepared Remarks', 'ceo_pr_text', build_prompt_5,  '1-5')
df_qa_5  = score_batch(sample, 'Q&A','ceo_qa_text', build_prompt_5,  '1-5')
df_qa_whole = score_batch(sample, 'Whole Text','ceo_whole_text', build_prompt_5,  '1-5')


# ─── COMBINE AND SAVE ───
all_scores = pd.concat([df_pr_5, df_qa_5, df_qa_whole], ignore_index=True)
all_scores.to_csv('./data_testing_storage/stress_scores_test.csv', index=False)
all_scores.to_parquet('./data_testing_storage/stress_scores_test.parquet', index=False)

