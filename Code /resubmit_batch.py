import anthropic
import json
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Load failed IDs
with open('./data_testing_storage/failed_ids.json') as f:
    failed_ids = json.load(f)

print(f"Failed requests to resubmit: {len(failed_ids)}")

# Load original data
call_text = pd.read_csv("./Data/final_scoring_data.csv")

# Build lookup dictionary from original data
# key: custom_id, value: text
lookup = {}
SECTIONS = [
    ('Prepared_Remarks', 'ceo_pr_text',    'Prepared Remarks'),
    ('QA',               'ceo_qa_text',    'Q&A'),
    ('Whole_Text',       'ceo_whole_text', 'Whole Text'),
]

for _, row in call_text.iterrows():
    for section_id, text_col, section_display in SECTIONS:
        custom_id = f"{row['symbol']}_{row['year']}_Q{row['quarter']}_{section_id}"
        lookup[custom_id] = {
            'text':            row[text_col],
            'section_display': section_display
        }

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

# ─── BUILD RESUBMISSION REQUESTS ───
requests = []
skipped  = 0

for custom_id in failed_ids:
    if custom_id not in lookup:
        print(f"⚠️ Could not find data for: {custom_id}")
        skipped += 1
        continue

    entry = lookup[custom_id]
    text  = entry['text']
    section_display = entry['section_display']

    if pd.isna(text) or len(str(text).strip()) < 50:
        skipped += 1
        continue

    requests.append({
        "custom_id": custom_id,
        "params": {
            "model":       "claude-sonnet-4-6",
            "max_tokens":  500,
            "temperature": 0,
            "messages": [{
                "role":    "user",
                "content": build_prompt_5(str(text), section_display)
            }]
        }
    })

print(f"Requests to resubmit: {len(requests)}")
print(f"Skipped: {skipped}")

# ─── SUBMIT ───
batch = client.messages.batches.create(requests=requests)

print(f"\n✅ Batch ID: {batch.id}")
print(f"Status: {batch.processing_status}")

# Save new batch ID separately
with open('./data_testing_storage/retry_batch_id.json', 'w') as f:
    json.dump([batch.id], f)

print("\nDone — come back in 30 mins to retrieve")