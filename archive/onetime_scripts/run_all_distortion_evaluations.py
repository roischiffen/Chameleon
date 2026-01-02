#!/usr/bin/env python3
"""
Master Script: Run All Distortion Evaluations

Coordinates evaluation of both models (GPT-4o and GPT-5-mini/o4-mini) 
on both difficulty levels (1.0 and 1.5) using the Batch API.

This script:
1. Prepares and submits all batches upfront (minimizes total wait time)
2. Monitors all batches in parallel
3. Downloads results as they complete
4. Generates final analysis report

Usage:
    # Prepare and submit all batches
    python run_all_distortion_evaluations.py --submit-all
    
    # Check status of all batches
    python run_all_distortion_evaluations.py --status
    
    # Download all completed results
    python run_all_distortion_evaluations.py --download-all
    
    # Run complete workflow (submit + wait + download + analyze)
    python run_all_distortion_evaluations.py --run-all
    
    # Resume monitoring and downloading
    python run_all_distortion_evaluations.py --resume

Cost Estimate (Batch API - 50% discount):
    - 400 questions per difficulty × 2 difficulties = 800 questions per model
    - 800 questions × 2 models = 1,600 total questions
    - Estimated cost: ~$2-4 (with 50% batch discount)
    
Time Estimate:
    - Batch API typically completes within 1-6 hours
    - All batches run in parallel, so total time ≈ time for slowest batch
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment
try:
    from dotenv import load_dotenv
    env_paths = [
        project_root / ".env",
        project_root / "venv" / "bin" / ".env",  # Your specific .env location
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
    sys.exit(1)

from omnimath_distortion_workflow.flows.evaluate_distortions_batch import (
    prepare_batch,
    submit_batch,
    check_batch_status,
    download_results,
    get_eval_dir,
    load_checkpoint,
    get_client
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# All evaluation combinations
EVALUATIONS = [
    {"model": "gpt-4o", "difficulty": 1.0},
    {"model": "gpt-4o", "difficulty": 1.5},
    {"model": "gpt-5", "difficulty": 1.0},
    {"model": "gpt-5", "difficulty": 1.5},
    {"model": "gpt-5-mini", "difficulty": 1.0},
    {"model": "gpt-5-mini", "difficulty": 1.5},
]

# Polling configuration
STATUS_CHECK_INTERVAL = 60  # seconds
MAX_WAIT_HOURS = 24

# Output directory for master coordination
MASTER_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "distortion_results"


# ============================================================================
# COORDINATION FUNCTIONS
# ============================================================================

def get_master_status_file() -> Path:
    """Get path to master status file."""
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    return MASTER_DIR / "master_status.json"


def load_master_status() -> Dict:
    """Load master status tracking file."""
    status_file = get_master_status_file()
    if status_file.exists():
        with open(status_file, 'r') as f:
            return json.load(f)
    return {
        "evaluations": {},
        "created_at": None,
        "updated_at": None
    }


def save_master_status(status: Dict):
    """Save master status tracking file."""
    status["updated_at"] = datetime.now().isoformat()
    with open(get_master_status_file(), 'w') as f:
        json.dump(status, f, indent=2)


def get_eval_key(model: str, difficulty: float) -> str:
    """Get unique key for an evaluation."""
    return f"{model}_difficulty_{difficulty}"


def prepare_all_batches(force: bool = False) -> Dict:
    """Prepare batch files for all evaluations."""
    print("\n" + "="*70)
    print("📋 PREPARING ALL BATCH FILES")
    print("="*70)
    
    master_status = load_master_status()
    if master_status["created_at"] is None:
        master_status["created_at"] = datetime.now().isoformat()
    
    results = {}
    
    for eval_config in EVALUATIONS:
        model = eval_config["model"]
        difficulty = eval_config["difficulty"]
        key = get_eval_key(model, difficulty)
        
        print(f"\n📦 Preparing: {model} on difficulty {difficulty}")
        
        try:
            batch_file, request_count = prepare_batch(model, difficulty, force=force)
            
            results[key] = {
                "status": "prepared" if request_count > 0 else "completed",
                "request_count": request_count,
                "batch_file": str(batch_file)
            }
            
            master_status["evaluations"][key] = {
                "model": model,
                "difficulty": difficulty,
                "status": "prepared" if request_count > 0 else "completed",
                "request_count": request_count
            }
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[key] = {"status": "error", "error": str(e)}
            master_status["evaluations"][key] = {"status": "error", "error": str(e)}
    
    save_master_status(master_status)
    
    # Summary
    print("\n" + "-"*70)
    print("📋 Preparation Summary:")
    for key, result in results.items():
        status = result.get("status", "unknown")
        count = result.get("request_count", 0)
        if status == "prepared":
            print(f"   ✅ {key}: {count} requests ready")
        elif status == "completed":
            print(f"   ⏭️  {key}: Already completed")
        else:
            print(f"   ❌ {key}: {result.get('error', 'Error')}")
    
    return results


def submit_all_batches(client: openai.OpenAI) -> Dict:
    """Submit all prepared batches to OpenAI."""
    print("\n" + "="*70)
    print("🚀 SUBMITTING ALL BATCHES")
    print("="*70)
    
    master_status = load_master_status()
    results = {}
    
    for eval_config in EVALUATIONS:
        model = eval_config["model"]
        difficulty = eval_config["difficulty"]
        key = get_eval_key(model, difficulty)
        
        # Check if already submitted or completed
        eval_dir = get_eval_dir(model, difficulty)
        checkpoint = load_checkpoint(eval_dir)
        
        if checkpoint.get("status") in ["submitted", "processing"]:
            print(f"\n⏭️  {key}: Already submitted (batch_id: {checkpoint.get('batch_id')})")
            results[key] = {"status": "already_submitted", "batch_id": checkpoint.get("batch_id")}
            continue
        
        if checkpoint.get("status") == "completed":
            print(f"\n⏭️  {key}: Already completed")
            results[key] = {"status": "completed"}
            continue
        
        print(f"\n🚀 Submitting: {model} on difficulty {difficulty}")
        
        try:
            batch_id = submit_batch(client, model, difficulty)
            
            if batch_id:
                results[key] = {"status": "submitted", "batch_id": batch_id}
                master_status["evaluations"][key]["status"] = "submitted"
                master_status["evaluations"][key]["batch_id"] = batch_id
            else:
                results[key] = {"status": "no_requests"}
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[key] = {"status": "error", "error": str(e)}
    
    save_master_status(master_status)
    
    # Summary
    print("\n" + "-"*70)
    print("📋 Submission Summary:")
    submitted_count = 0
    for key, result in results.items():
        status = result.get("status", "unknown")
        if status == "submitted":
            print(f"   ✅ {key}: Submitted (batch_id: {result.get('batch_id')})")
            submitted_count += 1
        elif status == "already_submitted":
            print(f"   ⏭️  {key}: Already submitted")
            submitted_count += 1
        elif status == "completed":
            print(f"   ✅ {key}: Already completed")
        else:
            print(f"   ❌ {key}: {result.get('error', status)}")
    
    if submitted_count > 0:
        print(f"\n💰 All batches qualify for 50% discount!")
        print(f"⏳ Batches will complete within 1-24 hours")
    
    return results


def check_all_statuses(client: openai.OpenAI) -> Dict:
    """Check status of all batches."""
    print("\n" + "="*70)
    print("📊 CHECKING ALL BATCH STATUSES")
    print("="*70)
    
    statuses = {}
    all_completed = True
    
    for eval_config in EVALUATIONS:
        model = eval_config["model"]
        difficulty = eval_config["difficulty"]
        key = get_eval_key(model, difficulty)
        
        eval_dir = get_eval_dir(model, difficulty)
        checkpoint = load_checkpoint(eval_dir)
        
        batch_id = checkpoint.get("batch_id")
        
        print(f"\n📋 {key}:")
        
        if not batch_id:
            if checkpoint.get("status") == "results_downloaded":
                print(f"   ✅ Completed and downloaded")
                statuses[key] = {"status": "completed"}
            else:
                print(f"   ⚪ Not started")
                statuses[key] = {"status": "not_started"}
                all_completed = False
            continue
        
        try:
            status = check_batch_status(client, model, difficulty, wait=False)
            statuses[key] = status
            
            if status.get("status") not in ["completed", "results_downloaded"]:
                all_completed = False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            statuses[key] = {"status": "error", "error": str(e)}
            all_completed = False
    
    print("\n" + "-"*70)
    print(f"📋 Status Summary: {'All completed!' if all_completed else 'Still processing...'}")
    
    return statuses


def download_all_results(client: openai.OpenAI) -> Dict:
    """Download results from all completed batches."""
    print("\n" + "="*70)
    print("📥 DOWNLOADING ALL RESULTS")
    print("="*70)
    
    results = {}
    
    for eval_config in EVALUATIONS:
        model = eval_config["model"]
        difficulty = eval_config["difficulty"]
        key = get_eval_key(model, difficulty)
        
        eval_dir = get_eval_dir(model, difficulty)
        checkpoint = load_checkpoint(eval_dir)
        
        # Check if already downloaded
        if checkpoint.get("status") == "results_downloaded":
            print(f"\n⏭️  {key}: Already downloaded")
            results[key] = {"status": "already_downloaded"}
            continue
        
        # Check if completed
        if checkpoint.get("status") != "completed":
            print(f"\n⏭️  {key}: Not completed yet (status: {checkpoint.get('status')})")
            results[key] = {"status": "not_ready"}
            continue
        
        print(f"\n📥 Downloading: {model} on difficulty {difficulty}")
        
        try:
            count = download_results(client, model, difficulty)
            results[key] = {"status": "downloaded", "count": count}
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[key] = {"status": "error", "error": str(e)}
    
    return results


def wait_for_all_batches(client: openai.OpenAI, max_hours: float = MAX_WAIT_HOURS):
    """Wait for all batches to complete, downloading as they finish."""
    print("\n" + "="*70)
    print("⏳ WAITING FOR ALL BATCHES TO COMPLETE")
    print("="*70)
    print(f"   Checking every {STATUS_CHECK_INTERVAL} seconds")
    print(f"   Max wait time: {max_hours} hours")
    print(f"   Press Ctrl+C to exit (progress is saved)")
    
    start_time = time.time()
    max_seconds = max_hours * 3600
    
    while True:
        elapsed = time.time() - start_time
        elapsed_mins = elapsed / 60
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking statuses... (elapsed: {elapsed_mins:.1f}m)")
        
        all_done = True
        
        for eval_config in EVALUATIONS:
            model = eval_config["model"]
            difficulty = eval_config["difficulty"]
            key = get_eval_key(model, difficulty)
            
            eval_dir = get_eval_dir(model, difficulty)
            checkpoint = load_checkpoint(eval_dir)
            
            current_status = checkpoint.get("status", "unknown")
            
            if current_status == "results_downloaded":
                print(f"   ✅ {key}: Done")
                continue
            
            if current_status == "completed":
                print(f"   📥 {key}: Downloading...")
                try:
                    download_results(client, model, difficulty)
                    print(f"      ✅ Downloaded!")
                except Exception as e:
                    print(f"      ❌ Error: {e}")
                    all_done = False
                continue
            
            if not checkpoint.get("batch_id"):
                print(f"   ⚪ {key}: Not submitted")
                all_done = False
                continue
            
            # Check batch status
            try:
                status = check_batch_status(client, model, difficulty, wait=False)
                batch_status = status.get("status", "unknown")
                progress = status.get("completed", 0)
                total = status.get("total", 0)
                
                if batch_status == "completed":
                    print(f"   📥 {key}: Completed! Downloading...")
                    download_results(client, model, difficulty)
                    print(f"      ✅ Downloaded!")
                else:
                    pct = progress / total * 100 if total > 0 else 0
                    print(f"   🔄 {key}: {batch_status} ({progress}/{total}, {pct:.0f}%)")
                    all_done = False
                    
            except Exception as e:
                print(f"   ⚠️  {key}: Error checking - {e}")
                all_done = False
        
        if all_done:
            print("\n✅ All batches completed and downloaded!")
            break
        
        if elapsed > max_seconds:
            print(f"\n⏰ Max wait time reached. Some batches still processing.")
            break
        
        print(f"\n   Waiting {STATUS_CHECK_INTERVAL}s before next check...")
        time.sleep(STATUS_CHECK_INTERVAL)


def run_analysis():
    """Run analysis on all completed evaluations."""
    print("\n" + "="*70)
    print("📊 RUNNING ANALYSIS ON ALL RESULTS")
    print("="*70)
    
    from omnimath_distortion_workflow.flows.analyze_distortion_results import (
        load_distortion_results,
        load_baseline_results,
        analyze_results,
        compare_with_baseline,
        generate_console_report,
        save_analysis
    )
    
    for eval_config in EVALUATIONS:
        model = eval_config["model"]
        difficulty = eval_config["difficulty"]
        
        print(f"\n{'='*50}")
        print(f"Analyzing: {model} on difficulty {difficulty}")
        print(f"{'='*50}")
        
        results = load_distortion_results(model, difficulty)
        
        if not results:
            print(f"   ⚠️  No results found")
            continue
        
        stats = analyze_results(results)
        
        # Try to load baseline for comparison
        baseline = load_baseline_results(model)
        comparison = None
        if baseline:
            comparison = compare_with_baseline(results, baseline, difficulty)
        
        generate_console_report(model, difficulty, stats, comparison)
        save_analysis(model, difficulty, stats, comparison)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Coordinate all distortion evaluations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full workflow: prepare + submit + wait + download + analyze
  %(prog)s --run-all
  
  # Step by step:
  %(prog)s --prepare-all
  %(prog)s --submit-all
  %(prog)s --status
  %(prog)s --wait
  %(prog)s --download-all
  %(prog)s --analyze
  
  # Resume monitoring
  %(prog)s --resume
        """
    )
    
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare-all", action="store_true",
                       help="Prepare all batch files")
    action.add_argument("--submit-all", action="store_true",
                       help="Submit all batches to OpenAI")
    action.add_argument("--status", action="store_true",
                       help="Check status of all batches")
    action.add_argument("--wait", action="store_true",
                       help="Wait for all batches to complete")
    action.add_argument("--download-all", action="store_true",
                       help="Download all completed results")
    action.add_argument("--analyze", action="store_true",
                       help="Run analysis on all results")
    action.add_argument("--run-all", action="store_true",
                       help="Run complete workflow")
    action.add_argument("--resume", action="store_true",
                       help="Resume from current state")
    
    parser.add_argument("--force", action="store_true",
                       help="Force recreate batch files")
    
    args = parser.parse_args()
    
    print("="*70)
    print("🚀 OmniMath Distortion Evaluation - Master Controller")
    print("="*70)
    print(f"\n📋 Evaluations to run:")
    for eval_config in EVALUATIONS:
        print(f"   • {eval_config['model']} on difficulty {eval_config['difficulty']}")
    
    client = None
    if not args.prepare_all:
        client = get_client()
    
    try:
        if args.prepare_all:
            prepare_all_batches(force=args.force)
        
        elif args.submit_all:
            prepare_all_batches(force=args.force)
            submit_all_batches(client)
        
        elif args.status:
            check_all_statuses(client)
        
        elif args.wait:
            wait_for_all_batches(client)
        
        elif args.download_all:
            download_all_results(client)
        
        elif args.analyze:
            run_analysis()
        
        elif args.run_all:
            print("\n🚀 Starting complete evaluation workflow...")
            
            # Step 1: Prepare
            prepare_all_batches(force=args.force)
            
            # Step 2: Submit
            submit_all_batches(client)
            
            # Step 3: Wait and download
            wait_for_all_batches(client)
            
            # Step 4: Analyze
            run_analysis()
            
            print("\n" + "="*70)
            print("✅ ALL EVALUATIONS COMPLETE!")
            print("="*70)
        
        elif args.resume:
            print("\n📋 Resuming from current state...")
            
            # Check what needs to be done
            statuses = check_all_statuses(client)
            
            # Submit any prepared but not submitted
            pending_submit = False
            for eval_config in EVALUATIONS:
                key = get_eval_key(eval_config["model"], eval_config["difficulty"])
                eval_dir = get_eval_dir(eval_config["model"], eval_config["difficulty"])
                checkpoint = load_checkpoint(eval_dir)
                if checkpoint.get("status") == "prepared":
                    pending_submit = True
                    break
            
            if pending_submit:
                submit_all_batches(client)
            
            # Wait and download
            wait_for_all_batches(client)
            
            # Analyze
            run_analysis()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted. All progress saved.")
        print("   Run --resume to continue.")


if __name__ == "__main__":
    main()
