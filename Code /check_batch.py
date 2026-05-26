import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

with open('./data_testing_storage/retry_batch_id.json') as f:
    batch_ids = json.load(f)

for batch_id in batch_ids:
    batch = client.messages.batches.retrieve(batch_id)
    counts = batch.request_counts
    print(f"\nBatch: {batch_id}")
    print(f"  Status:    {batch.processing_status}")
    print(f"  Succeeded: {counts.succeeded}")
    print(f"  Errored:   {counts.errored}")
    print(f"  Processing:{counts.processing}")