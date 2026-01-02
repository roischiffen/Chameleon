#!/usr/bin/env python3
"""
🦎 Chameleon Framework - Pipeline Verification Test
====================================================

This script tests the complete Chameleon pipeline with GSM8K benchmark:
1. Loads questions from GSM8K dataset
2. Generates distorted versions using OpenAI API
3. Evaluates answers using GPT-4o-mini
4. Shows before/after comparisons
5. Displays accuracy results

Usage:
    python3 test_chameleon_pipeline.py

Requirements:
    - OpenAI API key set as environment variable
    - pip install -r requirements-test.txt

Author: Chameleon Framework Test Suite
"""

import os
import sys
import json
import time
import yaml
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Check for OpenAI API key first
def check_api_key():
    """Check if OpenAI API key is available"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n" + "="*60)
        print("❌ OPENAI_API_KEY not found!")
        print("="*60)
        print("\nPlease set your OpenAI API key:")
        print("\n  Option 1 (Terminal):")
        print("    export OPENAI_API_KEY='your-api-key-here'")
        print("\n  Option 2 (Create .env file in project root):")
        print("    echo 'OPENAI_API_KEY=your-api-key-here' > .env")
        print("\nGet your API key at: https://platform.openai.com/api-keys")
        print("="*60 + "\n")
        sys.exit(1)
    return api_key

# Run check before imports that need it
API_KEY = check_api_key()

# Now import OpenAI and other dependencies
try:
    from openai import OpenAI
    from datasets import load_dataset
    import matplotlib.pyplot as plt
    import seaborn as sns
    from tqdm import tqdm
except ImportError as e:
    print(f"\n❌ Missing dependency: {e}")
    print("\nPlease install required packages:")
    print("  pip install -r requirements-test.txt\n")
    sys.exit(1)

# Initialize OpenAI client
client = OpenAI(api_key=API_KEY)

# Configuration
NUM_QUESTIONS = 5
MIU_LEVELS = [0.0, 0.5, 0.9]
MODEL_DISTORTION = "gpt-4o-mini"
MODEL_EVALUATION = "gpt-4o-mini"

# Create output directory
OUTPUT_DIR = Path("test_results")
OUTPUT_DIR.mkdir(exist_ok=True)


def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_subheader(title):
    """Print a formatted subheader"""
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def load_gsm8k_questions(num_questions=5):
    """
    Load questions from GSM8K dataset
    
    Returns:
        list: List of question dictionaries with 'question', 'answer', and 'full_answer'
    """
    print_header("📚 STEP 1: Loading GSM8K Questions")
    
    print(f"\n🔄 Loading GSM8K dataset from HuggingFace...")
    
    try:
        # Load GSM8K dataset
        dataset = load_dataset("openai/gsm8k", "main", split="test")
        
        questions = []
        for i, item in enumerate(dataset):
            if i >= num_questions:
                break
            
            # Extract the numerical answer from the solution
            # GSM8K format: solution ends with "#### <number>"
            full_answer = item['answer']
            
            # Extract just the final number
            if '####' in full_answer:
                final_answer = full_answer.split('####')[-1].strip()
            else:
                final_answer = full_answer.strip()
            
            questions.append({
                'id': i + 1,
                'question': item['question'],
                'full_answer': full_answer,
                'correct_answer': final_answer
            })
        
        print(f"✅ Loaded {len(questions)} questions from GSM8K\n")
        
        # Display loaded questions
        for q in questions:
            print(f"  Question {q['id']}:")
            # Truncate long questions for display
            q_display = q['question'][:100] + "..." if len(q['question']) > 100 else q['question']
            print(f"    \"{q_display}\"")
            print(f"    Answer: {q['correct_answer']}\n")
        
        return questions
        
    except Exception as e:
        print(f"❌ Error loading GSM8K: {e}")
        print("\nUsing fallback sample questions...")
        
        # Fallback questions if dataset fails to load
        return [
            {
                'id': 1,
                'question': "Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder at the farmers' market daily for $2 per fresh duck egg. How much in dollars does she make every day at the farmers' market?",
                'full_answer': "Janet sells 16 - 3 - 4 = 9 duck eggs a day. She makes 9 * 2 = $18 every day. #### 18",
                'correct_answer': "18"
            },
            {
                'id': 2,
                'question': "A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts in total does it take?",
                'full_answer': "It takes 2/2=1 bolt of white fiber. So the total is 2+1=3 bolts. #### 3",
                'correct_answer': "3"
            },
            {
                'id': 3,
                'question': "Josh decides to try flipping a house. He buys a house for $80,000 and then puts in $50,000 in repairs. This increased the value of the house by 150%. How much profit did he make?",
                'full_answer': "The cost of the house and repairs came out to 80,000+50,000=$130,000. He increased the value of the house by 80,000*1.5=120,000. So the new value is 120,000+80,000=$200,000. So he made a profit of 200,000-130,000=$70,000. #### 70000",
                'correct_answer': "70000"
            },
            {
                'id': 4,
                'question': "James decides to run 3 sprints 3 times a week. He runs 60 meters each sprint. How many total meters does he run a week?",
                'full_answer': "He runs 3*3=9 sprints. So he runs 9*60=540 meters. #### 540",
                'correct_answer': "540"
            },
            {
                'id': 5,
                'question': "Every day, Wendi feeds each of her chickens three cups of mixed chicken feed, containing seeds, mealworms and vegetables to help keep them healthy. She gives the chickens their feed in three separate meals. In the morning, she gives her flock of chickens 15 cups of feed. In the afternoon, she gives her chickens another 25 cups of feed. How many cups of feed does she need to give her chickens in the final meal of the day if the size of Wendi's flock is 20 chickens?",
                'full_answer': "Wendi needs to give her chickens 20*3=60 cups per day. She already gave them 15+25=40 cups. So she needs to give them 60-40=20 more cups. #### 20",
                'correct_answer': "20"
            }
        ]


def get_distortion_prompt(question, miu_level):
    """
    Create prompt for distorting a question based on μ level
    """
    if miu_level == 0.0:
        return None  # No distortion needed for baseline
    
    if miu_level <= 0.3:
        intensity = "minimal"
        instruction = "Make only 1-2 minor word substitutions using simple synonyms. Keep the exact same sentence structure."
    elif miu_level <= 0.6:
        intensity = "moderate"
        instruction = "Rephrase the question with different words and some restructuring, but maintain clarity. Use synonyms and change sentence flow slightly."
    else:
        intensity = "heavy"
        instruction = "Significantly paraphrase the question. Use very different wording, restructure sentences, but keep the exact same mathematical problem and all numerical values unchanged."
    
    prompt = f"""You are a question paraphrasing expert. Your task is to create a {intensity} distortion of the following math question.

RULES:
1. {instruction}
2. Keep ALL numerical values EXACTLY the same
3. The mathematical problem must remain identical
4. The answer must remain the same
5. Do NOT solve the problem - only rephrase the question
6. Return ONLY the rephrased question, nothing else

ORIGINAL QUESTION:
{question}

REPHRASED QUESTION:"""
    
    return prompt


def generate_distortions(questions, miu_levels):
    """
    Generate distorted versions of questions using OpenAI API
    
    Returns:
        list: List of dictionaries with original and distorted questions
    """
    print_header("🔄 STEP 2: Generating Distortions")
    
    print(f"\n📊 Settings:")
    print(f"   • Questions: {len(questions)}")
    print(f"   • μ levels: {miu_levels}")
    print(f"   • Model: {MODEL_DISTORTION}")
    print(f"   • Total distortions to generate: {len(questions) * len(miu_levels)}")
    
    all_distortions = []
    
    for q in tqdm(questions, desc="Processing questions"):
        for miu in miu_levels:
            distortion_entry = {
                'question_id': q['id'],
                'original_question': q['question'],
                'correct_answer': q['correct_answer'],
                'miu': miu,
                'distorted_question': None
            }
            
            if miu == 0.0:
                # Baseline - no distortion
                distortion_entry['distorted_question'] = q['question']
            else:
                # Generate distortion using OpenAI
                prompt = get_distortion_prompt(q['question'], miu)
                
                try:
                    response = client.chat.completions.create(
                        model=MODEL_DISTORTION,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7 + (miu * 0.5),  # Higher temp for higher distortion
                        max_tokens=500
                    )
                    distortion_entry['distorted_question'] = response.choices[0].message.content.strip()
                    
                except Exception as e:
                    print(f"\n⚠️  Error generating distortion for Q{q['id']} at μ={miu}: {e}")
                    distortion_entry['distorted_question'] = q['question']  # Fallback to original
            
            all_distortions.append(distortion_entry)
            time.sleep(0.1)  # Small delay to avoid rate limits
    
    print(f"\n✅ Generated {len(all_distortions)} distorted questions")
    
    return all_distortions


def display_distortion_comparison(distortions, questions):
    """
    Display side-by-side comparison of original vs distorted questions
    """
    print_header("👁️ STEP 3: Viewing Distortions (Before vs After)")
    
    for q in questions:
        print_subheader(f"Question {q['id']}")
        
        # Get all distortions for this question
        q_distortions = [d for d in distortions if d['question_id'] == q['id']]
        
        for d in q_distortions:
            miu = d['miu']
            
            if miu == 0.0:
                label = "📝 ORIGINAL (μ=0.0 - Baseline)"
            elif miu <= 0.3:
                label = f"🟢 LIGHT DISTORTION (μ={miu})"
            elif miu <= 0.6:
                label = f"🟡 MEDIUM DISTORTION (μ={miu})"
            else:
                label = f"🔴 HEAVY DISTORTION (μ={miu})"
            
            print(f"\n{label}:")
            print(f"  \"{d['distorted_question']}\"")
        
        print(f"\n  ✓ Correct Answer: {q['correct_answer']}")
        print()


def evaluate_with_llm(distortions):
    """
    Send distorted questions to GPT-4o-mini for evaluation
    
    Returns:
        list: Distortions with added 'llm_answer' and 'is_correct' fields
    """
    print_header("🤖 STEP 4: LLM Evaluation")
    
    print(f"\n📊 Evaluating {len(distortions)} questions with {MODEL_EVALUATION}...")
    
    evaluation_prompt_template = """You are solving a math word problem. 

IMPORTANT: 
- Solve the problem step by step
- Give your final answer as JUST A NUMBER on the last line
- Format: #### <number>

QUESTION:
{question}

Solve this problem:"""

    for d in tqdm(distortions, desc="Evaluating"):
        prompt = evaluation_prompt_template.format(question=d['distorted_question'])
        
        try:
            response = client.chat.completions.create(
                model=MODEL_EVALUATION,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # Deterministic for evaluation
                max_tokens=500
            )
            
            answer_text = response.choices[0].message.content.strip()
            
            # Extract numerical answer
            if '####' in answer_text:
                llm_answer = answer_text.split('####')[-1].strip()
            else:
                # Try to find the last number in the response
                import re
                numbers = re.findall(r'-?\d+\.?\d*', answer_text)
                llm_answer = numbers[-1] if numbers else answer_text
            
            d['llm_answer'] = llm_answer
            d['llm_full_response'] = answer_text
            
            # Check correctness (handle potential formatting differences)
            try:
                correct_num = float(d['correct_answer'].replace(',', '').replace('$', ''))
                llm_num = float(llm_answer.replace(',', '').replace('$', ''))
                d['is_correct'] = abs(correct_num - llm_num) < 0.01
            except:
                d['is_correct'] = d['correct_answer'].strip() == llm_answer.strip()
            
        except Exception as e:
            print(f"\n⚠️  Error evaluating Q{d['question_id']} at μ={d['miu']}: {e}")
            d['llm_answer'] = "ERROR"
            d['is_correct'] = False
        
        time.sleep(0.1)  # Rate limit protection
    
    print(f"\n✅ Evaluation complete!")
    
    return distortions


def display_evaluation_results(distortions):
    """
    Display the evaluation results for each question
    """
    print_header("📊 STEP 5: Evaluation Results")
    
    # Group by question
    question_ids = sorted(set(d['question_id'] for d in distortions))
    
    for q_id in question_ids:
        print_subheader(f"Question {q_id} Results")
        
        q_results = [d for d in distortions if d['question_id'] == q_id]
        
        for d in q_results:
            miu = d['miu']
            status = "✅ CORRECT" if d['is_correct'] else "❌ WRONG"
            
            print(f"\n  μ={miu}:")
            print(f"    Model answer: {d['llm_answer']}")
            print(f"    Correct answer: {d['correct_answer']}")
            print(f"    Result: {status}")


def calculate_accuracy_by_miu(distortions):
    """
    Calculate accuracy statistics by μ level
    
    Returns:
        DataFrame: Accuracy statistics
    """
    df = pd.DataFrame(distortions)
    
    stats = df.groupby('miu').agg(
        total=('is_correct', 'count'),
        correct=('is_correct', 'sum'),
        accuracy=('is_correct', 'mean')
    ).reset_index()
    
    stats['accuracy_pct'] = stats['accuracy'] * 100
    
    # Calculate degradation from baseline
    baseline_acc = stats[stats['miu'] == 0.0]['accuracy_pct'].values[0]
    stats['degradation'] = baseline_acc - stats['accuracy_pct']
    
    return stats


def display_summary(distortions):
    """
    Display final summary statistics
    """
    print_header("📈 STEP 6: Final Summary")
    
    stats = calculate_accuracy_by_miu(distortions)
    
    print("\n" + "┌" + "─"*58 + "┐")
    print(f"│{'μ Level':^12}│{'Correct':^12}│{'Total':^10}│{'Accuracy':^12}│{'Degradation':^12}│")
    print("├" + "─"*12 + "┼" + "─"*12 + "┼" + "─"*10 + "┼" + "─"*12 + "┼" + "─"*12 + "┤")
    
    for _, row in stats.iterrows():
        miu = row['miu']
        correct = int(row['correct'])
        total = int(row['total'])
        acc = row['accuracy_pct']
        deg = row['degradation']
        
        deg_str = f"{deg:+.1f}%" if miu > 0 else "baseline"
        print(f"│{miu:^12.1f}│{correct:^12}│{total:^10}│{acc:^11.1f}%│{deg_str:^12}│")
    
    print("└" + "─"*58 + "┘")
    
    # Overall statistics
    total_correct = sum(1 for d in distortions if d['is_correct'])
    total_questions = len(distortions)
    overall_acc = (total_correct / total_questions) * 100
    
    print(f"\n📊 Overall Statistics:")
    print(f"   • Total evaluations: {total_questions}")
    print(f"   • Correct answers: {total_correct}")
    print(f"   • Overall accuracy: {overall_acc:.1f}%")
    
    return stats


def create_visualization(distortions, stats):
    """
    Create a simple visualization of the results
    """
    print_header("📊 STEP 7: Creating Visualization")
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Plot 1: Accuracy by μ level
    ax1 = axes[0]
    colors = ['#2ecc71' if m == 0.0 else '#f39c12' if m <= 0.5 else '#e74c3c' for m in stats['miu']]
    bars = ax1.bar(stats['miu'].astype(str), stats['accuracy_pct'], color=colors, edgecolor='black')
    ax1.set_xlabel('Distortion Level (μ)', fontsize=12)
    ax1.set_ylabel('Accuracy (%)', fontsize=12)
    ax1.set_title('GPT-4o-mini Accuracy by Distortion Level', fontsize=14, fontweight='bold')
    ax1.set_ylim(0, 105)
    
    # Add value labels on bars
    for bar, acc in zip(bars, stats['accuracy_pct']):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
                f'{acc:.0f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # Plot 2: Degradation from baseline
    ax2 = axes[1]
    non_baseline = stats[stats['miu'] > 0]
    colors2 = ['#f39c12' if d < 20 else '#e74c3c' for d in non_baseline['degradation']]
    bars2 = ax2.bar(non_baseline['miu'].astype(str), non_baseline['degradation'], color=colors2, edgecolor='black')
    ax2.set_xlabel('Distortion Level (μ)', fontsize=12)
    ax2.set_ylabel('Performance Degradation (%)', fontsize=12)
    ax2.set_title('Performance Degradation from Baseline', fontsize=14, fontweight='bold')
    ax2.axhline(y=0, color='green', linestyle='--', linewidth=2, label='Baseline')
    
    # Add value labels
    for bar, deg in zip(bars2, non_baseline['degradation']):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{deg:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    
    # Save the plot
    output_path = OUTPUT_DIR / 'test_results_visualization.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Visualization saved to: {output_path}")
    
    plt.show()
    
    return output_path


def save_results(distortions, stats):
    """
    Save all results to files
    """
    print_header("💾 STEP 8: Saving Results")
    
    # Save distortions to CSV
    df = pd.DataFrame(distortions)
    csv_path = OUTPUT_DIR / 'test_distortions_results.csv'
    df.to_csv(csv_path, index=False)
    print(f"✅ Distortions saved to: {csv_path}")
    
    # Save statistics to CSV
    stats_path = OUTPUT_DIR / 'test_accuracy_stats.csv'
    stats.to_csv(stats_path, index=False)
    print(f"✅ Statistics saved to: {stats_path}")
    
    # Save detailed JSON
    json_path = OUTPUT_DIR / 'test_detailed_results.json'
    with open(json_path, 'w') as f:
        json.dump(distortions, f, indent=2)
    print(f"✅ Detailed results saved to: {json_path}")
    
    return csv_path, stats_path, json_path


def main():
    """
    Main function - runs the complete pipeline test
    """
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  🦎 CHAMELEON FRAMEWORK - PIPELINE VERIFICATION TEST".center(68) + "║")
    print("║" + " "*68 + "║")
    print("║" + f"  Model: {MODEL_EVALUATION}".ljust(68) + "║")
    print("║" + f"  Questions: {NUM_QUESTIONS}".ljust(68) + "║")
    print("║" + f"  μ Levels: {MIU_LEVELS}".ljust(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "═"*68 + "╝")
    
    start_time = time.time()
    
    # Step 1: Load questions
    questions = load_gsm8k_questions(NUM_QUESTIONS)
    
    # Step 2: Generate distortions
    distortions = generate_distortions(questions, MIU_LEVELS)
    
    # Step 3: Display distortion comparison
    display_distortion_comparison(distortions, questions)
    
    # Step 4: Evaluate with LLM
    distortions = evaluate_with_llm(distortions)
    
    # Step 5: Display evaluation results
    display_evaluation_results(distortions)
    
    # Step 6: Calculate and display summary
    stats = display_summary(distortions)
    
    # Step 7: Create visualization
    viz_path = create_visualization(distortions, stats)
    
    # Step 8: Save results
    csv_path, stats_path, json_path = save_results(distortions, stats)
    
    # Final summary
    elapsed_time = time.time() - start_time
    
    print_header("🎉 TEST COMPLETE!")
    print(f"\n⏱️  Total time: {elapsed_time:.1f} seconds")
    print(f"\n📁 Output files in '{OUTPUT_DIR}/':")
    print(f"   • test_distortions_results.csv")
    print(f"   • test_accuracy_stats.csv")
    print(f"   • test_detailed_results.json")
    print(f"   • test_results_visualization.png")
    
    print("\n" + "="*70)
    print("  You have successfully verified the Chameleon pipeline!")
    print("  Next steps: Modify config/test_config.yaml to test with more")
    print("  questions or different distortion levels.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

