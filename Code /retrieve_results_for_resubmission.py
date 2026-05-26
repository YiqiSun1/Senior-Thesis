import anthropic
import json
import re
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

with open('./data_testing_storage/retry_batch_id.json') as f: #change here 
    batch_ids = json.load(f)

def parse_response(raw):
    clean = re.sub(r'```json\s*', '', raw)
    clean = re.sub(r'```\s*', '', clean)
    return json.loads(clean.strip())

results = []

for batch_id in batch_ids:
    batch = client.messages.batches.retrieve(batch_id)

    if batch.processing_status != 'ended':
        print(f"Batch {batch_id} not done yet: {batch.processing_status}")
        continue

    print(f"Processing batch {batch_id}...")

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id

        # Parse custom_id back to components
        # Format: SYMBOL_YEAR_QQUARTER_SECTION
        parts    = custom_id.split('_')
        symbol   = parts[0]
        year     = parts[1]
        quarter  = parts[2]  # e.g. Q1
        section  = '_'.join(parts[3:]).replace('_', ' ')  # rejoin section name

        if result.result.type == 'succeeded':
            try:
                raw    = result.result.message.content[0].text
                parsed = parse_response(raw)

                results.append({
                    'symbol':          symbol,
                    'year':            int(year),
                    'quarter':         int(quarter[1:]),
                    'section':         section,
                    'stress_score':    parsed.get('stress_score'),
                    'primary_markers': str(parsed.get('primary_markers', []))
                    # 'reasoning':       parsed.get('reasoning', ''),
                    # 'confidence':      parsed.get('confidence', ''),
                })

            except Exception as e:
                print(f"  ❌ Parse error for {custom_id}: {e}")

        else:
            print(f"  ❌ Failed: {custom_id} — {result.result.type}")

# Save
df = pd.DataFrame(results)
df.to_csv('./data_testing_storage/stress_scores_final_resubmission.csv', index=False)
df.to_parquet('./data_testing_storage/stress_scores_final_resubmission.parquet', index=False)

print(f"\n✅ Done! {len(df)} results saved")
print(df.groupby('section')['stress_score'].describe())