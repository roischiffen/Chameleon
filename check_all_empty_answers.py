#!/usr/bin/env python3
"""
Comprehensive check for empty answers across ALL MIU levels (baseline + distorted).

This script:
1. Checks all MIU levels (0.0, 0.2, 0.5, 0.7, 0.9) for empty answers
2. Identifies the cause (token limit vs other reasons)
3. Compares with what we're already retrying
4. Generates a report of what still needs to be retried
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any

# Paths
DATA_DIR = Path(__file__).parent / "data" / "distortion_validation"
RESULTS_DIR = Path(__file__).parent / "data" / "results_verified"
RETRY_BATCH_DIR = Path(__file__).parent / "data" / "retry_batches"
ANALYSIS_FILE = Path(__file__).parent / "question_token_pattern_analysis.json"

MODELS = ["gpt-4_1", "gpt-5", "gpt-5-mini"]
MIU_LEVELS = [0.0, 0.2, 0.5, 0.7, 0.9]
CATEGORIES = [1, 2, 3]


def load_model_results(model: str) -> Dict[str, Dict[str, Any]]:
    """Load all results for a model, indexed by custom_id."""
    model_files = {
        "gpt-4_1": "gpt-4_1_results_*.jsonl",
        "gpt-5": "gpt-5_results_*.jsonl",
        "gpt-5-mini": "gpt-5-mini_results_*.jsonl",
    }
    
    pattern = model_files.get(model)
    if not pattern:
        return {}
    
    result_files = list(RESULTS_DIR.glob(pattern))
    if not result_files:
        return {}
    
    results = {}
    with open(result_files[0], 'r', encoding='utf-8') as f:
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


def parse_custom_id(custom_id: str) -> Tuple[int, str, float]:
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


def check_empty_answer(result_entry: Dict[str, Any]) -> Tuple[bool, str, int]:
    """
    Check if result has empty answer and determine cause.
    
    Returns:
        (is_empty, cause, completion_tokens)
        - is_empty: True if answer is empty
        - cause: "token_limit", "error", "empty_response", or "unknown"
        - completion_tokens: Number of completion tokens used
    """
    if not result_entry:
        return True, "missing", 0
    
    # Check for error
    if result_entry.get('error'):
        return True, "error", 0
    
    response = result_entry.get('response', {})
    
    # Check status code
    if response.get('status_code') != 200:
        return True, f"status_{response.get('status_code')}", 0
    
    body = response.get('body', {})
    choices = body.get('choices', [])
    
    if not choices:
        return True, "no_choices", 0
    
    # Check answer content
    content = choices[0].get('message', {}).get('content', '')
    is_empty = not content or not content.strip()
    
    # Check finish reason and token usage
    finish_reason = choices[0].get('finish_reason', '')
    usage = body.get('usage', {})
    completion_tokens = usage.get('completion_tokens', 0)
    
    if is_empty:
        if finish_reason == 'length' and completion_tokens >= 1490:  # Allow small buffer
            return True, "token_limit", completion_tokens
        elif finish_reason == 'length':
            return True, "token_limit_other", completion_tokens
        else:
            return True, "empty_response", completion_tokens
    
    return False, "has_answer", completion_tokens


def load_retry_batches() -> Set[str]:
    """Load custom_ids from retry batch files."""
    retry_custom_ids = set()
    
    for batch_file in RETRY_BATCH_DIR.glob("*_retry_3000tokens.jsonl"):
        with open(batch_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    custom_id = entry.get('custom_id', '')
                    if custom_id:
                        # Remove _retry_3000 suffix to match original custom_id
                        original_id = custom_id.replace('_retry_3000', '')
                        retry_custom_ids.add(original_id)
                except json.JSONDecodeError:
                    continue
    
    return retry_custom_ids


def check_all_miu_levels():
    """Check all MIU levels for empty answers."""
    print("="*80)
    print("COMPREHENSIVE EMPTY ANSWER CHECK")
    print("="*80)
    
    # Load retry batches to see what we're already retrying
    retry_custom_ids = load_retry_batches()
    print(f"\n📋 Loaded {len(retry_custom_ids)} custom_ids from retry batches")
    
    # Load all model results
    print("\n📚 Loading model results...")
    all_results = {}
    for model in MODELS:
        all_results[model] = load_model_results(model)
        print(f"   {model}: {len(all_results[model])} results")
    
    # Track empty answers
    empty_answers = defaultdict(lambda: defaultdict(dict))  # {model: {category: {question_id: {miu: details}}}}
    total_checked = 0
    total_empty = 0
    
    # Check all combinations
    print("\n🔍 Checking all MIU levels for empty answers...")
    
    for category in CATEGORIES:
        for model in MODELS:
            for miu in MIU_LEVELS:
                # Check all results for this category and MIU level
                for custom_id, result_entry in all_results[model].items():
                    cat, qid, result_miu = parse_custom_id(custom_id)
                    
                    if cat != category or result_miu != miu:
                        continue
                    
                    total_checked += 1
                    is_empty, cause, completion_tokens = check_empty_answer(result_entry)
                    
                    if is_empty:
                        total_empty += 1
                        if qid not in empty_answers[model][category]:
                            empty_answers[model][category][qid] = {}
                        
                        empty_answers[model][category][qid][miu] = {
                            'custom_id': custom_id,
                            'cause': cause,
                            'completion_tokens': completion_tokens,
                            'is_retrying': custom_id in retry_custom_ids
                        }
    
    print(f"\n✅ Checked {total_checked} results")
    print(f"   Found {total_empty} empty answers")
    
    # Analyze what needs retry
    already_retrying = set()
    need_retry = defaultdict(lambda: defaultdict(dict))
    need_retry_token_limit = defaultdict(lambda: defaultdict(dict))
    need_retry_other = defaultdict(lambda: defaultdict(dict))
    
    for model in MODELS:
        for category in CATEGORIES:
            for qid, miu_data in empty_answers[model][category].items():
                if qid not in need_retry[model][category]:
                    need_retry[model][category][qid] = {}
                if qid not in need_retry_token_limit[model][category]:
                    need_retry_token_limit[model][category][qid] = {}
                if qid not in need_retry_other[model][category]:
                    need_retry_other[model][category][qid] = {}
                
                for miu, details in miu_data.items():
                    custom_id = details['custom_id']
                    cause = details['cause']
                    
                    if details['is_retrying']:
                        already_retrying.add(custom_id)
                    else:
                        need_retry[model][category][qid][miu] = details
                        
                        if cause == 'token_limit':
                            need_retry_token_limit[model][category][qid][miu] = details
                        else:
                            need_retry_other[model][category][qid][miu] = details
    
    # Generate report
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)
    
    # Count properly
    total_need_retry = 0
    token_limit_count = 0
    other_count = 0
    
    for model in MODELS:
        for category in CATEGORIES:
            if category in need_retry.get(model, {}):
                for qid, miu_data in need_retry[model][category].items():
                    total_need_retry += len(miu_data)
                    
                    # Count token limit vs other
                    for miu, details in miu_data.items():
                        if details['cause'] == 'token_limit':
                            token_limit_count += 1
                        else:
                            other_count += 1
    
    print(f"\n📊 Empty Answers Breakdown:")
    print(f"   Total empty answers found: {total_empty}")
    print(f"   Already retrying: {len(already_retrying)}")
    print(f"   Still need retry: {total_need_retry}")
    
    print(f"\n📋 Need Retry Breakdown:")
    print(f"   Token limit issues: {token_limit_count}")
    print(f"   Other issues (errors, empty responses): {other_count}")
    
    # Detailed breakdown by model
    print(f"\n📈 By Model:")
    for model in MODELS:
        model_total = sum(
            len(miu_data)
            for cats in need_retry[model].values()
            for qids in cats.values()
            for miu_data in [qids]
        )
        token_limit = sum(
            len(miu_data)
            for cats in need_retry_token_limit[model].values()
            for qids in cats.values()
            for miu_data in [qids]
        )
        other = sum(
            len(miu_data)
            for cats in need_retry_other[model].values()
            for qids in cats.values()
            for miu_data in [qids]
        )
        print(f"   {model}: {model_total} total ({token_limit} token limit, {other} other)")
    
    # Detailed breakdown by MIU level
    print(f"\n📊 By MIU Level:")
    for miu in MIU_LEVELS:
        miu_total = sum(
            1
            for model in MODELS
            for cats in need_retry[model].values()
            for qids in cats.values()
            if miu in qids
        )
        print(f"   MIU {miu}: {miu_total} empty answers")
    
    # Save detailed report
    report = {
        'summary': {
            'total_checked': total_checked,
            'total_empty': total_empty,
            'already_retrying': len(already_retrying),
            'need_retry_total': sum(
                len(miu_data)
                for cats in need_retry.values()
                for qids in cats.values()
                for miu_data in [qids]
            ),
            'need_retry_token_limit': token_limit_count,
            'need_retry_other': other_count
        },
        'already_retrying': list(already_retrying),
        'need_retry': {
            model: {
                category: {
                    qid: {
                        str(miu): details
                        for miu, details in miu_data.items()
                    }
                    for qid, miu_data in qids.items()
                }
                for category, qids in cats.items()
            }
            for model, cats in need_retry.items()
        },
        'need_retry_token_limit': {
            model: {
                category: {
                    qid: {
                        str(miu): details
                        for miu, details in miu_data.items()
                    }
                    for qid, miu_data in qids.items()
                }
                for category, qids in cats.items()
            }
            for model, cats in need_retry_token_limit.items()
        },
        'need_retry_other': {
            model: {
                category: {
                    qid: {
                        str(miu): details
                        for miu, details in miu_data.items()
                    }
                    for qid, miu_data in qids.items()
                }
                for category, qids in cats.items()
            }
            for model, cats in need_retry_other.items()
        }
    }
    
    report_file = Path(__file__).parent / "empty_answers_comprehensive_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Generate human-readable summary
    summary_file = Path(__file__).parent / "EMPTY_ANSWERS_ANALYSIS.md"
    generate_summary_report(summary_file, report, empty_answers, retry_custom_ids)
    
    print(f"📝 Summary report saved to: {summary_file}")
    print("="*80)
    
    return report


def generate_summary_report(output_file: Path, report: Dict, empty_answers: Dict, retry_custom_ids: Set[str]):
    """Generate human-readable summary report."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Comprehensive Empty Answers Analysis\n\n")
        f.write("## Executive Summary\n\n")
        
        summary = report['summary']
        f.write(f"- **Total Results Checked**: {summary['total_checked']}\n")
        f.write(f"- **Total Empty Answers Found**: {summary['total_empty']}\n")
        f.write(f"- **Already Retrying**: {summary['already_retrying']}\n")
        f.write(f"- **Still Need Retry**: {summary['need_retry_token_limit'] + summary['need_retry_other']}\n")
        f.write(f"  - Token limit issues: {summary['need_retry_token_limit']}\n")
        f.write(f"  - Other issues: {summary['need_retry_other']}\n\n")
        
        f.write("## What We're Already Retrying\n\n")
        f.write("The following empty answers are **already included** in retry batches:\n\n")
        f.write(f"- **Total**: {len(retry_custom_ids)} combinations\n")
        f.write("- **All are token limit issues** (1500 token limit hit)\n")
        f.write("- **All are baseline (MIU 0.0)** questions\n")
        f.write("- **Models**: gpt-5 and gpt-5-mini\n\n")
        
        f.write("## What Still Needs Retry\n\n")
        
        # Token limit issues
        f.write("### 1. Token Limit Issues (Not Yet Retrying)\n\n")
        token_limit = report['need_retry_token_limit']
        token_limit_count = 0
        for model, cats in token_limit.items():
            for category, qids in cats.items():
                for qid, miu_data in qids.items():
                    token_limit_count += len(miu_data)
        
        if token_limit_count > 0:
            f.write(f"Found **{token_limit_count}** empty answers due to token limits that are NOT in retry batches:\n\n")
            f.write("These are likely:\n")
            f.write("- Distorted questions (MIU 0.2, 0.5, 0.7, 0.9) that hit token limits\n")
            f.write("- Questions that hit token limits but weren't flagged in baseline check\n\n")
            
            f.write("**Breakdown by Model:**\n")
            for model, cats in token_limit.items():
                model_count = sum(len(miu_data) for qids in cats.values() for miu_data in qids.values())
                if model_count > 0:
                    f.write(f"- {model}: {model_count}\n")
            
            f.write("\n**Breakdown by MIU Level:**\n")
            miu_counts = defaultdict(int)
            for model, cats in token_limit.items():
                for category, qids in cats.items():
                    for qid, miu_data in qids.items():
                        for miu in miu_data.keys():
                            miu_counts[float(miu)] += 1
            
            for miu in sorted(miu_counts.keys()):
                f.write(f"- MIU {miu}: {miu_counts[miu]}\n")
            
            f.write("\n**Sample Questions:**\n")
            sample_count = 0
            for model, cats in token_limit.items():
                for category, qids in list(cats.items())[:3]:
                    for qid, miu_data in list(qids.items())[:2]:
                        if sample_count < 10:
                            f.write(f"- Category {category}, QID {qid}, Model {model}: MIU levels {list(miu_data.keys())}\n")
                            sample_count += 1
        else:
            f.write("✅ **No token limit issues found that aren't already retrying!**\n\n")
        
        # Other issues
        f.write("\n### 2. Other Issues (Errors, Empty Responses)\n\n")
        other = report['need_retry_other']
        other_count = sum(len(miu_data) for cats in other.values() for qids in cats.values() for miu_data in qids.values())
        
        if other_count > 0:
            f.write(f"Found **{other_count}** empty answers due to other reasons:\n\n")
            
            # Group by cause
            causes = defaultdict(int)
            for model, cats in other.items():
                for category, qids in cats.items():
                    for qid, miu_data in qids.items():
                        for miu, details in miu_data.items():
                            causes[details['cause']] += 1
            
            f.write("**Breakdown by Cause:**\n")
            for cause, count in sorted(causes.items(), key=lambda x: -x[1]):
                f.write(f"- {cause}: {count}\n")
            
            f.write("\n**Breakdown by Model:**\n")
            for model, cats in other.items():
                model_count = sum(len(miu_data) for qids in cats.values() for miu_data in qids.values())
                if model_count > 0:
                    f.write(f"- {model}: {model_count}\n")
        else:
            f.write("✅ **No other issues found!**\n\n")
        
        f.write("\n## Recommendations\n\n")
        
        if token_limit_count > 0:
            f.write("### For Token Limit Issues:\n")
            f.write("1. **Add distorted questions to retry batches** - Currently only baseline (MIU 0.0) questions are retried\n")
            f.write("2. **Use 3000 token limit** for all retries (already configured)\n")
            f.write("3. **Include all failed MIU levels** in retry batches\n\n")
        
        if other_count > 0:
            f.write("### For Other Issues:\n")
            f.write("1. **Investigate root causes** - Check if these are API errors, timeouts, or other issues\n")
            f.write("2. **Retry with error handling** - May need different retry strategy than token limit issues\n")
            f.write("3. **Check if these are systematic** - May indicate API or configuration problems\n\n")
        
        f.write("## Next Steps\n\n")
        f.write("1. Review the detailed JSON report: `empty_answers_comprehensive_report.json`\n")
        f.write("2. Generate additional retry batches for:\n")
        if token_limit_count > 0:
            f.write(f"   - Token limit issues: {token_limit_count} combinations\n")
        if other_count > 0:
            f.write(f"   - Other issues: {other_count} combinations\n")
        f.write("3. Ensure complete coverage of all empty answers\n")


if __name__ == "__main__":
    check_all_miu_levels()

