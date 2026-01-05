# Instructions to Submit Retry Batches

## Prerequisites

1. **Install OpenAI package** (if not already installed):
   ```bash
   pip install openai
   # or if using venv:
   source venv/bin/activate
   pip install openai
   ```

2. **Set OpenAI API Key**:
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   # Or load from .env file:
   source venv/bin/.env  # if it's a shell script
   # Or manually:
   export $(cat venv/bin/.env | xargs)
   ```

## Submit Batches

Run the submission script:

```bash
python3 submit_retry_batches.py
```

## Manual Submission (Alternative)

If you prefer to submit manually using Python:

```python
import openai
import os
from pathlib import Path

# Set API key
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Upload and submit gpt-5 batch
batch_file = Path("data/retry_batches/gpt_5_retry_3000tokens.jsonl")
with open(batch_file, 'rb') as f:
    file_response = client.files.create(file=f, purpose="batch")

batch_response = client.batches.create(
    input_file_id=file_response.id,
    endpoint="/v1/chat/completions",
    completion_window="24h",
    metadata={
        "model": "gpt-5",
        "description": "Retry token limit failures - gpt-5 - 3000 tokens",
        "type": "retry_3000tokens"
    }
)
print(f"GPT-5 Batch ID: {batch_response.id}")

# Upload and submit gpt-5-mini batch
batch_file = Path("data/retry_batches/gpt_5_mini_retry_3000tokens.jsonl")
with open(batch_file, 'rb') as f:
    file_response = client.files.create(file=f, purpose="batch")

batch_response = client.batches.create(
    input_file_id=file_response.id,
    endpoint="/v1/chat/completions",
    completion_window="24h",
    metadata={
        "model": "gpt-5-mini",
        "description": "Retry token limit failures - gpt-5-mini - 3000 tokens",
        "type": "retry_3000tokens"
    }
)
print(f"GPT-5-mini Batch ID: {batch_response.id}")
```

## Check Batch Status

After submission, check status:

```python
import openai
import os

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Replace with your batch IDs
batch_id = "your-batch-id-here"
batch = client.batches.retrieve(batch_id)
print(f"Status: {batch.status}")
print(f"Request counts: {batch.request_counts}")
```

## Download Results

When batches are complete (status = "completed"):

```python
batch = client.batches.retrieve(batch_id)
output_file_id = batch.output_file_id

# Download results
file_response = client.files.content(output_file_id)
with open("retry_results.jsonl", "wb") as f:
    f.write(file_response.read())
```

