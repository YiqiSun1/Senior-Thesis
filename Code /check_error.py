import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

with open('./data_testing_storage/batch_ids.json') as f:
    batch_ids = json.load(f)

failed_ids = []

for batch_id in batch_ids:
    print(f"\nChecking batch: {batch_id}")
    
    for result in client.messages.batches.results(batch_id):
        if result.result.type != 'succeeded':
            print(f"  ❌ {result.custom_id}: {result.result.type}")
            failed_ids.append(result.custom_id)

print(f"\nTotal failed: {len(failed_ids)}")

# Save failed IDs for resubmission
with open('./data_testing_storage/failed_ids.json', 'w') as f:
    json.dump(failed_ids, f)

print("Saved to failed_ids.json")