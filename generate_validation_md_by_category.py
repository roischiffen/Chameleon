#!/usr/bin/env python3
"""
Generate validation MD files organized by category and model.
Works with the new category-based results structure.
"""

import json
from pathlib import Path
from typing import Dict, List, Any


def load_json(filepath: str) -> Any:
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_markdown_for_category(
    category: str,
    model_name: str,
    results: List[Dict],
    start_idx: int,
    end_idx: int
) -> str:
    """Generate markdown content for a batch of questions in a category."""
    
    display_model_name = model_name.upper().replace('_', '-')
    
    md_content = f"""# Model Answer Validation Report
## Category {category} - {display_model_name}
## Questions {start_idx + 1} to {end_idx}

**IMPORTANT VALIDATION INSTRUCTIONS:**

For each question below, you must evaluate whether the model's answers are:
1. **CORRECT** - The answer matches the ground truth or is mathematically equivalent
2. **DISTORTION-CAUSED** - The answer differs because the distorted question legitimately changed what should be answered
3. **EMPTY** - No answer was provided (marked as None or empty)
4. **EQUIVALENT** - Different string representation but same mathematical value (e.g., "1/2" vs "0.5")
5. **INCORRECT** - The model made an actual mistake

---

"""
    
    questions_to_process = results[start_idx:end_idx]
    
    for idx, question in enumerate(questions_to_process, start=start_idx + 1):
        md_content += f"## Question {idx} (ID: {question['question_id']})\n\n"
        md_content += f"**Category:** {category}\n\n"
        md_content += f"**Domain:** {', '.join(question.get('domain', ['N/A']))}\n\n"
        md_content += f"**Source:** {question.get('source', 'N/A')}\n\n"
        
        # Original question and ground truth
        md_content += "### Original Question & Ground Truth\n\n"
        md_content += f"**Question:** {question['original_problem']}\n\n"
        md_content += f"**Ground Truth Answer:** `{question['ground_truth_answer']}`\n\n"
        
        # Baseline answer
        baseline = question['model_answers']['baseline']
        md_content += "### Model Answer on Baseline (No Distortion - miu 0.0)\n\n"
        md_content += f"**Question:** {baseline['problem']}\n\n"
        baseline_answer = baseline['answer'] if baseline['answer'] else '[EMPTY ANSWER]'
        md_content += f"**Model Answer:** `{baseline_answer}`\n\n"
        
        # Distorted questions and answers
        miu_descriptions = {
            'miu_0.2': 'Synonym Substitution',
            'miu_0.5': 'Notation Variation',
            'miu_0.7': 'Format Conversion',
            'miu_0.9': 'Maximum Distortion'
        }
        
        for miu_key in ['miu_0.2', 'miu_0.5', 'miu_0.7', 'miu_0.9']:
            if miu_key in question['model_answers']['distortions']:
                distortion = question['model_answers']['distortions'][miu_key]
                miu_level = str(distortion['miu'])
                
                md_content += f"### Distortion Level {miu_level} - {miu_descriptions[miu_key]}\n\n"
                md_content += f"**Distorted Question:** {distortion['problem']}\n\n"
                
                model_answer = distortion['answer'] if distortion['answer'] else '[EMPTY ANSWER]'
                md_content += f"**Model Answer:** `{model_answer}`\n\n"
        
        md_content += "### YOUR VALIDATION TASK FOR THIS QUESTION:\n\n"
        md_content += "For EACH of the 5 answers above (baseline + 4 distortions), provide:\n\n"
        md_content += "```\n"
        md_content += f"Question {idx} - {question['question_id']}:\n"
        md_content += f"  Baseline (miu 0.0): [STATUS] - [REASONING]\n"
        md_content += f"  miu 0.2: [STATUS] - [REASONING]\n"
        md_content += f"  miu 0.5: [STATUS] - [REASONING]\n"
        md_content += f"  miu 0.7: [STATUS] - [REASONING]\n"
        md_content += f"  miu 0.9: [STATUS] - [REASONING]\n"
        md_content += "```\n\n"
        md_content += "**STATUS must be one of:** CORRECT | DISTORTION-CAUSED | EMPTY | EQUIVALENT | INCORRECT\n\n"
        md_content += "**REASONING:** Brief explanation (1-2 sentences) of why you chose this status.\n\n"
        md_content += "---\n\n"
    
    md_content += f"""
## FINAL SUMMARY FORMAT

After reviewing all questions, provide a summary in this exact format:

```
VALIDATION SUMMARY - Category {category} - {display_model_name}
Questions {start_idx + 1} to {end_idx}:

STATISTICS:
- Total answers evaluated: [NUMBER]
- CORRECT: [NUMBER] ([PERCENTAGE]%)
- DISTORTION-CAUSED: [NUMBER] ([PERCENTAGE]%)
- EMPTY: [NUMBER] ([PERCENTAGE]%)
- EQUIVALENT: [NUMBER] ([PERCENTAGE]%)
- INCORRECT: [NUMBER] ([PERCENTAGE]%)

CRITICAL FINDINGS:
[List any patterns, systematic issues, or important observations]

QUESTIONS REQUIRING HUMAN REVIEW:
[List question IDs where you're uncertain about the classification]
```
"""
    
    return md_content


def main():
    """Main function to generate validation MD files by category."""
    
    base_path = Path("/Users/schiffen/RESEARCH-PROJECT-REPO/Chameleon/data/results_by_category")
    output_dir = Path("/Users/schiffen/RESEARCH-PROJECT-REPO/Chameleon/validation_files")
    output_dir.mkdir(exist_ok=True)
    
    # Get all categories
    categories = ['1', '2', '3']
    
    # Get all models
    models = ['gpt_4_1', 'gpt_5', 'gpt_5_mini']
    
    print("Generating validation files by category and model...")
    print("="*60)
    
    for category in categories:
        category_path = base_path / f"category_{category}"
        
        if not category_path.exists():
            print(f"⚠ Category {category} directory not found")
            continue
        
        print(f"\nCategory {category}:")
        
        for model in models:
            model_file = category_path / f"{model}_results.json"
            
            if not model_file.exists():
                print(f"  ⚠ {model} results not found")
                continue
            
            # Load results
            results = load_json(str(model_file))
            total_questions = len(results)
            
            # Generate batches (50 questions each)
            num_batches = (total_questions + 49) // 50
            
            print(f"  {model}: {total_questions} questions, {num_batches} batch(es)")
            
            for batch_num in range(num_batches):
                start_idx = batch_num * 50
                end_idx = min(start_idx + 50, total_questions)
                
                md_content = generate_markdown_for_category(
                    category,
                    model,
                    results,
                    start_idx,
                    end_idx
                )
                
                # Save to file
                output_file = output_dir / f"cat{category}_{model}_batch{batch_num + 1}.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                print(f"    ✓ Batch {batch_num + 1} (Q{start_idx + 1}-{end_idx}): {output_file.name}")
    
    print("\n" + "="*60)
    print("VALIDATION FILES GENERATED!")
    print("="*60)
    print(f"Location: {output_dir}")
    print("\nFile naming: cat[CATEGORY]_[MODEL]_batch[NUMBER].md")
    print("\nExample workflow:")
    print("  1. Start with cat1_gpt_4_1_batch1.md")
    print("  2. Send to Claude with CLAUDE_VALIDATION_PROMPT.md")
    print("  3. Get validation report")
    print("  4. Process batch 2, then other models, then other categories")
    print("="*60)


if __name__ == "__main__":
    main()

