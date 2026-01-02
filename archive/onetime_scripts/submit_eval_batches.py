#!/usr/bin/env python3
"""
Submit Evaluation Batches to OpenAI Batch API

This script submits JSONL files to OpenAI Batch API for GPT-5 evaluation
and tracks batch submissions.

Usage:
    # Submit all batches
    python omnimath_distortion_workflow/flows/submit_eval_batches.py submit
    
    # Submit a single batch
    python omnimath_distortion_workflow/flows/submit_eval_batches.py submit --batch eval_batch1.jsonl
    
    # Check status of all submitted batches
    python omnimath_distortion_workflow/flows/submit_eval_batches.py status
    
    # Download results for completed batches
    python omnimath_distortion_workflow/flows/submit_eval_batches.py download

Environment:
    OPENAI_API_KEY: Your OpenAI API key (required)
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.gpt5_batch_processor import GPT5BatchProcessor


# Paths
EVAL_BATCHES_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "batches"
EVAL_RESULTS_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "results"
TRACKING_FILE = project_root / "omnimath_distortion_workflow" / "evaluation" / "batch_tracking.json"


def load_tracking() -> Dict:
    """Load the batch tracking file."""
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    return {"submissions": []}


def save_tracking(tracking: Dict) -> None:
    """Save the batch tracking file."""
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking, f, indent=2)
    print(f"  📝 Tracking saved to: {TRACKING_FILE}")


def get_api_key() -> str:
    """Get OpenAI API key from environment."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    return api_key


def submit_batches(batch_files: Optional[List[str]] = None) -> None:
    """Submit batches to OpenAI Batch API."""
    
    print("=" * 60)
    print("OmniMath Batch Submission")
    print("=" * 60)
    
    # Get API key
    api_key = get_api_key()
    processor = GPT5BatchProcessor(api_key)
    
    # Find batch files to submit
    if batch_files:
        # Submit specific batches
        jsonl_files = [EVAL_BATCHES_DIR / bf for bf in batch_files]
    else:
        # Submit all batches
        jsonl_files = sorted(EVAL_BATCHES_DIR.glob("*.jsonl"))
    
    if not jsonl_files:
        print(f"❌ No JSONL files found in {EVAL_BATCHES_DIR}")
        return
    
    print(f"\nFound {len(jsonl_files)} batch file(s) to submit:")
    for f in jsonl_files:
        print(f"  - {f.name}")
    
    # Load existing tracking
    tracking = load_tracking()
    submitted_files = {s["batch_file"] for s in tracking["submissions"]}
    
    # Submit each batch
    print("\n" + "-" * 60)
    print("SUBMITTING BATCHES")
    print("-" * 60)
    
    for jsonl_file in jsonl_files:
        filename = jsonl_file.name
        
        # Check if already submitted
        if filename in submitted_files:
            # Find existing submission
            existing = next(s for s in tracking["submissions"] if s["batch_file"] == filename)
            print(f"\n⏭️  {filename}: Already submitted")
            print(f"   Batch ID: {existing['batch_id']}")
            print(f"   Status: {existing['status']}")
            continue
        
        print(f"\n📤 Submitting: {filename}")
        
        try:
            # Submit batch
            description = f"OmniMath Evaluation - {filename}"
            batch_id = processor.submit_batch(str(jsonl_file), description)
            
            # Record submission
            submission = {
                "batch_file": filename,
                "batch_id": batch_id,
                "submitted_at": datetime.now().isoformat(),
                "status": "submitted",
                "completed_at": None,
                "results_file": None
            }
            tracking["submissions"].append(submission)
            save_tracking(tracking)
            
            print(f"   ✅ Submitted successfully!")
            print(f"   Batch ID: {batch_id}")
            
        except Exception as e:
            print(f"   ❌ Failed to submit: {e}")
    
    print("\n" + "=" * 60)
    print("Submission complete. Use 'status' command to check progress.")
    print("=" * 60)


def check_status() -> None:
    """Check status of all submitted batches."""
    
    print("=" * 60)
    print("OmniMath Batch Status")
    print("=" * 60)
    
    # Load tracking
    tracking = load_tracking()
    
    if not tracking["submissions"]:
        print("\n❌ No batches have been submitted yet.")
        print("   Run: python submit_eval_batches.py submit")
        return
    
    # Get API key
    api_key = get_api_key()
    processor = GPT5BatchProcessor(api_key)
    
    print(f"\nTracking {len(tracking['submissions'])} batch(es):\n")
    
    updated = False
    for submission in tracking["submissions"]:
        filename = submission["batch_file"]
        batch_id = submission["batch_id"]
        
        print(f"📋 {filename}")
        print(f"   Batch ID: {batch_id}")
        print(f"   Submitted: {submission['submitted_at']}")
        
        try:
            status_info = processor.check_batch_status(batch_id)
            
            if status_info:
                new_status = status_info["status"]
                
                # Update tracking if status changed
                if new_status != submission["status"]:
                    submission["status"] = new_status
                    updated = True
                
                print(f"   Status: {new_status}")
                
                if status_info.get("request_counts"):
                    counts = status_info["request_counts"]
                    if counts.get("total"):
                        progress = (counts.get("completed", 0) / counts["total"]) * 100
                        print(f"   Progress: {counts.get('completed', 0)}/{counts['total']} ({progress:.1f}%)")
                
                if new_status == "completed" and not submission.get("completed_at"):
                    submission["completed_at"] = datetime.now().isoformat()
                    updated = True
                    
        except Exception as e:
            print(f"   ⚠️  Error checking status: {e}")
        
        print()
    
    if updated:
        save_tracking(tracking)
    
    # Summary
    print("-" * 60)
    statuses = {}
    for s in tracking["submissions"]:
        status = s["status"]
        statuses[status] = statuses.get(status, 0) + 1
    
    print("Summary:")
    for status, count in sorted(statuses.items()):
        emoji = {"completed": "✅", "in_progress": "🔄", "submitted": "📤", "failed": "❌"}.get(status, "❓")
        print(f"  {emoji} {status}: {count}")


def download_results() -> None:
    """Download results for completed batches."""
    
    print("=" * 60)
    print("OmniMath Results Download")
    print("=" * 60)
    
    # Load tracking
    tracking = load_tracking()
    
    if not tracking["submissions"]:
        print("\n❌ No batches have been submitted yet.")
        return
    
    # Get API key
    api_key = get_api_key()
    processor = GPT5BatchProcessor(api_key)
    
    # Create results directory
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find completed batches without downloaded results
    completed = [s for s in tracking["submissions"] 
                 if s["status"] == "completed" and not s.get("results_file")]
    
    if not completed:
        print("\n⏳ No completed batches ready for download.")
        print("   Batches with results already downloaded are skipped.")
        return
    
    print(f"\nFound {len(completed)} completed batch(es) to download:\n")
    
    updated = False
    for submission in completed:
        filename = submission["batch_file"]
        batch_id = submission["batch_id"]
        
        # Generate output filename
        base_name = filename.replace(".jsonl", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = EVAL_RESULTS_DIR / f"{base_name}_results_{timestamp}.jsonl"
        
        print(f"📥 Downloading: {filename}")
        print(f"   Batch ID: {batch_id}")
        
        try:
            result_path = processor.download_results(batch_id, str(output_file))
            
            if result_path:
                submission["results_file"] = str(output_file)
                submission["downloaded_at"] = datetime.now().isoformat()
                updated = True
                print(f"   ✅ Saved to: {output_file}")
            else:
                print(f"   ⚠️  Download returned None")
                
        except Exception as e:
            print(f"   ❌ Error downloading: {e}")
        
        print()
    
    if updated:
        save_tracking(tracking)
    
    print("=" * 60)
    print("Download complete.")
    print("=" * 60)


def show_tracking() -> None:
    """Display current tracking information."""
    
    print("=" * 60)
    print("OmniMath Batch Tracking Info")
    print("=" * 60)
    
    tracking = load_tracking()
    
    if not tracking["submissions"]:
        print("\n❌ No batches tracked yet.")
        return
    
    print(f"\nTracking file: {TRACKING_FILE}")
    print(f"Total batches: {len(tracking['submissions'])}\n")
    
    for submission in tracking["submissions"]:
        print(f"📋 {submission['batch_file']}")
        print(f"   Batch ID: {submission['batch_id']}")
        print(f"   Status: {submission['status']}")
        print(f"   Submitted: {submission['submitted_at']}")
        if submission.get("completed_at"):
            print(f"   Completed: {submission['completed_at']}")
        if submission.get("results_file"):
            print(f"   Results: {submission['results_file']}")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Submit and manage OmniMath evaluation batches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  submit    Submit JSONL batches to OpenAI Batch API
  status    Check status of submitted batches
  download  Download results for completed batches
  tracking  Show tracking information

Examples:
  %(prog)s submit                    # Submit all batches
  %(prog)s submit --batch eval_batch1.jsonl  # Submit specific batch
  %(prog)s status                    # Check all batch statuses
  %(prog)s download                  # Download completed results
        """
    )
    
    parser.add_argument(
        "command",
        choices=["submit", "status", "download", "tracking"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--batch",
        action="append",
        help="Specific batch file(s) to submit (can be used multiple times)"
    )
    
    args = parser.parse_args()
    
    if args.command == "submit":
        submit_batches(args.batch)
    elif args.command == "status":
        check_status()
    elif args.command == "download":
        download_results()
    elif args.command == "tracking":
        show_tracking()


if __name__ == "__main__":
    main()

