#!/usr/bin/env python3
"""
GPT-5 Retry and Baseline Evaluation Script

This script handles:
1. Identifying questions that failed due to token limits (reasoning_tokens == max_tokens)
2. Creating baseline evaluation batches for GPT-5 (original questions)
3. Re-evaluating failed questions with higher token limits
4. Merging results back into existing results files

Usage:
    # Step 1: Identify failures and prepare batches
    python retry_and_baseline_batch.py --prepare --difficulty 1.0
    python retry_and_baseline_batch.py --prepare --difficulty 1.5
    
    # Step 2: Submit batches
    python retry_and_baseline_batch.py --submit --difficulty 1.0
    python retry_and_baseline_batch.py --submit --difficulty 1.5
    
    # Step 3: Check status
    python retry_and_baseline_batch.py --status --difficulty 1.0
    python retry_and_baseline_batch.py --status --difficulty 1.5
    
    # Step 4: Download and merge results
    python retry_and_baseline_batch.py --download --difficulty 1.0
    python retry_and_baseline_batch.py --download --difficulty 1.5
    
    # Or do all at once:
    python retry_and_baseline_batch.py --run --difficulty 1.0
"""

import argparse
import json
import os
import sys
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_paths = [
        project_root / ".env",
        project_root / "venv" / "bin" / ".env",
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

from omnimath_distortion_workflow.modules.evaluation_prompt import (
    create_evaluation_prompt,
    generate_custom_id,
    parse_custom_id
)
from omnimath_distortion_workflow.modules.answer_comparator import compare_answers

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = project_root / "omnimath_distortion_workflow" / "data" / "by_difficulty"
EVAL_DIR = project_root / "omnimath_distortion_workflow" / "evaluation"
DISTORTION_RESULTS_DIR = EVAL_DIR / "distortion_results"
BASELINE_RESULTS_DIR = EVAL_DIR / "baseline_results"

# Increased token limit for retry - gives model more room for reasoning
GPT5_CONFIG = {
    "model_id": "gpt-5",
    "max_completion_tokens": 1200,  # Increased from 400
    "reasoning_effort": "low",
}

# Batch polling
POLL_INTERVAL = 30
MAX_POLLS = 720  # 6 hours


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client() -> openai.OpenAI:
    """Get OpenAI client."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        sys.exit(1)
    return openai.OpenAI(api_key=api_key)


def get_retry_dir(difficulty: float) -> Path:
    """Get directory for retry/baseline batches."""
    diff_str = str(difficulty).replace(".", "_")
    dir_path = DISTORTION_RESULTS_DIR / f"gpt_5_difficulty_{diff_str}" / "retry_baseline"
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def load_existing_results(difficulty: float) -> List[Dict]:
    """Load existing GPT-5 distortion results."""
    diff_str = str(difficulty).replace(".", "_")
    results_file = DISTORTION_RESULTS_DIR / f"gpt_5_difficulty_{diff_str}" / "results.jsonl"
    
    results = []
    if results_file.exists():
        with open(results_file, 'r') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    return results


def load_baseline_questions(difficulty: float) -> List[Dict]:
    """Load baseline questions for a difficulty level."""
    if difficulty == int(difficulty):
        diff_str = f"difficulty_{int(difficulty)}"
    else:
        diff_str = f"difficulty_{difficulty}"
    
    baseline_file = DATA_DIR / diff_str / f"{diff_str}_baseline_questions.json"
    
    if not baseline_file.exists():
        raise FileNotFoundError(f"Baseline file not found: {baseline_file}")
    
    with open(baseline_file, 'r') as f:
        return json.load(f)


def load_distortions(difficulty: float) -> List[Dict]:
    """Load distorted questions for retry."""
    if difficulty == int(difficulty):
        diff_str = f"difficulty_{int(difficulty)}"
    else:
        diff_str = f"difficulty_{difficulty}"
    
    distortions_file = DATA_DIR / diff_str / f"{diff_str}_distortions.json"
    
    if not distortions_file.exists():
        raise FileNotFoundError(f"Distortions file not found: {distortions_file}")
    
    with open(distortions_file, 'r') as f:
        all_entries = json.load(f)
    
    # Flatten if needed
    distortions = []
    for entry in all_entries:
        if 'miu' in entry and entry.get('miu') is not None:
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
                    }
                    distortions.append(flat_entry)
    
    return distortions


def identify_token_limit_failures(results: List[Dict], max_tokens: int = 400) -> Set[str]:
    """
    Identify questions that failed due to token limits.
    
    Criteria:
    - model_answer is empty
    - reasoning_tokens equals or exceeds max_tokens
    """
    failures = set()
    
    for r in results:
        model_answer = r.get("model_answer", "").strip()
        reasoning_tokens = r.get("reasoning_tokens", 0) or 0
        
        # Empty answer + high reasoning tokens = token limit hit
        if not model_answer and reasoning_tokens >= max_tokens - 10:  # Allow small buffer
            failures.add(r.get("custom_id"))
    
    return failures


def create_batch_request(question: str, custom_id: str) -> Dict:
    """Create a batch request for GPT-5 with increased token limit."""
    prompt = create_evaluation_prompt(question)
    
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": GPT5_CONFIG["model_id"],
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": GPT5_CONFIG["max_completion_tokens"],
            "reasoning_effort": GPT5_CONFIG["reasoning_effort"],
        }
    }


# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def prepare_batches(difficulty: float) -> Tuple[Path, int, int]:
    """
    Prepare batch files for:
    1. Baseline questions (miu=0.0)
    2. Retry questions (token limit failures)
    
    Returns:
        (batch_file_path, baseline_count, retry_count)
    """
    retry_dir = get_retry_dir(difficulty)
    
    print(f"\n📋 Preparing batches for difficulty {difficulty}...")
    
    # Load existing results to find failures
    existing_results = load_existing_results(difficulty)
    print(f"   Loaded {len(existing_results)} existing results")
    
    # Identify token limit failures
    failures = identify_token_limit_failures(existing_results)
    print(f"   Found {len(failures)} token limit failures to retry")
    
    # Load data
    baseline_questions = load_baseline_questions(difficulty)
    distortions = load_distortions(difficulty)
    print(f"   Loaded {len(baseline_questions)} baseline questions")
    print(f"   Loaded {len(distortions)} distorted questions")
    
    # Create distortion lookup
    distortion_map = {}
    for d in distortions:
        cid = generate_custom_id(d["question_id"], d["miu"])
        distortion_map[cid] = d
    
    # Prepare requests
    requests = []
    baseline_count = 0
    retry_count = 0
    
    # 1. Add baseline questions (miu=0.0)
    for q in baseline_questions:
        custom_id = generate_custom_id(q["question_id"], 0.0)
        question_text = q.get("original_question", "")
        
        if question_text:
            req = create_batch_request(question_text, custom_id)
            requests.append(req)
            baseline_count += 1
    
    # 2. Add retry questions (token limit failures)
    for cid in failures:
        dist = distortion_map.get(cid)
        if dist:
            question_text = dist.get("distorted_question", "")
            if question_text:
                req = create_batch_request(question_text, cid)
                requests.append(req)
                retry_count += 1
    
    # Write batch file
    batch_file = retry_dir / "batch_requests.jsonl"
    with open(batch_file, 'w') as f:
        for req in requests:
            f.write(json.dumps(req) + '\n')
    
    # Save checkpoint
    checkpoint = {
        "status": "prepared",
        "difficulty": difficulty,
        "baseline_count": baseline_count,
        "retry_count": retry_count,
        "total_requests": len(requests),
        "retry_custom_ids": list(failures),
        "created_at": datetime.now().isoformat(),
    }
    with open(retry_dir / "checkpoint.json", 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    print(f"\n   ✅ Created batch file: {batch_file}")
    print(f"   📊 Baseline questions: {baseline_count}")
    print(f"   📊 Retry questions: {retry_count}")
    print(f"   📊 Total requests: {len(requests)}")
    
    return batch_file, baseline_count, retry_count


def submit_batch(client: openai.OpenAI, difficulty: float) -> str:
    """Submit batch to OpenAI."""
    retry_dir = get_retry_dir(difficulty)
    
    # Load checkpoint
    checkpoint_file = retry_dir / "checkpoint.json"
    if not checkpoint_file.exists():
        print("❌ No batch prepared. Run --prepare first.")
        return None
    
    with open(checkpoint_file, 'r') as f:
        checkpoint = json.load(f)
    
    if checkpoint.get("batch_id") and checkpoint.get("status") in ["submitted", "processing"]:
        print(f"⚠️  Batch already submitted: {checkpoint['batch_id']}")
        return checkpoint["batch_id"]
    
    batch_file = retry_dir / "batch_requests.jsonl"
    if not batch_file.exists():
        print("❌ Batch file not found.")
        return None
    
    print(f"\n🚀 Submitting batch for difficulty {difficulty}...")
    
    # Upload file
    with open(batch_file, 'rb') as f:
        file_response = client.files.create(file=f, purpose="batch")
    file_id = file_response.id
    print(f"   ✅ File uploaded: {file_id}")
    
    # Create batch
    batch_response = client.batches.create(
        input_file_id=file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": f"GPT-5 retry+baseline - difficulty {difficulty}",
            "type": "retry_baseline"
        }
    )
    batch_id = batch_response.id
    print(f"   ✅ Batch created: {batch_id}")
    print(f"   💰 50% discount via Batch API!")
    
    # Update checkpoint
    checkpoint["status"] = "submitted"
    checkpoint["batch_id"] = batch_id
    checkpoint["file_id"] = file_id
    checkpoint["submitted_at"] = datetime.now().isoformat()
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    return batch_id


def check_status(client: openai.OpenAI, difficulty: float, wait: bool = False) -> Dict:
    """Check batch status."""
    retry_dir = get_retry_dir(difficulty)
    
    checkpoint_file = retry_dir / "checkpoint.json"
    if not checkpoint_file.exists():
        print("❌ No checkpoint found.")
        return {"status": "not_found"}
    
    with open(checkpoint_file, 'r') as f:
        checkpoint = json.load(f)
    
    batch_id = checkpoint.get("batch_id")
    if not batch_id:
        print("❌ No batch ID found.")
        return {"status": "no_batch"}
    
    print(f"\n📊 Checking batch: {batch_id}")
    
    poll_count = 0
    while True:
        batch = client.batches.retrieve(batch_id)
        
        completed = batch.request_counts.completed if batch.request_counts else 0
        total = batch.request_counts.total if batch.request_counts else 0
        failed = batch.request_counts.failed if batch.request_counts else 0
        
        pct = (completed / total * 100) if total > 0 else 0
        print(f"   Status: {batch.status} | Progress: {completed}/{total} ({pct:.1f}%)")
        
        if failed > 0:
            print(f"   ⚠️  Failed: {failed}")
        
        if batch.status == "completed":
            print("   ✅ Batch completed!")
            checkpoint["status"] = "completed"
            checkpoint["output_file_id"] = batch.output_file_id
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            return {"status": "completed", "output_file_id": batch.output_file_id}
        
        if batch.status in ["failed", "expired", "cancelled"]:
            print(f"   ❌ Batch {batch.status}")
            checkpoint["status"] = batch.status
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            return {"status": batch.status}
        
        if not wait:
            return {"status": batch.status}
        
        poll_count += 1
        if poll_count >= MAX_POLLS:
            print("   ⏰ Max polling time reached.")
            return {"status": "polling_timeout"}
        
        print(f"   ⏳ Waiting... ({poll_count}/{MAX_POLLS})")
        time.sleep(POLL_INTERVAL)


def download_and_merge(client: openai.OpenAI, difficulty: float):
    """Download results and merge into existing files."""
    retry_dir = get_retry_dir(difficulty)
    diff_str = str(difficulty).replace(".", "_")
    
    # Load checkpoint
    checkpoint_file = retry_dir / "checkpoint.json"
    with open(checkpoint_file, 'r') as f:
        checkpoint = json.load(f)
    
    output_file_id = checkpoint.get("output_file_id")
    if not output_file_id:
        batch_id = checkpoint.get("batch_id")
        if batch_id:
            batch = client.batches.retrieve(batch_id)
            output_file_id = batch.output_file_id
    
    if not output_file_id:
        print("❌ No output file available.")
        return
    
    print(f"\n📥 Downloading results...")
    
    # Download
    content = client.files.content(output_file_id)
    raw_results = content.text.strip().split('\n')
    print(f"   Downloaded {len(raw_results)} results")
    
    # Load baseline questions for ground truth
    baseline_questions = load_baseline_questions(difficulty)
    baseline_map = {q["question_id"]: q for q in baseline_questions}
    
    # Load distortions for ground truth
    distortions = load_distortions(difficulty)
    distortion_map = {}
    for d in distortions:
        cid = generate_custom_id(d["question_id"], d["miu"])
        distortion_map[cid] = d
    
    # Process results
    baseline_results = []
    retry_results = []
    retry_ids = set(checkpoint.get("retry_custom_ids", []))
    
    for line in raw_results:
        if not line.strip():
            continue
        
        try:
            obj = json.loads(line)
            custom_id = obj.get("custom_id")
            response = obj.get("response", {})
            body = response.get("body", {})
            choices = body.get("choices", [])
            
            if not choices:
                continue
            
            model_answer = choices[0].get("message", {}).get("content", "").strip()
            
            # Clean answer
            for pattern in [r'^the\s+answer\s+is\s*:?\s*', r'^answer\s*:?\s*', r'^=\s*']:
                model_answer = re.sub(pattern, '', model_answer, flags=re.IGNORECASE)
            model_answer = model_answer.strip().rstrip('.')
            
            usage = body.get("usage", {})
            
            # Parse custom_id
            question_id, miu = parse_custom_id(custom_id)
            
            # Determine ground truth and question type
            if miu == 0.0:
                # Baseline question
                q_data = baseline_map.get(question_id, {})
                ground_truth = q_data.get("correct_answer", "")
                domain = q_data.get("domain", "")
                
                is_correct, match_type = compare_answers(model_answer, ground_truth)
                
                result = {
                    "custom_id": custom_id,
                    "question_id": question_id,
                    "miu": 0.0,
                    "miu_description": "Baseline (Original)",
                    "domain": domain,
                    "difficulty": difficulty,
                    "ground_truth": ground_truth,
                    "model_answer": model_answer,
                    "is_correct": is_correct,
                    "match_type": match_type,
                    "input_tokens": usage.get("prompt_tokens"),
                    "output_tokens": usage.get("completion_tokens"),
                    "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens") if usage.get("completion_tokens_details") else 0,
                    "model": "gpt-5",
                    "timestamp": datetime.now().isoformat(),
                }
                baseline_results.append(result)
            
            else:
                # Retry distortion
                dist_data = distortion_map.get(custom_id, {})
                ground_truth = dist_data.get("correct_answer", "")
                
                is_correct, match_type = compare_answers(model_answer, ground_truth)
                
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
                    "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens") if usage.get("completion_tokens_details") else 0,
                    "model": "gpt-5",
                    "timestamp": datetime.now().isoformat(),
                    "is_retry": True,
                }
                retry_results.append(result)
        
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
    
    # Save baseline results
    if baseline_results:
        baseline_file = BASELINE_RESULTS_DIR / f"gpt5_baseline_difficulty_{diff_str}.json"
        with open(baseline_file, 'w') as f:
            json.dump(baseline_results, f, indent=2)
        
        correct = sum(1 for r in baseline_results if r.get("is_correct"))
        print(f"\n   📊 Baseline Results: {correct}/{len(baseline_results)} ({correct/len(baseline_results)*100:.1f}%)")
        print(f"   📁 Saved to: {baseline_file}")
    
    # Merge retry results into existing results
    if retry_results:
        existing_results_file = DISTORTION_RESULTS_DIR / f"gpt_5_difficulty_{diff_str}" / "results.jsonl"
        existing = load_existing_results(difficulty)
        
        # Create map of existing results
        existing_map = {r.get("custom_id"): r for r in existing}
        
        # Replace failed results with retries
        replaced = 0
        for retry in retry_results:
            cid = retry.get("custom_id")
            if cid in existing_map:
                existing_map[cid] = retry
                replaced += 1
        
        # Write updated results
        all_results = list(existing_map.values())
        with open(existing_results_file, 'w') as f:
            for r in all_results:
                f.write(json.dumps(r) + '\n')
        
        correct = sum(1 for r in retry_results if r.get("is_correct"))
        print(f"\n   📊 Retry Results: {correct}/{len(retry_results)} ({correct/len(retry_results)*100:.1f}%)")
        print(f"   🔄 Replaced {replaced} failed results")
        
        # Update summary
        update_summary(difficulty, all_results)
    
    # Update checkpoint
    checkpoint["status"] = "merged"
    checkpoint["merged_at"] = datetime.now().isoformat()
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    print(f"\n   ✅ Results merged successfully!")


def update_summary(difficulty: float, all_results: List[Dict]):
    """Update the summary.json file."""
    diff_str = str(difficulty).replace(".", "_")
    summary_file = DISTORTION_RESULTS_DIR / f"gpt_5_difficulty_{diff_str}" / "summary.json"
    
    total = len(all_results)
    correct = sum(1 for r in all_results if r.get("is_correct"))
    
    # By MIU
    miu_stats = {}
    for r in all_results:
        miu = r.get("miu")
        if miu not in miu_stats:
            miu_stats[miu] = {"correct": 0, "total": 0}
        miu_stats[miu]["total"] += 1
        if r.get("is_correct"):
            miu_stats[miu]["correct"] += 1
    
    summary = {
        "model": "gpt-5",
        "difficulty": difficulty,
        "total_questions": total,
        "correct": correct,
        "accuracy": correct / total * 100 if total > 0 else 0,
        "by_miu": {},
        "updated_at": datetime.now().isoformat(),
    }
    
    for miu, stats in sorted(miu_stats.items()):
        summary["by_miu"][str(miu)] = {
            "correct": stats["correct"],
            "total": stats["total"],
            "accuracy": stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"   📁 Updated summary: {summary_file}")


def run_full(client: openai.OpenAI, difficulty: float):
    """Run the complete pipeline."""
    print(f"\n{'='*60}")
    print(f"🚀 GPT-5 Retry + Baseline Evaluation - Difficulty {difficulty}")
    print(f"{'='*60}")
    
    # Prepare
    batch_file, baseline_count, retry_count = prepare_batches(difficulty)
    
    if baseline_count + retry_count == 0:
        print("\n✅ Nothing to do!")
        return
    
    # Submit
    batch_id = submit_batch(client, difficulty)
    if not batch_id:
        return
    
    # Wait
    print(f"\n⏳ Waiting for batch completion...")
    try:
        status = check_status(client, difficulty, wait=True)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted. Run --status later.")
        return
    
    if status.get("status") != "completed":
        print(f"\n⚠️  Batch not completed: {status.get('status')}")
        return
    
    # Download and merge
    download_and_merge(client, difficulty)
    
    print(f"\n{'='*60}")
    print("✅ Complete!")
    print(f"{'='*60}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="GPT-5 Retry and Baseline Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true", help="Prepare batch files")
    action.add_argument("--submit", action="store_true", help="Submit batch")
    action.add_argument("--status", action="store_true", help="Check status")
    action.add_argument("--download", action="store_true", help="Download and merge")
    action.add_argument("--run", action="store_true", help="Run full pipeline")
    
    parser.add_argument("--difficulty", type=float, required=True, choices=[1.0, 1.5])
    parser.add_argument("--wait", action="store_true", help="Wait for completion (with --status)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("GPT-5 Retry + Baseline Evaluation (Batch API)")
    print("=" * 60)
    print(f"Difficulty: {args.difficulty}")
    print(f"Max Completion Tokens: {GPT5_CONFIG['max_completion_tokens']}")
    
    client = get_client()
    
    try:
        if args.prepare:
            prepare_batches(args.difficulty)
        elif args.submit:
            submit_batch(client, args.difficulty)
        elif args.status:
            check_status(client, args.difficulty, wait=args.wait)
        elif args.download:
            download_and_merge(client, args.difficulty)
        elif args.run:
            run_full(client, args.difficulty)
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()

