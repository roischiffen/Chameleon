#!/usr/bin/env python3
"""
Download retry batch results, validate success, merge into existing results, and generate report.

This script:
1. Downloads completed batch results from OpenAI
2. Validates each retry result BEFORE replacing existing results
3. Only replaces empty answers if retry has successful content
4. Generates detailed report on questions that still have empty answers
"""

import openai
import os
import sys
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# Load environment variables
def load_env_file(env_path: Path):
    """Load environment variables from .env file."""
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

env_path = Path(__file__).parent / "venv" / "bin" / ".env"
load_env_file(env_path)
root_env = Path(__file__).parent / ".env"
load_env_file(root_env)

# Get API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("❌ Error: OPENAI_API_KEY not set")
    sys.exit(1)

client = openai.OpenAI(api_key=api_key)

RESULTS_DIR = Path(__file__).parent / "data" / "results_verified"
DATA_DIR = Path(__file__).parent / "data" / "distortion_validation"

# Batch IDs from submission
BATCH_IDS = {
    "gpt-5": [
        "batch_695b6fd62e008190917aa6d5faa968c8",  # initial retry
        "batch_695b73d88e008190be87586780a9fb8e",  # complete retry
    ],
    "gpt-5-mini": [
        "batch_695b6fd85f388190abb3e06df7866afc",  # initial retry
        "batch_695b73da2b2c8190b407dcd7579c3a85",  # complete retry
    ],
}


def normalize_custom_id(custom_id: str) -> str:
    """Normalize custom_id by removing retry suffixes."""
    if custom_id.endswith('_retry_3000'):
        custom_id = custom_id[:-len('_retry_3000')]
    if custom_id.endswith('_complete'):
        custom_id = custom_id[:-len('_complete')]
    if custom_id.endswith('_retry_3000_complete'):
        custom_id = custom_id[:-len('_retry_3000_complete')]
    return custom_id


def parse_custom_id(custom_id: str) -> Tuple[Optional[int], Optional[str], Optional[float]]:
    """Parse custom_id to extract category, question_id, and miu."""
    try:
        parts = custom_id.split('_')
        if len(parts) < 4:
            return None, None, None
        
        cat_str = parts[0]  # e.g., "cat1"
        category = int(cat_str.replace('cat', ''))
        
        # Find question_id (between 'q' and 'miu')
        q_start_idx = None
        miu_start_idx = None
        for i, part in enumerate(parts):
            if part == 'q' and i + 1 < len(parts):
                q_start_idx = i + 1
            elif part == 'miu' and i + 1 < len(parts):
                miu_start_idx = i + 1
                break
        
        if q_start_idx is None or miu_start_idx is None:
            return None, None, None
        
        question_id = '_'.join(parts[q_start_idx:miu_start_idx])
        miu_level = float(parts[miu_start_idx])
        
        return category, question_id, miu_level
    except (ValueError, IndexError):
        return None, None, None


def check_batch_status(batch_id: str) -> Optional[Dict]:
    """Check status of a batch."""
    try:
        batch = client.batches.retrieve(batch_id)
        return {
            "id": batch.id,
            "status": batch.status,
            "output_file_id": batch.output_file_id,
            "request_counts": batch.request_counts if hasattr(batch, 'request_counts') else None,
        }
    except Exception as e:
        print(f"   ❌ Error checking batch {batch_id}: {e}")
        return None


def download_batch_results(batch_id: str, model: str) -> Optional[Path]:
    """Download results from a completed batch."""
    batch_info = check_batch_status(batch_id)
    
    if not batch_info:
        return None
    
    if batch_info["status"] != "completed":
        print(f"   ⏳ Batch {batch_id} not completed yet. Status: {batch_info['status']}")
        return None
    
    if not batch_info["output_file_id"]:
        print(f"   ⚠️  No output file available for batch {batch_id}")
        return None
    
    print(f"   📥 Downloading results from batch {batch_id}...")
    try:
        file_response = client.files.content(batch_info["output_file_id"])
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_safe = model.replace("-", "_")
        batch_short = batch_id.split('_')[-1][:8]
        results_file = RESULTS_DIR / f"{model_safe}_retry_{batch_short}_{timestamp}.jsonl"
        
        with open(results_file, 'wb') as f:
            f.write(file_response.content)
        
        # Count results
        with open(results_file, 'r') as f:
            result_count = sum(1 for line in f if line.strip())
        
        print(f"   ✅ Downloaded {result_count} results to {results_file.name}")
        return results_file
        
    except Exception as e:
        print(f"   ❌ Error downloading batch {batch_id}: {e}")
        return None


def check_empty_answer(result_entry: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
    """Check if result has empty answer and determine cause."""
    response = result_entry.get('response', {})
    
    if response.get('status_code') != 200:
        return True, f"error_{response.get('status_code')}", None
    
    body = response.get('body', {})
    if not body:
        return True, "no_response", None
    
    choices = body.get('choices', [])
    if not choices:
        return True, "no_choices", None
    
    message = choices[0].get('message', {})
    content = message.get('content', '').strip()
    
    if not content:
        finish_reason = choices[0].get('finish_reason', '')
        usage = body.get('usage', {})
        completion_tokens = usage.get('completion_tokens', 0)
        
        if finish_reason == "length":
            return True, "token_limit", completion_tokens
        elif finish_reason == "content_filter":
            return True, "content_filter", completion_tokens
        elif finish_reason == "stop" and not content:
            return True, "empty_response", completion_tokens
        else:
            return True, f"unknown_{finish_reason}", completion_tokens
    
    return False, None, None


def load_existing_results(model: str) -> Dict[str, Dict]:
    """Load existing results for a model, indexed by custom_id."""
    model_files = {
        "gpt-5": "gpt-5_results_*.jsonl",
        "gpt-5-mini": "gpt-5-mini_results_*.jsonl",
    }
    
    pattern = model_files.get(model)
    if not pattern:
        return {}
    
    results = {}
    for result_file in RESULTS_DIR.glob(pattern):
        # Skip retry results files
        if "retry" in result_file.name:
            continue
        
        with open(result_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    custom_id = entry.get('custom_id', '')
                    if custom_id:
                        results[custom_id] = entry
                except json.JSONDecodeError:
                    continue
    
    return results


def load_question_text(category: int, question_id: str, miu: float) -> str:
    """Load question text for a given category, question_id, and MIU."""
    cat_dir = DATA_DIR / f"category_{category}"
    
    if miu == 0.0:
        # Load from original questions
        orig_file = cat_dir / "original_questions_and_ground_truth.json"
        if orig_file.exists():
            with open(orig_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for q in data:
                    if q.get('question_id') == question_id:
                        return q.get('problem', '')
            elif isinstance(data, dict) and 'questions' in data:
                for q in data['questions']:
                    if q.get('question_id') == question_id:
                        return q.get('problem', '')
    else:
        # Load from distorted questions
        dist_file = cat_dir / "distorted_questions.json"
        if not dist_file.exists():
            dist_file = cat_dir / "distorted_question.json"
        
        if dist_file.exists():
            with open(dist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict) and 'distortions' in data:
                for entry in data['distortions']:
                    if entry.get('question_id') == question_id:
                        distortions = entry.get('distortions', {})
                        miu_key = f"miu_{miu}"
                        if miu_key in distortions:
                            return distortions[miu_key].get('distorted_problem', '')
    
    return ''


def validate_and_merge_results(existing_results: Dict[str, Dict], retry_results_files: List[Path]) -> Tuple[Dict[str, Dict], Dict]:
    """Validate retry results and merge into existing results."""
    merged = existing_results.copy()
    stats = {
        "replaced": 0,
        "skipped_empty": 0,
        "skipped_token_limit": 0,
        "new": 0,
        "validation_failed": 0,
    }
    
    for retry_file in retry_results_files:
        with open(retry_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    retry_entry = json.loads(line)
                    custom_id = retry_entry.get('custom_id', '')
                    
                    if not custom_id:
                        continue
                    
                    # Normalize custom_id
                    normalized_id = normalize_custom_id(custom_id)
                    
                    # Validate retry result
                    is_empty, cause, completion_tokens = check_empty_answer(retry_entry)
                    
                    if is_empty:
                        # Don't replace if retry is also empty
                        if normalized_id in merged:
                            if cause == "token_limit":
                                stats["skipped_token_limit"] += 1
                            else:
                                stats["skipped_empty"] += 1
                        else:
                            stats["skipped_empty"] += 1
                        continue
                    
                    # Retry has content - validate it's successful
                    if retry_entry.get('response', {}).get('status_code') != 200:
                        stats["validation_failed"] += 1
                        continue
                    
                    # Update custom_id to normalized version
                    retry_entry['custom_id'] = normalized_id
                    
                    # Replace existing or add new
                    if normalized_id in merged:
                        merged[normalized_id] = retry_entry
                        stats["replaced"] += 1
                    else:
                        merged[normalized_id] = retry_entry
                        stats["new"] += 1
                        
                except json.JSONDecodeError as e:
                    print(f"   ⚠️  Error parsing line in {retry_file.name}: {e}")
                    continue
    
    return merged, stats


def generate_empty_answers_report(models: List[str], existing_results: Dict[str, Dict]) -> Dict:
    """Generate detailed report on questions that still have empty answers."""
    report = {
        "summary": {
            "total_empty": 0,
            "token_limit_empty": 0,
            "other_empty": 0,
            "unique_questions_with_empty": set(),
        },
        "by_model": {},
        "by_question": defaultdict(lambda: {
            "category": None,
            "question_id": None,
            "baseline_empty": False,
            "distorted_empty": [],
            "models_affected": set(),
            "token_limit_issues": [],
            "question_text": "",
        }),
    }
    
    for model in models:
        model_results = existing_results.get(model, {})
        model_empty = []
        model_token_limit = []
        
        for custom_id, entry in model_results.items():
            is_empty, cause, completion_tokens = check_empty_answer(entry)
            
            if is_empty:
                category, question_id, miu = parse_custom_id(custom_id)
                
                if category and question_id:
                    report["summary"]["unique_questions_with_empty"].add((category, question_id))
                    
                    q_key = f"cat{category}_q_{question_id}"
                    report["by_question"][q_key]["category"] = category
                    report["by_question"][q_key]["question_id"] = question_id
                    report["by_question"][q_key]["models_affected"].add(model)
                    
                    if miu == 0.0:
                        report["by_question"][q_key]["baseline_empty"] = True
                    else:
                        report["by_question"][q_key]["distorted_empty"].append({
                            "miu": miu,
                            "model": model,
                            "cause": cause,
                            "completion_tokens": completion_tokens,
                        })
                    
                    if cause == "token_limit":
                        report["by_question"][q_key]["token_limit_issues"].append({
                            "miu": miu,
                            "model": model,
                            "completion_tokens": completion_tokens,
                        })
                        model_token_limit.append({
                            "custom_id": custom_id,
                            "category": category,
                            "question_id": question_id,
                            "miu": miu,
                            "completion_tokens": completion_tokens,
                        })
                        report["summary"]["token_limit_empty"] += 1
                    else:
                        model_empty.append({
                            "custom_id": custom_id,
                            "category": category,
                            "question_id": question_id,
                            "miu": miu,
                            "cause": cause,
                        })
                        report["summary"]["other_empty"] += 1
                    
                    report["summary"]["total_empty"] += 1
        
        report["by_model"][model] = {
            "empty": len(model_empty),
            "token_limit": len(model_token_limit),
            "details": {
                "empty": model_empty,
                "token_limit": model_token_limit,
            },
        }
    
    # Load question texts
    for q_key, q_data in report["by_question"].items():
        category = q_data["category"]
        question_id = q_data["question_id"]
        
        # Load baseline text
        if q_data["baseline_empty"]:
            text = load_question_text(category, question_id, 0.0)
            if text:
                q_data["question_text"] = text[:500] + "..." if len(text) > 500 else text
        
        # Load distorted texts if needed
        if q_data["distorted_empty"]:
            for dist in q_data["distorted_empty"]:
                miu = dist["miu"]
                text = load_question_text(category, question_id, miu)
                if text and not q_data["question_text"]:
                    q_data["question_text"] = text[:500] + "..." if len(text) > 500 else text
    
    # Convert sets to lists for JSON serialization
    report["summary"]["unique_questions_with_empty"] = len(report["summary"]["unique_questions_with_empty"])
    for q_data in report["by_question"].values():
        q_data["models_affected"] = list(q_data["models_affected"])
    
    return report


def save_merged_results(model: str, merged_results: Dict[str, Dict]):
    """Save merged results to the original results file."""
    model_files = {
        "gpt-5": "gpt-5_results_*.jsonl",
        "gpt-5-mini": "gpt-5-mini_results_*.jsonl",
    }
    
    pattern = model_files.get(model)
    if not pattern:
        return None
    
    # Find the original results file
    result_files = list(RESULTS_DIR.glob(pattern))
    if not result_files:
        # Create new file if none exists
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_safe = model.replace("-", "_")
        result_file = RESULTS_DIR / f"{model_safe}_results_{timestamp}.jsonl"
    else:
        # Use the most recent file
        result_file = max(result_files, key=lambda p: p.stat().st_mtime)
    
    # Backup original file
    backup_file = result_file.with_suffix('.jsonl.backup')
    if result_file.exists():
        import shutil
        shutil.copy2(result_file, backup_file)
        print(f"   💾 Backed up original to: {backup_file.name}")
    
    # Write merged results
    with open(result_file, 'w', encoding='utf-8') as f:
        for custom_id in sorted(merged_results.keys()):
            f.write(json.dumps(merged_results[custom_id]) + '\n')
    
    print(f"   ✅ Saved merged results to: {result_file.name}")
    return result_file


def main():
    print("="*80)
    print("DOWNLOAD, VALIDATE, AND MERGE RETRY BATCH RESULTS")
    print("="*80)
    
    # Step 1: Download all batch results
    print("\n" + "="*80)
    print("STEP 1: DOWNLOADING BATCH RESULTS")
    print("="*80)
    
    downloaded_files = defaultdict(list)
    
    for model, batch_ids in BATCH_IDS.items():
        print(f"\n📦 {model}")
        for batch_id in batch_ids:
            result_file = download_batch_results(batch_id, model)
            if result_file:
                downloaded_files[model].append(result_file)
    
    if not downloaded_files:
        print("\n❌ No results downloaded. Exiting.")
        return
    
    # Step 2: Validate and merge results
    print("\n" + "="*80)
    print("STEP 2: VALIDATING AND MERGING RESULTS")
    print("="*80)
    
    all_merged_results = {}
    all_merge_stats = {}
    
    for model, retry_files in downloaded_files.items():
        print(f"\n🔄 Processing {model}...")
        
        # Load existing results
        existing_results = load_existing_results(model)
        print(f"   Existing results: {len(existing_results)} entries")
        
        # Validate and merge
        merged_results, stats = validate_and_merge_results(existing_results, retry_files)
        all_merged_results[model] = merged_results
        all_merge_stats[model] = stats
        
        print(f"   📊 Merge statistics:")
        print(f"      Replaced (successful): {stats['replaced']}")
        print(f"      New (successful): {stats['new']}")
        print(f"      Skipped (empty): {stats['skipped_empty']}")
        print(f"      Skipped (token limit): {stats['skipped_token_limit']}")
        print(f"      Validation failed: {stats['validation_failed']}")
        
        # Save merged results
        save_merged_results(model, merged_results)
    
    # Step 3: Generate report on remaining empty answers
    print("\n" + "="*80)
    print("STEP 3: GENERATING EMPTY ANSWERS REPORT")
    print("="*80)
    
    # Combine all results for report
    combined_results = {}
    for model, results in all_merged_results.items():
        for custom_id, entry in results.items():
            key = f"{model}:{custom_id}"
            combined_results[key] = entry
    
    report = generate_empty_answers_report(list(BATCH_IDS.keys()), all_merged_results)
    
    # Save report
    report_file = Path(__file__).parent / "empty_answers_after_retry_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        # Convert defaultdict to dict for JSON serialization
        report_dict = {
            "summary": report["summary"],
            "by_model": report["by_model"],
            "by_question": dict(report["by_question"]),
        }
        json.dump(report_dict, f, indent=2)
    
    print(f"\n✅ Report saved to: {report_file.name}")
    
    # Generate text report
    text_report_file = Path(__file__).parent / "EMPTY_ANSWERS_AFTER_RETRY_REPORT.txt"
    with open(text_report_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("EMPTY ANSWERS AFTER RETRY REPORT\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"SUMMARY\n")
        f.write(f"Total empty answers: {report['summary']['total_empty']}\n")
        f.write(f"Token limit issues: {report['summary']['token_limit_empty']}\n")
        f.write(f"Other empty: {report['summary']['other_empty']}\n")
        f.write(f"Unique questions with empty answers: {report['summary']['unique_questions_with_empty']}\n\n")
        
        f.write("="*80 + "\n")
        f.write("BY MODEL\n")
        f.write("="*80 + "\n\n")
        
        for model, model_data in report["by_model"].items():
            f.write(f"{model}:\n")
            f.write(f"  Empty: {model_data['empty']}\n")
            f.write(f"  Token limit: {model_data['token_limit']}\n\n")
        
        f.write("="*80 + "\n")
        f.write("BY QUESTION (QUESTIONS WITH EMPTY ANSWERS)\n")
        f.write("="*80 + "\n\n")
        
        for q_key, q_data in sorted(report["by_question"].items()):
            f.write(f"Question: {q_key}\n")
            f.write(f"  Category: {q_data['category']}\n")
            f.write(f"  Question ID: {q_data['question_id']}\n")
            f.write(f"  Models affected: {', '.join(q_data['models_affected'])}\n")
            
            if q_data["baseline_empty"]:
                f.write(f"  Baseline (MIU 0.0): EMPTY\n")
            
            if q_data["distorted_empty"]:
                f.write(f"  Distorted versions empty:\n")
                for dist in q_data["distorted_empty"]:
                    f.write(f"    MIU {dist['miu']} ({dist['model']}): {dist['cause']}")
                    if dist.get('completion_tokens'):
                        f.write(f" - {dist['completion_tokens']} tokens")
                    f.write("\n")
            
            if q_data["token_limit_issues"]:
                f.write(f"  Token limit issues:\n")
                for issue in q_data["token_limit_issues"]:
                    f.write(f"    MIU {issue['miu']} ({issue['model']}): {issue['completion_tokens']} tokens reached\n")
            
            if q_data["question_text"]:
                f.write(f"  Question text: {q_data['question_text']}\n")
            
            f.write("\n")
    
    print(f"✅ Text report saved to: {text_report_file.name}")
    
    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()

