#!/usr/bin/env python3
"""
Mistral Batch API Evaluation Script (50% Cost Savings)

Evaluates Mistral Large 3 on distorted questions using the Batch API.
Similar to OpenAI's Batch API - submit all requests at once, get 50% discount.

Key Features:
- 50% cost savings via Batch API
- Robust checkpointing
- Resume from interruptions
- Submit all 800 questions at once

Usage:
    # Step 1: Prepare batch file
    python evaluate_mistral_batch.py --prepare
    
    # Step 2: Submit batch
    python evaluate_mistral_batch.py --submit
    
    # Step 3: Check status
    python evaluate_mistral_batch.py --status
    
    # Step 4: Download results
    python evaluate_mistral_batch.py --download
    
    # Or do everything at once
    python evaluate_mistral_batch.py --run

Environment:
    MISTRAL_API_KEY: Your Mistral API key (required)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
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

# Try to import Mistral SDK
try:
    from mistralai import Mistral
except ImportError:
    print("❌ Error: mistralai package not installed")
    print("   Install with: pip install mistralai")
    sys.exit(1)

from omnimath_distortion_workflow.modules.evaluation_prompt import (
    create_evaluation_prompt,
    generate_custom_id,
    parse_custom_id,
)
from omnimath_distortion_workflow.modules.answer_comparator import compare_answers

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = project_root / "omnimath_distortion_workflow" / "data" / "by_difficulty"
EVAL_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "distortion_results"

# Model configuration - Mistral Large 3 (flagship)
MODEL_ID = "mistral-large-latest"  # or "mistral-large-2512" for specific version

# Polling configuration
POLL_INTERVAL_SECONDS = 30
MAX_POLL_HOURS = 24


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client() -> Mistral:
    """Initialize Mistral client."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("❌ Error: MISTRAL_API_KEY not set")
        print("   Make sure it's in your .env file")
        sys.exit(1)
    
    return Mistral(api_key=api_key)


def get_eval_dir() -> Path:
    """Get evaluation directory for Mistral."""
    model_name = MODEL_ID.replace("-", "_")
    eval_dir = EVAL_DIR / f"{model_name}_all_difficulties"
    eval_dir.mkdir(parents=True, exist_ok=True)
    return eval_dir


def load_distortions(difficulty: float) -> List[Dict]:
    """Load distorted questions for a difficulty level."""
    if difficulty == int(difficulty):
        diff_str = f"difficulty_{int(difficulty)}"
    else:
        diff_str = f"difficulty_{difficulty}"
    
    diff_dir = DATA_DIR / diff_str
    distortions_file = diff_dir / f"{diff_str}_distortions.json"
    
    if not distortions_file.exists():
        raise FileNotFoundError(f"Distortions file not found: {distortions_file}")
    
    with open(distortions_file, 'r') as f:
        all_entries = json.load(f)
    
    distortions = []
    
    for entry in all_entries:
        if 'miu' in entry and entry.get('miu') is not None:
            entry['source_difficulty'] = difficulty
            distortions.append(entry)
        elif 'distortions' in entry and isinstance(entry['distortions'], list):
            for dist in entry['distortions']:
                if 'miu' in dist and 'distorted_question' in dist:
                    flat_entry = {
                        'question_id': entry.get('question_id'),
                        'original_question': entry.get('original_question'),
                        'correct_answer': entry.get('correct_answer'),
                        'difficulty': entry.get('difficulty'),
                        'difficulty_category': entry.get('difficulty_category', 'easy'),
                        'domain': entry.get('domain', ''),
                        'distorted_question': dist.get('distorted_question'),
                        'miu': dist.get('miu'),
                        'miu_description': dist.get('miu_description', ''),
                        'source_difficulty': difficulty,
                    }
                    distortions.append(flat_entry)
    
    return distortions


def load_all_distortions() -> List[Dict]:
    """Load all distortions from both difficulty levels."""
    all_distortions = []
    
    for difficulty in [1.0, 1.5]:
        distortions = load_distortions(difficulty)
        all_distortions.extend(distortions)
        print(f"   Loaded {len(distortions)} from difficulty {difficulty}")
    
    return all_distortions


def load_checkpoint(eval_dir: Path) -> Dict:
    """Load checkpoint data."""
    checkpoint_file = eval_dir / "checkpoint.json"
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return {
        "status": "not_started",
        "batch_job_id": None,
        "input_file_id": None,
        "output_file_id": None,
        "completed_ids": [],
        "created_at": None,
        "updated_at": None
    }


def save_checkpoint(eval_dir: Path, checkpoint: Dict):
    """Save checkpoint data."""
    checkpoint["updated_at"] = datetime.now().isoformat()
    checkpoint_file = eval_dir / "checkpoint.json"
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)


def load_results(eval_dir: Path) -> List[Dict]:
    """Load existing results."""
    results_file = eval_dir / "results.jsonl"
    results = []
    if results_file.exists():
        with open(results_file, 'r') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    return results


def append_results(eval_dir: Path, new_results: List[Dict]):
    """Append new results."""
    results_file = eval_dir / "results.jsonl"
    with open(results_file, 'a') as f:
        for result in new_results:
            f.write(json.dumps(result) + '\n')


# ============================================================================
# BATCH API FUNCTIONS
# ============================================================================

def create_batch_request(question_data: Dict) -> Dict:
    """Create a single batch request for Mistral Batch API."""
    custom_id = generate_custom_id(question_data["question_id"], question_data["miu"])
    prompt = create_evaluation_prompt(question_data["distorted_question"])
    
    # Mistral batch format
    return {
        "custom_id": custom_id,
        "body": {
            "max_tokens": 150,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    }


def prepare_batch(force: bool = False) -> tuple:
    """Prepare batch file for Mistral Batch API."""
    eval_dir = get_eval_dir()
    checkpoint = load_checkpoint(eval_dir)
    
    batch_file = eval_dir / "batch_requests.jsonl"
    
    if batch_file.exists() and not force:
        if checkpoint["status"] not in ["not_started", "failed"]:
            print(f"⚠️  Batch already prepared. Use --force to recreate.")
            with open(batch_file, 'r') as f:
                count = sum(1 for _ in f)
            return batch_file, count
    
    print(f"\n📋 Preparing batch for {MODEL_ID}...")
    
    # Load all distortions
    all_distortions = load_all_distortions()
    print(f"   Total distortions: {len(all_distortions)}")
    
    # Load completed IDs to skip
    completed_ids = set(checkpoint.get("completed_ids", []))
    existing_results = load_results(eval_dir)
    for result in existing_results:
        if result.get("custom_id"):
            completed_ids.add(result["custom_id"])
    
    # Create batch requests
    requests = []
    skipped = 0
    
    for dist in all_distortions:
        custom_id = generate_custom_id(dist["question_id"], dist["miu"])
        
        if custom_id in completed_ids:
            skipped += 1
            continue
        
        request = create_batch_request(dist)
        requests.append(request)
    
    if skipped > 0:
        print(f"   ⏭️  Skipped {skipped} already completed questions")
    
    if not requests:
        print("   ✅ All questions already completed!")
        return batch_file, 0
    
    # Write batch file
    with open(batch_file, 'w') as f:
        for req in requests:
            f.write(json.dumps(req) + '\n')
    
    # Update checkpoint
    checkpoint["status"] = "prepared"
    checkpoint["created_at"] = datetime.now().isoformat()
    checkpoint["request_count"] = len(requests)
    save_checkpoint(eval_dir, checkpoint)
    
    print(f"   ✅ Created batch file with {len(requests)} requests")
    print(f"   📁 File: {batch_file}")
    
    return batch_file, len(requests)


def submit_batch(client: Mistral) -> str:
    """Submit batch to Mistral Batch API."""
    eval_dir = get_eval_dir()
    checkpoint = load_checkpoint(eval_dir)
    
    if checkpoint.get("batch_job_id") and checkpoint["status"] in ["submitted", "processing"]:
        print(f"⚠️  Batch already submitted: {checkpoint['batch_job_id']}")
        return checkpoint["batch_job_id"]
    
    batch_file = eval_dir / "batch_requests.jsonl"
    if not batch_file.exists():
        raise FileNotFoundError("Batch file not found. Run --prepare first.")
    
    with open(batch_file, 'r') as f:
        request_count = sum(1 for _ in f)
    
    if request_count == 0:
        print("   ✅ No requests to submit")
        return None
    
    print(f"\n🚀 Submitting batch to Mistral...")
    print(f"   Requests: {request_count}")
    
    # Upload batch file
    print("   📤 Uploading batch file...")
    with open(batch_file, 'rb') as f:
        file_response = client.files.upload(
            file={"file_name": "batch_requests.jsonl", "content": f},
            purpose="batch"
        )
    file_id = file_response.id
    print(f"   ✅ File uploaded: {file_id}")
    
    # Create batch job
    print("   🔄 Creating batch job...")
    batch_job = client.batch.jobs.create(
        input_files=[file_id],
        model=MODEL_ID,
        endpoint="/v1/chat/completions",
        metadata={"description": "OmniMath distortion evaluation"}
    )
    job_id = batch_job.id
    
    print(f"   ✅ Batch job created: {job_id}")
    print(f"   💰 This batch qualifies for 50% discount!")
    
    # Update checkpoint
    checkpoint["status"] = "submitted"
    checkpoint["batch_job_id"] = job_id
    checkpoint["input_file_id"] = file_id
    checkpoint["submitted_at"] = datetime.now().isoformat()
    save_checkpoint(eval_dir, checkpoint)
    
    return job_id


def check_status(client: Mistral, wait: bool = False) -> Dict:
    """Check batch job status."""
    eval_dir = get_eval_dir()
    checkpoint = load_checkpoint(eval_dir)
    
    job_id = checkpoint.get("batch_job_id")
    if not job_id:
        print("❌ No batch job found. Run --prepare and --submit first.")
        return {"status": "not_found"}
    
    print(f"\n📊 Checking batch status: {job_id}")
    
    max_polls = int(MAX_POLL_HOURS * 3600 / POLL_INTERVAL_SECONDS)
    poll_count = 0
    
    while True:
        job = client.batch.jobs.get(job_id=job_id)
        
        status = {
            "job_id": job_id,
            "status": job.status,
            "created_at": str(job.created_at) if job.created_at else None,
        }
        
        # Try to get progress info
        if hasattr(job, 'total_requests'):
            status["total"] = job.total_requests
        if hasattr(job, 'succeeded_requests'):
            status["succeeded"] = job.succeeded_requests
        if hasattr(job, 'failed_requests'):
            status["failed"] = job.failed_requests
        
        print(f"   Status: {job.status}")
        if "total" in status:
            print(f"   Progress: {status.get('succeeded', 0)}/{status.get('total', '?')}")
        
        # Check completion
        if job.status == "SUCCESS":
            print("   ✅ Batch completed!")
            checkpoint["status"] = "completed"
            checkpoint["output_file_id"] = job.output_file if hasattr(job, 'output_file') else None
            save_checkpoint(eval_dir, checkpoint)
            status["output_file_id"] = checkpoint["output_file_id"]
            return status
        
        elif job.status in ["FAILED", "CANCELLED", "EXPIRED"]:
            print(f"   ❌ Batch {job.status}!")
            checkpoint["status"] = job.status.lower()
            if hasattr(job, 'errors'):
                checkpoint["error"] = str(job.errors)
            save_checkpoint(eval_dir, checkpoint)
            return status
        
        if not wait:
            return status
        
        poll_count += 1
        if poll_count >= max_polls:
            print(f"   ⏰ Max wait time reached.")
            return status
        
        print(f"   ⏳ Waiting... ({poll_count}/{max_polls})")
        time.sleep(POLL_INTERVAL_SECONDS)


def download_results(client: Mistral) -> int:
    """Download and process batch results."""
    eval_dir = get_eval_dir()
    checkpoint = load_checkpoint(eval_dir)
    
    job_id = checkpoint.get("batch_job_id")
    if not job_id:
        print("❌ No batch job found.")
        return 0
    
    # Get job to find output file
    job = client.batch.jobs.get(job_id=job_id)
    
    if job.status != "SUCCESS":
        print(f"❌ Batch not completed. Status: {job.status}")
        return 0
    
    output_file_id = job.output_file if hasattr(job, 'output_file') else None
    if not output_file_id:
        print("❌ No output file available.")
        return 0
    
    print(f"\n📥 Downloading results...")
    
    # Download file
    file_content = client.files.download(file_id=output_file_id)
    
    # Handle different response types
    if hasattr(file_content, 'read'):
        raw_content = file_content.read().decode('utf-8')
    elif hasattr(file_content, 'text'):
        raw_content = file_content.text
    else:
        raw_content = str(file_content)
    
    raw_results = raw_content.strip().split('\n')
    print(f"   Downloaded {len(raw_results)} results")
    
    # Load all distortions for ground truth
    all_distortions = load_all_distortions()
    distortion_map = {}
    for dist in all_distortions:
        custom_id = generate_custom_id(dist["question_id"], dist["miu"])
        distortion_map[custom_id] = dist
    
    # Load existing completed IDs
    existing_results = load_results(eval_dir)
    completed_ids = set(r.get("custom_id") for r in existing_results)
    
    # Process results
    new_results = []
    correct = 0
    errors = 0
    
    for line in raw_results:
        if not line.strip():
            continue
        
        try:
            result_obj = json.loads(line)
            custom_id = result_obj.get("custom_id")
            
            if custom_id in completed_ids:
                continue
            
            # Extract response
            body = result_obj.get("body", result_obj.get("response", {}))
            choices = body.get("choices", [])
            
            if not choices:
                errors += 1
                continue
            
            model_answer = choices[0].get("message", {}).get("content", "").strip()
            
            # Clean up answer
            for pattern in [r'^the\s+answer\s+is\s*:?\s*', r'^answer\s*:?\s*', r'^=\s*']:
                model_answer = re.sub(pattern, '', model_answer, flags=re.IGNORECASE)
            model_answer = model_answer.strip().rstrip('.')
            
            # Get ground truth
            dist_data = distortion_map.get(custom_id, {})
            ground_truth = dist_data.get("correct_answer", "")
            
            question_id, miu = parse_custom_id(custom_id)
            
            is_correct, match_type = compare_answers(model_answer, ground_truth)
            if is_correct:
                correct += 1
            
            usage = body.get("usage", {})
            
            result = {
                "custom_id": custom_id,
                "question_id": question_id,
                "miu": miu,
                "miu_description": dist_data.get("miu_description", ""),
                "domain": dist_data.get("domain", ""),
                "difficulty": dist_data.get("difficulty"),
                "difficulty_category": dist_data.get("difficulty_category", ""),
                "ground_truth": ground_truth,
                "model_answer": model_answer,
                "is_correct": is_correct,
                "match_type": match_type,
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
                "model": MODEL_ID,
                "timestamp": datetime.now().isoformat()
            }
            
            new_results.append(result)
            
        except Exception as e:
            print(f"   ⚠️  Error processing result: {e}")
            errors += 1
    
    # Save results
    if new_results:
        append_results(eval_dir, new_results)
        
        all_completed_ids = list(completed_ids) + [r["custom_id"] for r in new_results]
        checkpoint["completed_ids"] = all_completed_ids
        checkpoint["status"] = "results_downloaded"
        save_checkpoint(eval_dir, checkpoint)
    
    total_processed = len(new_results)
    accuracy = correct / total_processed * 100 if total_processed > 0 else 0
    
    print(f"\n   📊 Results Summary:")
    print(f"   New results: {total_processed}")
    print(f"   Correct: {correct}/{total_processed} ({accuracy:.1f}%)")
    if errors > 0:
        print(f"   Errors: {errors}")
    
    # Save summary
    all_results = load_results(eval_dir)
    save_summary(eval_dir, all_results)
    
    print(f"\n   📁 Results saved to: {eval_dir}")
    
    return total_processed


def save_summary(eval_dir: Path, results: List[Dict]):
    """Save evaluation summary."""
    summary = {
        "model": MODEL_ID,
        "total_questions": len(results),
        "correct": sum(1 for r in results if r.get("is_correct")),
        "accuracy": sum(1 for r in results if r.get("is_correct")) / len(results) * 100 if results else 0,
        "by_difficulty": {},
        "by_miu": {},
        "updated_at": datetime.now().isoformat()
    }
    
    # Group by difficulty
    diff_results = {}
    for r in results:
        diff = r.get("difficulty", 0)
        if diff not in diff_results:
            diff_results[diff] = {"correct": 0, "total": 0}
        diff_results[diff]["total"] += 1
        if r.get("is_correct"):
            diff_results[diff]["correct"] += 1
    
    for diff, stats in sorted(diff_results.items()):
        summary["by_difficulty"][str(diff)] = {
            "correct": stats["correct"],
            "total": stats["total"],
            "accuracy": stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        }
    
    # Group by miu
    miu_results = {}
    for r in results:
        miu = r.get("miu")
        if miu not in miu_results:
            miu_results[miu] = {"correct": 0, "total": 0}
        miu_results[miu]["total"] += 1
        if r.get("is_correct"):
            miu_results[miu]["correct"] += 1
    
    for miu, stats in sorted(miu_results.items()):
        summary["by_miu"][str(miu)] = {
            "correct": stats["correct"],
            "total": stats["total"],
            "accuracy": stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        }
    
    summary_file = eval_dir / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n   📋 Summary by difficulty:")
    for diff, stats in summary["by_difficulty"].items():
        print(f"      Difficulty {diff}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.1f}%)")
    
    print(f"\n   📋 Summary by μ level:")
    for miu, stats in summary["by_miu"].items():
        print(f"      μ={miu}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.1f}%)")


def run_full_evaluation(client: Mistral):
    """Run complete evaluation workflow."""
    print(f"\n{'='*60}")
    print(f"🚀 Full Mistral Evaluation: {MODEL_ID}")
    print(f"{'='*60}")
    
    # Step 1: Prepare
    batch_file, request_count = prepare_batch()
    
    if request_count == 0:
        print("\n✅ All questions already evaluated!")
        return
    
    # Step 2: Submit
    job_id = submit_batch(client)
    if not job_id:
        return
    
    # Step 3: Wait
    print(f"\n⏳ Waiting for batch completion...")
    print(f"   This may take several hours. You can Ctrl+C and run --status later.")
    
    try:
        status = check_status(client, wait=True)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted. Run --status to check progress later.")
        return
    
    if status.get("status") != "SUCCESS":
        print(f"\n⚠️  Batch not completed. Status: {status.get('status')}")
        return
    
    # Step 4: Download
    download_results(client)
    
    print(f"\n{'='*60}")
    print(f"✅ Evaluation complete!")
    print(f"{'='*60}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Mistral on distorted questions using Batch API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full workflow
  %(prog)s --run
  
  # Step by step
  %(prog)s --prepare
  %(prog)s --submit
  %(prog)s --status
  %(prog)s --download
  
  # Check status and wait for completion
  %(prog)s --status --wait

Cost Savings:
  The Batch API provides 50% discount on API costs!
        """
    )
    
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true",
                       help="Prepare batch file")
    action.add_argument("--submit", action="store_true",
                       help="Submit batch to Mistral")
    action.add_argument("--status", action="store_true",
                       help="Check batch status")
    action.add_argument("--download", action="store_true",
                       help="Download results")
    action.add_argument("--run", action="store_true",
                       help="Run full evaluation")
    
    parser.add_argument("--force", action="store_true",
                       help="Force recreate batch file")
    parser.add_argument("--wait", action="store_true",
                       help="Wait for completion (with --status)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"Mistral Distortion Evaluation - {MODEL_ID}")
    print("=" * 60)
    
    client = get_client()
    
    try:
        if args.prepare:
            prepare_batch(force=args.force)
        
        elif args.submit:
            prepare_batch(force=args.force)
            submit_batch(client)
        
        elif args.status:
            check_status(client, wait=args.wait)
        
        elif args.download:
            download_results(client)
        
        elif args.run:
            run_full_evaluation(client)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted. Progress saved.")


if __name__ == "__main__":
    main()
