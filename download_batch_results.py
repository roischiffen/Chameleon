#!/usr/bin/env python3
"""
Download completed batch results from OpenAI.

Usage:
    python download_batch_results.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_paths = [
        Path(".env"),
        Path("venv/bin/.env"),
        Path.home() / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"📁 Loaded .env from: {env_path}")
            break
except ImportError:
    pass

try:
    import openai
except ImportError:
    print("❌ Error: openai package not installed")
    print("   Install with: pip install openai")
    sys.exit(1)

# Paths
TRACKING_FILE = Path("data/batch_tracking.json")
RESULTS_DIR = Path("data/results_verified")

def get_client():
    """Get OpenAI client."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    return openai.OpenAI(api_key=api_key)

def load_tracking():
    """Load batch tracking data."""
    if not TRACKING_FILE.exists():
        print("❌ No tracking file found at data/batch_tracking.json")
        sys.exit(1)
    
    with open(TRACKING_FILE, 'r') as f:
        return json.load(f)

def save_tracking(tracking):
    """Save batch tracking data."""
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking, f, indent=2)

def download_results():
    """Download all completed batch results."""
    print("\n" + "=" * 70)
    print("  📥 DOWNLOADING BATCH RESULTS")
    print("=" * 70)
    
    # Load tracking
    tracking = load_tracking()
    
    # Get client
    client = get_client()
    
    # Create results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find completed batches without downloaded results
    completed = [s for s in tracking["submissions"]
                 if s["status"] == "completed" and not s.get("results_file")]
    
    if not completed:
        print("\n✅ All completed batches already downloaded!")
        print("\nExisting downloads:")
        for s in tracking["submissions"]:
            if s.get("results_file"):
                print(f"  • {s['model']}: {s['results_file']}")
        return
    
    print(f"\n📦 Found {len(completed)} completed batch(es) to download:\n")
    
    updated = False
    downloaded_count = 0
    
    for submission in completed:
        model = submission["model"]
        batch_id = submission["batch_id"]
        
        print(f"{'─' * 70}")
        print(f"📥 Downloading: {model}")
        print(f"   Batch ID: {batch_id}")
        
        try:
            # Get batch
            batch = client.batches.retrieve(batch_id)
            
            if not batch.output_file_id:
                print(f"   ⚠️  No output file available yet")
                continue
            
            # Download results
            print(f"   Downloading from OpenAI...")
            file_response = client.files.content(batch.output_file_id)
            
            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_safe = model.replace(".", "_")
            results_file = RESULTS_DIR / f"{model_safe}_results_{timestamp}.jsonl"
            
            with open(results_file, 'wb') as f:
                f.write(file_response.content)
            
            print(f"   ✅ Saved: {results_file.name}")
            
            # Count results
            with open(results_file, 'r') as f:
                result_count = sum(1 for _ in f)
            print(f"   Results: {result_count} responses")
            
            # Update tracking
            submission["results_file"] = str(results_file)
            submission["downloaded_at"] = datetime.now().isoformat()
            updated = True
            downloaded_count += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    if updated:
        save_tracking(tracking)
    
    print("=" * 70)
    print(f"  ✅ Downloaded {downloaded_count} batch result(s)!")
    print(f"  📁 Results saved to: {RESULTS_DIR}/")
    print("=" * 70 + "\n")
    
    # Show all results
    print("All downloaded results:")
    for s in tracking["submissions"]:
        if s.get("results_file"):
            print(f"  • {s['model']:12} → {Path(s['results_file']).name}")

if __name__ == "__main__":
    download_results()

