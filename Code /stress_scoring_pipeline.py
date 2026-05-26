import anthropic
import json
import pandas as pd
import time
from dotenv import load_dotenv
import os
import re


def parse_response(raw):
    # Remove markdown code fences if present
    clean = re.sub(r'```json\s*', '', raw)
    clean = re.sub(r'```\s*', '', clean)
    clean = clean.strip()
    return json.loads(clean)
load_dotenv()  # reads the .env file

call_text = pd.read_csv("./Data/final_scoring_data.csv")

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
# Sample 50
sample = call_text.sample(1, random_state=42)
print(f"Scoring {len(sample)} calls...")

# ─── PROMPT ───
def build_prompt(text, section):
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



SCALE 1 — Coarse (1 to 5):
1 = No stress. Confident, direct, specific. Strong forward guidance.
2 = Minimal stress. Mostly confident with occasional hedging.
3 = Moderate stress. Noticeable hedging, some distancing or vagueness.
4 = High stress. Multiple markers present, evasiveness, strong negative affect.
5 = Very high stress. Pervasive markers throughout, highly evasive, emotionally loaded.



CEO {section} Text:
{text[:4000]}

Return ONLY a raw JSON object. Do NOT wrap it in markdown code blocks or backticks. No ```json, no ```, just the raw JSON object starting with {{ and ending with }}:
{{
    "stress_score_5":  <integer 1-5>,
    "primary_markers": ["specific phrase 1", "specific phrase 2", "specific phrase 3"],
    "reasoning": "2-3 sentences referencing specific language from the text",
    "confidence": "high/medium/low"
}}"""
# ─── SCORE ───
results = []

# Loop through sample and score each section
for i, (_, row) in enumerate(sample.iterrows()):
    symbol  = row['symbol']
    year    = row['year']
    quarter = row['quarter']

    print(f"[{i+1}/10] {symbol} {year} Q{quarter}...")

    for section, text_col in [('Prepared Remarks', 'ceo_pr_text'), 
                                ('Q&A', 'ceo_qa_text')]:
        text = row[text_col]
        if pd.isna(text) or len(str(text).strip()) < 50:
            print(f"  ⚠️ {section}: insufficient text, skipping")
            continue
        # 
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": build_prompt(str(text), section)
                }]
            )

            raw = response.content[0].text.strip()
            print(raw)
        
            parsed = json.loads(raw)

            results.append({
                'symbol':           symbol,
                'year':             year,
                'quarter':          quarter,
                'section':          section,
                'stress_score_5':   parsed['stress_score_5'],
                'primary_markers':  str(parsed['primary_markers']),
                'reasoning':        parsed['reasoning'],
                'confidence':       parsed['confidence'],
                'text_length':      len(text)
            })

            print(f"  ✅ {section}: {parsed['stress_score_5']}/5 ({parsed['confidence']})")

        except json.JSONDecodeError as e:
            print(f"  ❌ {section}: JSON parse error — {e}")
            print(f"     Raw output: {raw[:200]}")
        except Exception as e:
            print(f"  ❌ {section}: {e}")
        

        time.sleep(0.5)  # small delay between calls

# ─── SAVE & PREVIEW ───
scores_df = pd.DataFrame(results)
scores_df.to_parquet('stress_scores_sample10.parquet', index=False)
scores_df.to_csv('stress_scores_sample10.csv', index=False)
