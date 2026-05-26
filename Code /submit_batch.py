import anthropic
import json
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

call_text = pd.read_csv("./Data/final_scoring_data.csv")

SECTIONS = [
    ('Prepared_Remarks', 'ceo_pr_text',   'Prepared Remarks'),
    ('QA',               'ceo_qa_text',   'Q&A'),
    ('Whole_Text',       'ceo_whole_text','Whole Text'),
]

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

# ─── BUILD REQUESTS ───
requests = []

for _, row in call_text.iterrows():
    for section_id, text_col, section_display in SECTIONS:
        text = row[text_col]

        # Skip insufficient text
        if pd.isna(text) or len(str(text).strip()) < 50:
            continue

        # custom_id is your key to match results back to rows
        custom_id = f"{row['symbol']}_{row['year']}_Q{row['quarter']}_{section_id}"

        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 500,
                "temperature": 0,
                "messages": [{
                    "role": "user",
                    "content": build_prompt_5(str(text), section_display)
                }]
            }
        })

print(f"Total requests to submit: {len(requests)}")

# ─── SUBMIT IN BATCHES OF 10,000 (API limit per batch) ───
BATCH_SIZE = 10000
batch_ids  = []

for i in range(0, len(requests), BATCH_SIZE):
    chunk = requests[i:i + BATCH_SIZE]
    print(f"Submitting batch {i//BATCH_SIZE + 1}: {len(chunk)} requests...")
    response = client.messages.batches.create(requests=chunk)
    batch_ids.append(response.id)
    print(f"  ✅ Batch ID: {response.id} | Status: {response.processing_status}")

# Save batch IDs so you can retrieve results later
with open('./data_testing_storage/batch_ids.json', 'w') as f:
    json.dump(batch_ids, f)

print(f"\nAll batches submitted. IDs saved to batch_ids.json")
print(f"Come back in 1-24 hours to retrieve results")

# ─── SUBMIT — single batch for testing ───
# print("Checking custom_ids...")
# for req in requests:
#     cid = req['custom_id']
#     import re
#     if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', cid):
#         print(f"❌ BAD: '{cid}'")
#     else:
#         print(f"✅ OK:  '{cid}'")
# batch = client.messages.batches.create(requests=requests)
# batch_id = batch.id

# print(f"✅ Batch ID: {batch_id}")
# print(f"Status: {batch.processing_status}")

# # Save batch ID
# with open('./data_testing_storage/batch_ids.json', 'w') as f:
#     json.dump([batch_id], f)

# print(f"\nBatch submitted. Come back in a few minutes to retrieve results.")