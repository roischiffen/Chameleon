#!/usr/bin/env python3
"""
Distortion Evaluation Script using OpenAI Batch API (50% Cost Savings)

Evaluates models on distorted questions from difficulty 1.0 and 1.5.
Uses OpenAI's Batch API for 50% cost reduction compared to synchronous calls.

Key Features:
- 50% cost savings via Batch API
- Robust checkpointing - saves progress incrementally
- Resume from interruptions - never lose completed work
- Supports both GPT-4o and GPT-5-mini models
- Handles both difficulty levels (1.0 and 1.5)

Usage:
    # Step 1: Create batch requests (doesn't use API credits)
    python evaluate_distortions_batch.py --prepare --model gpt-4o --difficulty 1.0
    
    # Step 2: Submit batch to OpenAI (starts processing)
    python evaluate_distortions_batch.py --submit --model gpt-4o --difficulty 1.0
    
    # Step 3: Check status and download when ready
    python evaluate_distortions_batch.py --status --model gpt-4o --difficulty 1.0
    
    # Or do everything in one command (prepare + submit + wait):
    python evaluate_distortions_batch.py --run --model gpt-4o --difficulty 1.0
    
    # Resume/retry after failure:
    python evaluate_distortions_batch.py --resume --model gpt-4o --difficulty 1.0

Environment:
    OPENAI_API_KEY: Your OpenAI API key (required)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
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

# Try to import openai
try:
    import openai
except ImportError:
    print("❌ Error: openai package not installed")
    print("   Install with: pip install openai")
    sys.exit(1)

from omnimath_distortion_workflow.modules.evaluation_prompt import (
    create_evaluation_prompt,
    generate_custom_id,
    parse_custom_id
)
from omnimath_distortion_workflow.modules.answer_comparator import compare_answers

# ============================================================================
# PATHS AND CONFIGURATION
# ============================================================================

DATA_DIR = project_root / "omnimath_distortion_workflow" / "data" / "by_difficulty"
EVAL_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "distortion_results"

# Model configurations
MODEL_CONFIGS = {
    "gpt-4o": {
        "model_id": "gpt-4o",
        "use_reasoning": False,
        "max_tokens_param": "max_tokens",
        "max_tokens": 150,
        "temperature": 0,
    },
    "gpt-5": {
        "model_id": "gpt-5",
        "use_reasoning": True,
        "max_tokens_param": "max_completion_tokens",
        "max_tokens": 1200,  # Increased from 400 to prevent token limit issues
        "reasoning_effort": "low",  # Low reasoning for fair comparison
    },
    "gpt-5-mini": {
        "model_id": "gpt-5-mini",
        "use_reasoning": True,
        "max_tokens_param": "max_completion_tokens",
        "max_tokens": 800,  # Increased for safety
        "reasoning_effort": "low",
    },
    "o4-mini": {
        "model_id": "o4-mini",
        "use_reasoning": True,
        "max_tokens_param": "max_completion_tokens",
        "max_tokens": 150,
        "reasoning_effort": "low",
    }
}

# Batch API polling configuration
POLL_INTERVAL_SECONDS = 30  # Check every 30 seconds
MAX_POLL_ATTEMPTS = 720     # 6 hours max wait (720 * 30s = 6h)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client() -> openai.OpenAI:
    """Get OpenAI client with API key from environment."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    return openai.OpenAI(api_key=api_key)


def get_eval_dir(model: str, difficulty: float) -> Path:
    """Get evaluation directory for specific model and difficulty."""
    model_name = model.replace("-", "_")
    diff_str = str(difficulty).replace(".", "_")
    eval_dir = EVAL_DIR / f"{model_name}_difficulty_{diff_str}"
    eval_dir.mkdir(parents=True, exist_ok=True)
    return eval_dir


def load_distortions(difficulty: float) -> List[Dict]:
    """Load distorted questions for a specific difficulty level."""
    # Handle folder naming: difficulty_1 (not difficulty_1.0) but difficulty_1.5
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
        # Format 1: Flat format - miu is directly in the entry
        if 'miu' in entry and entry.get('miu') is not None:
            distortions.append(entry)
        
        # Format 2: Nested format - distortions array contains miu entries
        elif 'distortions' in entry and isinstance(entry['distortions'], list):
            for dist in entry['distortions']:
                if 'miu' in dist and 'distorted_question' in dist:
                    # Flatten the nested structure
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
                    }
                    distortions.append(flat_entry)
    
    print(f"   Loaded {len(distortions)} distorted questions")
    return distortions


def load_checkpoint(eval_dir: Path) -> Dict:
    """Load checkpoint data from evaluation directory."""
    checkpoint_file = eval_dir / "checkpoint.json"
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return {
        "status": "not_started",
        "batch_id": None,
        "batch_input_file_id": None,
        "completed_ids": [],
        "results": [],
        "created_at": None,
        "updated_at": None
    }


def save_checkpoint(eval_dir: Path, checkpoint: Dict):
    """Save checkpoint data to evaluation directory."""
    checkpoint["updated_at"] = datetime.now().isoformat()
    checkpoint_file = eval_dir / "checkpoint.json"
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)


def load_results(eval_dir: Path) -> List[Dict]:
    """Load existing results from evaluation directory."""
    results_file = eval_dir / "results.jsonl"
    results = []
    if results_file.exists():
        with open(results_file, 'r') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    return results


def append_results(eval_dir: Path, new_results: List[Dict]):
    """Append new results to results file."""
    results_file = eval_dir / "results.jsonl"
    with open(results_file, 'a') as f:
        for result in new_results:
            f.write(json.dumps(result) + '\n')


# ============================================================================
# BATCH API FUNCTIONS
# ============================================================================

def create_batch_request(question_data: Dict, model_config: Dict) -> Dict:
    """Create a single batch request for OpenAI Batch API."""
    custom_id = generate_custom_id(question_data["question_id"], question_data["miu"])
    prompt = create_evaluation_prompt(question_data["distorted_question"])
    
    body = {
        "model": model_config["model_id"],
        "messages": [{"role": "user", "content": prompt}],
        model_config["max_tokens_param"]: model_config["max_tokens"],
    }
    
    # Add reasoning effort for reasoning models
    if model_config.get("use_reasoning"):
        body["reasoning_effort"] = model_config.get("reasoning_effort", "low")
    else:
        body["temperature"] = model_config.get("temperature", 0)
    
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": body
    }


def prepare_batch(model: str, difficulty: float, force: bool = False) -> Tuple[Path, int]:
    """
    Prepare batch requests file for OpenAI Batch API.
    
    Returns:
        Tuple of (batch_file_path, request_count)
    """
    eval_dir = get_eval_dir(model, difficulty)
    checkpoint = load_checkpoint(eval_dir)
    
    # Check if already prepared
    batch_file = eval_dir / "batch_requests.jsonl"
    if batch_file.exists() and not force:
        if checkpoint["status"] not in ["not_started", "failed"]:
            print(f"⚠️  Batch already prepared. Use --force to recreate.")
            # Count existing requests
            with open(batch_file, 'r') as f:
                count = sum(1 for _ in f)
            return batch_file, count
    
    print(f"\n📋 Preparing batch for {model} on difficulty {difficulty}...")
    
    # Load distortions
    distortions = load_distortions(difficulty)
    print(f"   Loaded {len(distortions)} distorted questions")
    
    # Get model config
    model_config = MODEL_CONFIGS.get(model)
    if not model_config:
        raise ValueError(f"Unknown model: {model}. Available: {list(MODEL_CONFIGS.keys())}")
    
    # Load existing completed IDs to skip
    completed_ids = set(checkpoint.get("completed_ids", []))
    existing_results = load_results(eval_dir)
    for result in existing_results:
        if result.get("custom_id"):
            completed_ids.add(result["custom_id"])
    
    # Create batch requests
    requests = []
    skipped = 0
    
    for dist in distortions:
        custom_id = generate_custom_id(dist["question_id"], dist["miu"])
        
        # Skip already completed
        if custom_id in completed_ids:
            skipped += 1
            continue
        
        request = create_batch_request(dist, model_config)
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


def submit_batch(client: openai.OpenAI, model: str, difficulty: float) -> str:
    """
    Submit batch to OpenAI Batch API.
    
    Returns:
        Batch ID
    """
    eval_dir = get_eval_dir(model, difficulty)
    checkpoint = load_checkpoint(eval_dir)
    
    # Check for existing batch
    if checkpoint.get("batch_id") and checkpoint["status"] in ["submitted", "processing"]:
        print(f"⚠️  Batch already submitted: {checkpoint['batch_id']}")
        print(f"   Run with --status to check progress")
        return checkpoint["batch_id"]
    
    batch_file = eval_dir / "batch_requests.jsonl"
    if not batch_file.exists():
        raise FileNotFoundError(f"Batch file not found. Run --prepare first.")
    
    # Count requests
    with open(batch_file, 'r') as f:
        request_count = sum(1 for _ in f)
    
    if request_count == 0:
        print("   ✅ No requests to submit (all completed)")
        return None
    
    print(f"\n🚀 Submitting batch to OpenAI...")
    print(f"   Requests: {request_count}")
    
    # Upload batch file
    print("   📤 Uploading batch file...")
    with open(batch_file, 'rb') as f:
        file_response = client.files.create(
            file=f,
            purpose="batch"
        )
    file_id = file_response.id
    print(f"   ✅ File uploaded: {file_id}")
    
    # Create batch
    print("   🔄 Creating batch job...")
    batch_response = client.batches.create(
        input_file_id=file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "model": model,
            "difficulty": str(difficulty),
            "description": f"OmniMath distortion evaluation - {model} - difficulty {difficulty}"
        }
    )
    batch_id = batch_response.id
    
    print(f"   ✅ Batch created: {batch_id}")
    print(f"   💰 This batch qualifies for 50% discount!")
    
    # Update checkpoint
    checkpoint["status"] = "submitted"
    checkpoint["batch_id"] = batch_id
    checkpoint["batch_input_file_id"] = file_id
    checkpoint["submitted_at"] = datetime.now().isoformat()
    save_checkpoint(eval_dir, checkpoint)
    
    return batch_id


def check_batch_status(client: openai.OpenAI, model: str, difficulty: float, wait: bool = False) -> Dict:
    """
    Check batch status and optionally wait for completion.
    
    Args:
        client: OpenAI client
        model: Model name
        difficulty: Difficulty level
        wait: If True, poll until completion
    
    Returns:
        Status dict with batch info
    """
    eval_dir = get_eval_dir(model, difficulty)
    checkpoint = load_checkpoint(eval_dir)
    
    batch_id = checkpoint.get("batch_id")
    if not batch_id:
        print("❌ No batch found. Run --prepare and --submit first.")
        return {"status": "not_found"}
    
    print(f"\n📊 Checking batch status: {batch_id}")
    
    poll_count = 0
    while True:
        batch = client.batches.retrieve(batch_id)
        
        status = {
            "batch_id": batch_id,
            "status": batch.status,
            "created_at": batch.created_at,
            "completed": batch.request_counts.completed if batch.request_counts else 0,
            "failed": batch.request_counts.failed if batch.request_counts else 0,
            "total": batch.request_counts.total if batch.request_counts else 0,
        }
        
        progress_pct = (status["completed"] / status["total"] * 100) if status["total"] > 0 else 0
        
        print(f"   Status: {status['status']}")
        print(f"   Progress: {status['completed']}/{status['total']} ({progress_pct:.1f}%)")
        
        if status["failed"] > 0:
            print(f"   ⚠️  Failed: {status['failed']}")
        
        # Check if done
        if batch.status == "completed":
            print("   ✅ Batch completed!")
            checkpoint["status"] = "completed"
            checkpoint["output_file_id"] = batch.output_file_id
            save_checkpoint(eval_dir, checkpoint)
            status["output_file_id"] = batch.output_file_id
            return status
        
        elif batch.status == "failed":
            print("   ❌ Batch failed!")
            checkpoint["status"] = "failed"
            checkpoint["error"] = str(batch.errors) if hasattr(batch, 'errors') else "Unknown error"
            save_checkpoint(eval_dir, checkpoint)
            return status
        
        elif batch.status in ["expired", "cancelled"]:
            print(f"   ⚠️  Batch {batch.status}")
            checkpoint["status"] = batch.status
            save_checkpoint(eval_dir, checkpoint)
            return status
        
        # If not waiting, return current status
        if not wait:
            return status
        
        # Poll for completion
        poll_count += 1
        if poll_count >= MAX_POLL_ATTEMPTS:
            print(f"   ⏰ Max polling time reached. Run --status again later.")
            return status
        
        print(f"   ⏳ Waiting... (poll {poll_count}/{MAX_POLL_ATTEMPTS})")
        time.sleep(POLL_INTERVAL_SECONDS)


def download_results(client: openai.OpenAI, model: str, difficulty: float) -> int:
    """
    Download and process batch results.
    
    Returns:
        Number of new results processed
    """
    eval_dir = get_eval_dir(model, difficulty)
    checkpoint = load_checkpoint(eval_dir)
    
    output_file_id = checkpoint.get("output_file_id")
    if not output_file_id:
        # Try to get from batch status
        batch_id = checkpoint.get("batch_id")
        if batch_id:
            batch = client.batches.retrieve(batch_id)
            output_file_id = batch.output_file_id
    
    if not output_file_id:
        print("❌ No output file available. Check batch status first.")
        return 0
    
    print(f"\n📥 Downloading results...")
    
    # Download file content
    file_content = client.files.content(output_file_id)
    raw_results = file_content.text.strip().split('\n')
    
    print(f"   Downloaded {len(raw_results)} results")
    
    # Load distortions for ground truth
    distortions = load_distortions(difficulty)
    distortion_map = {}
    for dist in distortions:
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
            
            # Skip already processed
            if custom_id in completed_ids:
                continue
            
            # Extract response
            response = result_obj.get("response", {})
            body = response.get("body", {})
            choices = body.get("choices", [])
            
            if not choices:
                errors += 1
                continue
            
            # Get model answer
            model_answer = choices[0].get("message", {}).get("content", "").strip()
            
            # Clean up answer
            for pattern in [r'^the\s+answer\s+is\s*:?\s*', r'^answer\s*:?\s*', r'^=\s*']:
                model_answer = re.sub(pattern, '', model_answer, flags=re.IGNORECASE)
            model_answer = model_answer.strip().rstrip('.')
            
            # Get ground truth
            dist_data = distortion_map.get(custom_id, {})
            ground_truth = dist_data.get("correct_answer", "")
            
            # Parse custom_id
            question_id, miu = parse_custom_id(custom_id)
            
            # Compare answers
            is_correct, match_type = compare_answers(model_answer, ground_truth)
            if is_correct:
                correct += 1
            
            # Get token usage
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
                "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens") if usage.get("completion_tokens_details") else None,
                "model": model,
                "timestamp": datetime.now().isoformat()
            }
            
            new_results.append(result)
            
        except Exception as e:
            print(f"   ⚠️  Error processing result: {e}")
            errors += 1
    
    # Save new results
    if new_results:
        append_results(eval_dir, new_results)
        
        # Update checkpoint
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
    
    # Save final summary
    all_results = load_results(eval_dir)
    summary_file = eval_dir / "summary.json"
    summary = {
        "model": model,
        "difficulty": difficulty,
        "total_questions": len(all_results),
        "correct": sum(1 for r in all_results if r.get("is_correct")),
        "accuracy": sum(1 for r in all_results if r.get("is_correct")) / len(all_results) * 100 if all_results else 0,
        "by_miu": {},
        "updated_at": datetime.now().isoformat()
    }
    
    # Accuracy by miu level
    miu_results = {}
    for r in all_results:
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
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n   📁 Results saved to: {eval_dir}")
    print(f"   📁 Summary saved to: {summary_file}")
    
    return total_processed


def run_full_evaluation(client: openai.OpenAI, model: str, difficulty: float):
    """Run complete evaluation: prepare, submit, wait, download."""
    print(f"\n{'='*60}")
    print(f"🚀 Full Evaluation: {model} on difficulty {difficulty}")
    print(f"{'='*60}")
    
    # Step 1: Prepare
    batch_file, request_count = prepare_batch(model, difficulty)
    
    if request_count == 0:
        print("\n✅ All questions already evaluated!")
        return
    
    # Step 2: Submit
    batch_id = submit_batch(client, model, difficulty)
    if not batch_id:
        return
    
    # Step 3: Wait for completion
    print(f"\n⏳ Waiting for batch completion...")
    print(f"   This may take 1-24 hours. You can Ctrl+C and run --status later.")
    
    try:
        status = check_batch_status(client, model, difficulty, wait=True)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted. Run --status to check progress later.")
        return
    
    if status.get("status") != "completed":
        print(f"\n⚠️  Batch not completed. Status: {status.get('status')}")
        return
    
    # Step 4: Download results
    download_results(client, model, difficulty)
    
    print(f"\n{'='*60}")
    print(f"✅ Evaluation complete!")
    print(f"{'='*60}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate models on distorted questions using Batch API (50% discount)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full evaluation (prepare + submit + wait + download)
  %(prog)s --run --model gpt-4o --difficulty 1.0
  
  # Step-by-step evaluation
  %(prog)s --prepare --model gpt-4o --difficulty 1.0
  %(prog)s --submit --model gpt-4o --difficulty 1.0
  %(prog)s --status --model gpt-4o --difficulty 1.0
  %(prog)s --download --model gpt-4o --difficulty 1.0
  
  # Evaluate both difficulties for a model
  %(prog)s --run --model gpt-4o --difficulty 1.0
  %(prog)s --run --model gpt-4o --difficulty 1.5
  
  # Resume after interruption
  %(prog)s --status --model gpt-4o --difficulty 1.0 --wait

Cost Savings:
  The Batch API provides 50% discount on API costs!
  - Standard API: ~$0.0025 per question (GPT-4o)
  - Batch API: ~$0.00125 per question (50% off)
  
  For 800 questions (difficulty 1.0 + 1.5):
  - Standard: ~$2.00
  - Batch: ~$1.00 (saves $1.00!)
        """
    )
    
    # Action arguments (mutually exclusive)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true",
                       help="Prepare batch requests file")
    action.add_argument("--submit", action="store_true",
                       help="Submit batch to OpenAI")
    action.add_argument("--status", action="store_true",
                       help="Check batch status")
    action.add_argument("--download", action="store_true",
                       help="Download and process results")
    action.add_argument("--run", action="store_true",
                       help="Run full evaluation (prepare + submit + wait + download)")
    action.add_argument("--resume", action="store_true",
                       help="Resume from last checkpoint")
    
    # Required arguments
    parser.add_argument("--model", type=str, required=True,
                       choices=list(MODEL_CONFIGS.keys()),
                       help="Model to evaluate")
    parser.add_argument("--difficulty", type=float, required=True,
                       choices=[1.0, 1.5],
                       help="Difficulty level to evaluate")
    
    # Optional arguments
    parser.add_argument("--force", action="store_true",
                       help="Force recreate batch file (with --prepare)")
    parser.add_argument("--wait", action="store_true",
                       help="Wait for batch completion (with --status)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("OmniMath Distortion Evaluation (Batch API - 50% Discount)")
    print("=" * 60)
    print(f"Model: {args.model}")
    print(f"Difficulty: {args.difficulty}")
    
    # Get OpenAI client
    client = get_client()
    
    try:
        if args.prepare:
            prepare_batch(args.model, args.difficulty, force=args.force)
        
        elif args.submit:
            submit_batch(client, args.model, args.difficulty)
        
        elif args.status:
            check_batch_status(client, args.model, args.difficulty, wait=args.wait)
        
        elif args.download:
            download_results(client, args.model, args.difficulty)
        
        elif args.run:
            run_full_evaluation(client, args.model, args.difficulty)
        
        elif args.resume:
            eval_dir = get_eval_dir(args.model, args.difficulty)
            checkpoint = load_checkpoint(eval_dir)
            status = checkpoint.get("status", "not_started")
            
            print(f"\n📋 Current status: {status}")
            
            if status == "not_started":
                run_full_evaluation(client, args.model, args.difficulty)
            elif status == "prepared":
                submit_batch(client, args.model, args.difficulty)
                check_batch_status(client, args.model, args.difficulty, wait=True)
                download_results(client, args.model, args.difficulty)
            elif status in ["submitted", "processing"]:
                result = check_batch_status(client, args.model, args.difficulty, wait=True)
                if result.get("status") == "completed":
                    download_results(client, args.model, args.difficulty)
            elif status == "completed":
                download_results(client, args.model, args.difficulty)
            else:
                print(f"   Status: {status}")
                print("   Run --run to start fresh evaluation")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted. Progress saved. Run --resume to continue.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
