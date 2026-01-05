#!/usr/bin/env python3
"""
Analyze token limit patterns across all MIU levels for flagged questions.
For each unique question, check if token limit issues occur at multiple MIU levels.
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

MIU_LEVELS = [0.0, 0.2, 0.5, 0.7, 0.9]

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
    if not result_entry:
        return False, None, None
    
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

def analyze_question(category, question_id, all_results):
    """Analyze a question across all MIU levels and models."""
    question_analysis = {
        'category': category,
        'question_id': question_id,
        'miu_levels_affected': defaultdict(lambda: defaultdict(bool)),  # {model: {miu: hit_limit}}
        'total_miu_levels_affected': defaultdict(int),  # {model: count}
        'all_miu_levels': set()
    }
    
    for model in MODELS.keys():
        for miu in MIU_LEVELS:
            custom_id = f"cat{category}_q_{question_id}_miu_{miu}"
            
            if custom_id in all_results[model]:
                result_entry = all_results[model][custom_id]
                hit_limit, finish_reason, completion_tokens = check_token_limit(result_entry)
                
                question_analysis['miu_levels_affected'][model][miu] = hit_limit
                if hit_limit:
                    question_analysis['total_miu_levels_affected'][model] += 1
                question_analysis['all_miu_levels'].add(miu)
    
    return question_analysis

def main():
    # Load validation report
    with open(validation_report, 'r') as f:
        report = json.load(f)
    
    # Extract unique flagged questions
    flagged_questions = set()
    
    for warning in report['warnings']:
        category = warning['category']
        question_id = warning['question_id']
        flagged_questions.add((category, question_id))
    
    print("="*80)
    print("TOKEN LIMIT PATTERN ANALYSIS FOR FLAGGED QUESTIONS")
    print("="*80)
    print(f"\nTotal unique flagged questions: {len(flagged_questions)}\n")
    
    # Load all model results
    print("Loading model results...")
    all_results = {}
    for model in MODELS.keys():
        all_results[model] = load_model_results(model)
        print(f"  Loaded {len(all_results[model])} results for {model}")
    
    # Analyze each flagged question
    question_analyses = []
    
    for category, question_id in sorted(flagged_questions):
        analysis = analyze_question(category, question_id, all_results)
        question_analyses.append(analysis)
    
    # Categorize questions
    only_baseline_affected = []  # Only MIU 0.0 affected
    multiple_miu_affected = []   # Multiple MIU levels affected
    all_miu_affected = []        # All 5 MIU levels affected
    
    for analysis in question_analyses:
        max_affected = 0
        for model in MODELS.keys():
            count = analysis['total_miu_levels_affected'][model]
            max_affected = max(max_affected, count)
        
        if max_affected == 1:
            only_baseline_affected.append(analysis)
        elif max_affected == 5:
            all_miu_affected.append(analysis)
        else:
            multiple_miu_affected.append(analysis)
    
    # Print summary
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)
    
    print(f"\n📊 Question Categories:")
    print(f"  Only baseline (MIU 0.0) affected: {len(only_baseline_affected)}")
    print(f"  Multiple MIU levels affected (2-4 levels): {len(multiple_miu_affected)}")
    print(f"  All 5 MIU levels affected: {len(all_miu_affected)}")
    
    # Detailed breakdown
    print(f"\n📋 Detailed Breakdown:")
    print(f"\n1. Questions with ONLY baseline (MIU 0.0) token limit issues:")
    print("-"*80)
    if only_baseline_affected:
        for analysis in only_baseline_affected[:10]:
            models_affected = [m for m in MODELS.keys() 
                             if analysis['total_miu_levels_affected'][m] == 1]
            print(f"  Category {analysis['category']}, QID {analysis['question_id']}: "
                  f"Affected models: {', '.join(models_affected)}")
        if len(only_baseline_affected) > 10:
            print(f"  ... and {len(only_baseline_affected) - 10} more")
    else:
        print("  None")
    
    print(f"\n2. Questions with MULTIPLE MIU levels affected (2-4 levels):")
    print("-"*80)
    if multiple_miu_affected:
        for analysis in multiple_miu_affected[:10]:
            affected_levels = {}
            for model in MODELS.keys():
                levels = [miu for miu, hit in analysis['miu_levels_affected'][model].items() if hit]
                if levels:
                    affected_levels[model] = sorted(levels)
            
            print(f"  Category {analysis['category']}, QID {analysis['question_id']}:")
            for model, levels in affected_levels.items():
                print(f"    {model}: MIU levels {levels} ({len(levels)}/5 levels)")
        if len(multiple_miu_affected) > 10:
            print(f"  ... and {len(multiple_miu_affected) - 10} more")
    else:
        print("  None")
    
    print(f"\n3. Questions with ALL 5 MIU levels affected:")
    print("-"*80)
    if all_miu_affected:
        for analysis in all_miu_affected[:10]:
            models_affected = [m for m in MODELS.keys() 
                             if analysis['total_miu_levels_affected'][m] == 5]
            print(f"  Category {analysis['category']}, QID {analysis['question_id']}: "
                  f"Affected models: {', '.join(models_affected)}")
        if len(all_miu_affected) > 10:
            print(f"  ... and {len(all_miu_affected) - 10} more")
    else:
        print("  None")
    
    # Model-specific breakdown
    print(f"\n📈 Model-Specific Breakdown:")
    print("-"*80)
    for model in MODELS.keys():
        baseline_only = sum(1 for a in question_analyses 
                          if a['total_miu_levels_affected'][model] == 1)
        multiple = sum(1 for a in question_analyses 
                      if 1 < a['total_miu_levels_affected'][model] < 5)
        all_levels = sum(1 for a in question_analyses 
                        if a['total_miu_levels_affected'][model] == 5)
        
        print(f"\n  {model}:")
        print(f"    Only baseline affected: {baseline_only}")
        print(f"    Multiple levels affected: {multiple}")
        print(f"    All 5 levels affected: {all_levels}")
    
    # Save detailed report
    output_file = Path(__file__).parent / "question_token_pattern_analysis.json"
    
    report_data = {
        'summary': {
            'total_unique_flagged': len(flagged_questions),
            'only_baseline': len(only_baseline_affected),
            'multiple_miu': len(multiple_miu_affected),
            'all_miu': len(all_miu_affected)
        },
        'only_baseline_affected': [
            {
                'category': a['category'],
                'question_id': a['question_id'],
                'affected_models': {m: list(a['miu_levels_affected'][m].keys()) 
                                  for m in MODELS.keys() 
                                  if a['total_miu_levels_affected'][m] > 0}
            }
            for a in only_baseline_affected
        ],
        'multiple_miu_affected': [
            {
                'category': a['category'],
                'question_id': a['question_id'],
                'affected_models': {
                    m: {
                        'affected_levels': sorted([miu for miu, hit in a['miu_levels_affected'][m].items() if hit]),
                        'count': a['total_miu_levels_affected'][m]
                    }
                    for m in MODELS.keys() 
                    if a['total_miu_levels_affected'][m] > 0
                }
            }
            for a in multiple_miu_affected
        ],
        'all_miu_affected': [
            {
                'category': a['category'],
                'question_id': a['question_id'],
                'affected_models': {m: 'all_5_levels' 
                                  for m in MODELS.keys() 
                                  if a['total_miu_levels_affected'][m] == 5}
            }
            for a in all_miu_affected
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {output_file}")
    print("="*80)

if __name__ == "__main__":
    main()

