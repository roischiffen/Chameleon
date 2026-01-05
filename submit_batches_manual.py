#!/usr/bin/env python3
"""
Manual batch submission script - run this directly.
"""

import openai
import os
import sys
from pathlib import Path

# Load environment variables from .env file if it exists
def load_env_file(env_path: Path):
    """Load environment variables from .env file."""
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

# Try to load .env file
env_path = Path(__file__).parent / "venv" / "bin" / ".env"
load_env_file(env_path)

# Also try root .env file
root_env = Path(__file__).parent / ".env"
load_env_file(root_env)

# Get API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("❌ Error: OPENAI_API_KEY not set")
    print("   Set it with: export OPENAI_API_KEY='your-key-here'")
    print("   Or ensure venv/bin/.env contains OPENAI_API_KEY=...")
    sys.exit(1)

client = openai.OpenAI(api_key=api_key)

BATCH_DIR = Path(__file__).parent / "data" / "retry_batches"

print("="*80)
print("SUBMITTING RETRY BATCHES")
print("="*80)

# Submit gpt-5 batch
gpt5_file = BATCH_DIR / "gpt_5_retry_3000tokens.jsonl"
if gpt5_file.exists():
    print(f"\n📤 Uploading {gpt5_file.name}...")
    with open(gpt5_file, 'rb') as f:
        file_response = client.files.create(file=f, purpose="batch")
    
    print(f"   ✅ File uploaded: {file_response.id}")
    
    print(f"\n🔄 Creating batch job for gpt-5...")
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
    print(f"   ✅ GPT-5 Batch ID: {batch_response.id}")
    print(f"   💰 This batch qualifies for 50% discount!")
else:
    print(f"\n⚠️  {gpt5_file.name} not found")

# Submit gpt-5-mini batch
gpt5mini_file = BATCH_DIR / "gpt_5_mini_retry_3000tokens.jsonl"
if gpt5mini_file.exists():
    print(f"\n📤 Uploading {gpt5mini_file.name}...")
    with open(gpt5mini_file, 'rb') as f:
        file_response = client.files.create(file=f, purpose="batch")
    
    print(f"   ✅ File uploaded: {file_response.id}")
    
    print(f"\n🔄 Creating batch job for gpt-5-mini...")
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
    print(f"   ✅ GPT-5-mini Batch ID: {batch_response.id}")
    print(f"   💰 This batch qualifies for 50% discount!")
else:
    print(f"\n⚠️  {gpt5mini_file.name} not found")

print("\n" + "="*80)
print("✅ Submission complete!")
print("="*80)

