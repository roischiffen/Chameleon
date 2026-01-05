#!/usr/bin/env python3
"""
Submit retry batch files to OpenAI Batch API.
"""

import os
import sys
from pathlib import Path

try:
    import openai
except ImportError:
    print("❌ Error: openai package not installed")
    print("   Install with: pip install openai")
    sys.exit(1)

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

# Paths
BATCH_DIR = Path(__file__).parent / "data" / "retry_batches"

MODELS = {
    "gpt_5": "gpt-5",
    "gpt_5_mini": "gpt-5-mini",
}


def get_client() -> openai.OpenAI:
    """Get OpenAI client."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        sys.exit(1)
    return openai.OpenAI(api_key=api_key)


def upload_batch_file(client: openai.OpenAI, batch_file: Path) -> str:
    """Upload batch file to OpenAI and return file ID."""
    print(f"\n📤 Uploading {batch_file.name}...")
    
    with open(batch_file, 'rb') as f:
        file_response = client.files.create(
            file=f,
            purpose="batch"
        )
    
    file_id = file_response.id
    print(f"   ✅ File uploaded: {file_id}")
    return file_id


def create_batch(client: openai.OpenAI, file_id: str, model: str, batch_file: Path) -> str:
    """Create batch job and return batch ID."""
    print(f"\n🔄 Creating batch job for {model}...")
    
    batch_response = client.batches.create(
        input_file_id=file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "model": model,
            "description": f"Retry token limit failures - {model} - 3000 tokens",
            "type": "retry_3000tokens"
        }
    )
    
    batch_id = batch_response.id
    print(f"   ✅ Batch created: {batch_id}")
    print(f"   💰 This batch qualifies for 50% discount!")
    
    return batch_id


def submit_batch(client: openai.OpenAI, batch_file: Path) -> str:
    """Submit a single batch file."""
    model_name = batch_file.stem.replace("_retry_3000tokens", "").replace("_", "-")
    model_display = MODELS.get(batch_file.stem.replace("_retry_3000tokens", ""), model_name)
    
    print(f"\n{'='*80}")
    print(f"Processing: {batch_file.name}")
    print(f"Model: {model_display}")
    print(f"{'='*80}")
    
    # Count requests
    with open(batch_file, 'r') as f:
        request_count = sum(1 for _ in f)
    
    print(f"   Requests: {request_count}")
    
    # Upload file
    file_id = upload_batch_file(client, batch_file)
    
    # Create batch
    batch_id = create_batch(client, file_id, model_display, batch_file)
    
    return batch_id


def main():
    print("="*80)
    print("SUBMITTING RETRY BATCHES TO OPENAI")
    print("="*80)
    
    # Check batch directory exists
    if not BATCH_DIR.exists():
        print(f"❌ Error: Batch directory not found: {BATCH_DIR}")
        sys.exit(1)
    
    # Find batch files
    batch_files = sorted(BATCH_DIR.glob("*_retry_3000tokens.jsonl"))
    
    if not batch_files:
        print(f"❌ Error: No batch files found in {BATCH_DIR}")
        sys.exit(1)
    
    print(f"\n📋 Found {len(batch_files)} batch file(s):")
    for bf in batch_files:
        print(f"   - {bf.name}")
    
    # Get client
    client = get_client()
    
    # Submit each batch
    batch_ids = {}
    
    for batch_file in batch_files:
        try:
            batch_id = submit_batch(client, batch_file)
            model_key = batch_file.stem.replace("_retry_3000tokens", "")
            batch_ids[model_key] = batch_id
        except Exception as e:
            print(f"\n❌ Error submitting {batch_file.name}: {e}")
            continue
    
    # Summary
    print(f"\n{'='*80}")
    print("SUBMISSION SUMMARY")
    print(f"{'='*80}")
    
    if batch_ids:
        print("\n✅ Successfully submitted batches:")
        for model_key, batch_id in batch_ids.items():
            model_display = MODELS.get(model_key, model_key)
            print(f"   {model_display}: {batch_id}")
        
        print("\n📋 Next steps:")
        print("   1. Monitor batch status:")
        print("      client.batches.retrieve(batch_id)")
        print("   2. Download results when complete:")
        print("      client.batches.retrieve(batch_id).output_file_id")
        print("   3. Check status:")
        print("      python3 check_batch_status.py")
    else:
        print("\n❌ No batches were successfully submitted")
    
    print("="*80)


if __name__ == "__main__":
    main()

