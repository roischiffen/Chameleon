#!/usr/bin/env python3
"""
Investigate questions where resilient models (GPT-5, GPT-4o) got wrong on baseline
but correct on distorted versions. This helps verify the resilience claims.
"""

import json
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path("/Users/schiffen/RESEARCH-PROJECT-REPO/Chameleon/omnimath_distortion_workflow")
BASELINE_DIR = BASE_DIR / "evaluation" / "baseline_results"
DISTORTION_DIR = BASE_DIR / "evaluation" / "distortion_results"

# Focus on the "resilient" models
RESILIENT_MODELS = ["gpt_5", "gpt_4o"]
MODEL_DISPLAY_NAMES = {
    "gpt_5": "GPT-5",
    "gpt_4o": "GPT-4o"
}
DIFFICULTIES = [1.0, 1.5]
MIU_LEVELS = [0.2, 0.5, 0.7, 0.9]


def load_baseline_results(model: str, difficulty: float):
    """Load baseline results with full details."""
    folder = f"{model}_difficulty_{difficulty}".replace(".", "_")
    results_file = BASELINE_DIR / folder / "results.json"
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    return {r['question_id']: r for r in results}


def load_distortion_results(model: str, difficulty: float):
    """Load distortion results with full details."""
    folder = f"{model}_difficulty_{difficulty}".replace(".", "_")
    results_file = DISTORTION_DIR / folder / "results.jsonl"
    
    miu_results = defaultdict(dict)
    
    with open(results_file, 'r') as f:
        for line in f:
            r = json.loads(line.strip())
            miu = r['miu']
            qid = r['question_id']
            miu_results[miu][qid] = r
    
    return dict(miu_results)


def investigate_gained_questions():
    """Find and display questions where baseline was wrong but distortion was correct."""
    
    all_gained = []
    
    for model in RESILIENT_MODELS:
        display_name = MODEL_DISPLAY_NAMES[model]
        
        for diff in DIFFICULTIES:
            print(f"\n{'='*80}")
            print(f"Model: {display_name}, Difficulty: {diff}")
            print('='*80)
            
            baseline = load_baseline_results(model, diff)
            distortion = load_distortion_results(model, diff)
            
            gained_count = 0
            
            for miu in MIU_LEVELS:
                if miu not in distortion:
                    continue
                
                dist_data = distortion[miu]
                
                for qid, base_result in baseline.items():
                    if qid not in dist_data:
                        continue
                    
                    dist_result = dist_data[qid]
                    
                    # Find "gained" questions: baseline wrong, distortion correct
                    if not base_result['is_correct'] and dist_result['is_correct']:
                        gained_count += 1
                        
                        record = {
                            'model': display_name,
                            'difficulty': diff,
                            'miu': miu,
                            'question_id': qid,
                            'question': base_result.get('question', 'N/A'),
                            'distorted_question': dist_result.get('question', 'N/A'),
                            'ground_truth': base_result.get('ground_truth', 'N/A'),
                            'baseline_answer': base_result.get('model_answer', 'N/A'),
                            'distorted_answer': dist_result.get('model_answer', 'N/A'),
                            'domain': base_result.get('domain', 'N/A')
                        }
                        all_gained.append(record)
                        
                        print(f"\n--- Question ID: {qid} (MIU {miu}) ---")
                        print(f"Domain: {record['domain']}")
                        print(f"\nOriginal Question:\n{record['question'][:500]}...")
                        if record['distorted_question'] != 'N/A':
                            print(f"\nDistorted Question:\n{record['distorted_question'][:500]}...")
                        print(f"\nGround Truth: {record['ground_truth']}")
                        print(f"Baseline Answer (WRONG): {record['baseline_answer']}")
                        print(f"Distorted Answer (CORRECT): {record['distorted_answer']}")
            
            print(f"\nTotal gained for {display_name} D{diff}: {gained_count}")
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY OF GAINED QUESTIONS FOR RESILIENT MODELS")
    print('='*80)
    
    # Group by model
    by_model = defaultdict(list)
    for rec in all_gained:
        by_model[rec['model']].append(rec)
    
    for model, records in by_model.items():
        print(f"\n{model}: {len(records)} total gained questions")
        
        # Group by MIU
        by_miu = defaultdict(list)
        for rec in records:
            by_miu[rec['miu']].append(rec)
        
        for miu in sorted(by_miu.keys()):
            print(f"  MIU {miu}: {len(by_miu[miu])} questions")
    
    # Save detailed results
    output_file = BASE_DIR / "statistical_analysis_report" / "gained_questions_investigation.json"
    with open(output_file, 'w') as f:
        json.dump(all_gained, f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")
    
    return all_gained


if __name__ == "__main__":
    investigate_gained_questions()



