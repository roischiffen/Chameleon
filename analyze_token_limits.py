#!/usr/bin/env python3
"""
Analyze flagged questions to determine how many hit the 1500 token limit.
"""

import json
from pathlib import Path
from collections import defaultdict

# Load validation report
validation_report = Path(__file__).parent / "validation_report.json"
results_dir = Path(__file__).parent / "data" / "results_verified"

MODELS = {
    "gpt-4_1": "gpt-4_1_results_*.jsonl",
    "gpt-5": "gpt-5_results_*.jsonl",
    "gpt-5-mini": "gpt-5-mini_results_*.jsonl",
}

def load_model_results(model_name):
    """Load all results for a model."""
    pattern = MODELS[model_name]
    result_files = list(results_dir.glob(pattern))
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

def parse_custom_id(custom_id):
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

def check_token_limit(result_entry):
    """Check if result hit 1500 token limit."""
    response = result_entry.get('response', {})
    body = response.get('body', {})
    choices = body.get('choices', [])
    
    if not choices:
        return False, None, None
    
    finish_reason = choices[0].get('finish_reason', '')
    usage = body.get('usage', {})
    completion_tokens = usage.get('completion_tokens', 0)
    
    # Check if hit token limit
    hit_limit = (finish_reason == 'length' and completion_tokens == 1500)
    
    return hit_limit, finish_reason, completion_tokens

def main():
    # Load validation report
    with open(validation_report, 'r') as f:
        report = json.load(f)
    
    # Extract flagged questions
    flagged = defaultdict(set)  # {(category, question_id, model): True}
    
    for warning in report['warnings']:
        category = warning['category']
        question_id = warning['question_id']
        message = warning['message']
        
        # Extract model name from message
        if 'gpt-4_1' in message:
            model = 'gpt-4_1'
        elif 'gpt-5-mini' in message:
            model = 'gpt-5-mini'
        elif 'gpt-5' in message:
            model = 'gpt-5'
        else:
            continue
        
        flagged[(category, question_id, model)] = True
    
    print("="*80)
    print("TOKEN LIMIT ANALYSIS FOR FLAGGED QUESTIONS")
    print("="*80)
    print(f"\nTotal flagged warnings: {len(report['warnings'])}")
    print(f"Unique flagged question-model combinations: {len(flagged)}\n")
    
    # Load all model results
    print("Loading model results...")
    all_results = {}
    for model in MODELS.keys():
        all_results[model] = load_model_results(model)
        print(f"  Loaded {len(all_results[model])} results for {model}")
    
    # Analyze flagged questions
    token_limit_hits = defaultdict(int)
    token_limit_details = []
    
    for (category, question_id, model), _ in flagged.items():
        custom_id = f"cat{category}_q_{question_id}_miu_0.0"
        
        if custom_id not in all_results[model]:
            continue
        
        result_entry = all_results[model][custom_id]
        hit_limit, finish_reason, completion_tokens = check_token_limit(result_entry)
        
        if hit_limit:
            token_limit_hits[model] += 1
            token_limit_details.append({
                'category': category,
                'question_id': question_id,
                'model': model,
                'finish_reason': finish_reason,
                'completion_tokens': completion_tokens
            })
    
    # Print results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    total_hits = sum(token_limit_hits.values())
    print(f"\nTotal flagged questions: {len(flagged)}")
    print(f"Questions that hit 1500 token limit: {total_hits}")
    print(f"Percentage: {(total_hits / len(flagged) * 100):.1f}%\n")
    
    print("Breakdown by model:")
    for model in MODELS.keys():
        hits = token_limit_hits[model]
        flagged_count = sum(1 for (c, q, m) in flagged.keys() if m == model)
        if flagged_count > 0:
            percentage = (hits / flagged_count * 100) if flagged_count > 0 else 0
            print(f"  {model}: {hits}/{flagged_count} ({(percentage):.1f}%)")
    
    # Show sample details
    print(f"\nSample questions that hit token limit (first 10):")
    print("-"*80)
    for detail in token_limit_details[:10]:
        print(f"  Category {detail['category']}, QID {detail['question_id']}, "
              f"Model {detail['model']}: {detail['completion_tokens']} tokens, "
              f"finish_reason='{detail['finish_reason']}'")
    
    if len(token_limit_details) > 10:
        print(f"  ... and {len(token_limit_details) - 10} more")
    
    # Save detailed report
    output_file = Path(__file__).parent / "token_limit_analysis.json"
    with open(output_file, 'w') as f:
        json.dump({
            'total_flagged': len(flagged),
            'total_hit_limit': total_hits,
            'percentage': (total_hits / len(flagged) * 100) if len(flagged) > 0 else 0,
            'by_model': dict(token_limit_hits),
            'details': token_limit_details
        }, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {output_file}")
    print("="*80)

if __name__ == "__main__":
    main()

