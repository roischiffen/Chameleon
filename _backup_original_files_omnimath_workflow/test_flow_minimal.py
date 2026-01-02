#!/usr/bin/env python3
"""
🦎 Chameleon - Minimal Flow Test
================================
Tests the REAL pipeline with a subset of existing data:
- Uses existing chameleon_dataset.csv (NO downloads!)
- 50 questions × 3-4 μ levels = ~150-200 test cases
- Calls actual gpt5_manager.py functions

Usage:
    python3 test_flow_minimal.py --dry-run    # Test without API calls
    python3 test_flow_minimal.py --submit     # Actually submit to OpenAI
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_step(step_num, title):
    print(f"\n{'─' * 50}")
    print(f"  Step {step_num}: {title}")
    print(f"{'─' * 50}")

class MinimalFlowTest:
    """Test the Chameleon flow with a small subset of data"""
    
    def __init__(self, num_questions=50, miu_levels=None):
        self.num_questions = num_questions
        self.miu_levels = miu_levels or [0.0, 0.3, 0.6, 0.9]  # 4 levels by default
        
        # Paths
        self.original_csv = Path("distortions/chameleon_dataset.csv")
        self.test_csv = Path("distortions/test_subset_dataset.csv")
        self.test_batch_dir = Path("batches/test")
        self.test_results_dir = Path("test_results")
        
        # Create directories
        self.test_batch_dir.mkdir(parents=True, exist_ok=True)
        self.test_results_dir.mkdir(parents=True, exist_ok=True)
        
    def step1_create_subset(self):
        """Create a subset of the existing dataset"""
        print_step(1, "Creating Test Subset from Existing Data")
        
        if not self.original_csv.exists():
            raise FileNotFoundError(f"❌ Original dataset not found: {self.original_csv}")
        
        print(f"📂 Loading: {self.original_csv}")
        df = pd.read_csv(self.original_csv)
        print(f"   Total rows in original: {len(df):,}")
        
        # Get unique original questions (to ensure we get truly different questions)
        unique_questions = df['original_question'].unique()
        print(f"   Unique questions available: {len(unique_questions):,}")
        
        # Sample N unique questions
        sample_questions = list(unique_questions[:self.num_questions])
        print(f"   Selecting {len(sample_questions)} questions")
        
        # Filter to selected questions AND selected miu levels
        subset = df[
            (df['original_question'].isin(sample_questions)) &
            (df['miu'].isin(self.miu_levels))
        ].copy()
        
        print(f"\n📊 Subset Statistics:")
        print(f"   Questions: {subset['original_question'].nunique()}")
        print(f"   μ levels: {sorted(subset['miu'].unique())}")
        print(f"   Total rows: {len(subset):,}")
        
        # Show breakdown by miu
        print(f"\n   Breakdown by μ:")
        for miu in sorted(subset['miu'].unique()):
            count = len(subset[subset['miu'] == miu])
            print(f"     μ={miu}: {count} rows")
        
        # Save subset
        subset.to_csv(self.test_csv, index=False)
        print(f"\n💾 Saved subset to: {self.test_csv}")
        
        return subset
    
    def step2_create_batch_requests(self, df):
        """Create batch request files using gpt5_manager logic"""
        print_step(2, "Creating Batch Requests (Using Real Logic)")
        
        # We'll manually create requests using the same format as gpt5_manager
        batch_requests = []
        
        for idx, row in df.iterrows():
            try:
                answer_options = json.loads(row['answer_options'])
                question_text = row['distorted_question']
                choices_text = "\n".join([f"{k}: {v}" for k, v in answer_options.items()])
                custom_id = f"test_q_{idx}"
                
                # Same format as GPT5BatchManager.create_batches()
                request = {
                    "custom_id": custom_id,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "gpt-4o-mini",  # Use cheaper model for testing!
                        "messages": [
                            {
                                "role": "user",
                                "content": f"EVALUATION TASK: You will receive +1 point for choosing the correct answer and -2 points for any incorrect choice. Your goal is to maximize your score.\n\nINSTRUCTIONS:\n- Read the question carefully\n- Analyze all four options (A, B, C, D)\n- Choose the ONE most correct answer\n- Respond with ONLY the letter (A, B, C, or D)\n- No explanations, no additional text, no reasoning shown\n- Wrong answers result in -2 points, correct answers give +1 point\n\nQUESTION:\n{question_text}\n\nOPTIONS:\n{choices_text}\n\nYour answer (single letter only):"
                            }
                        ],
                        "max_completion_tokens": 10  # Much smaller for single letter!
                    }
                }
                batch_requests.append(request)
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"   ⚠️ Skipping row {idx}: {e}")
                continue
        
        print(f"✅ Created {len(batch_requests)} batch requests")
        
        # Save to JSONL file
        batch_file = self.test_batch_dir / "test_batch.jsonl"
        with open(batch_file, 'w') as f:
            for request in batch_requests:
                f.write(json.dumps(request) + '\n')
        
        file_size_kb = batch_file.stat().st_size / 1024
        print(f"💾 Saved to: {batch_file} ({file_size_kb:.1f} KB)")
        
        return batch_file, batch_requests
    
    def step3_validate_batch_format(self, batch_file):
        """Validate the batch file format"""
        print_step(3, "Validating Batch Format")
        
        valid_count = 0
        error_count = 0
        
        with open(batch_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    request = json.loads(line)
                    
                    # Validate required fields
                    assert 'custom_id' in request, "Missing custom_id"
                    assert 'method' in request, "Missing method"
                    assert 'url' in request, "Missing url"
                    assert 'body' in request, "Missing body"
                    assert 'model' in request['body'], "Missing model"
                    assert 'messages' in request['body'], "Missing messages"
                    
                    valid_count += 1
                    
                except (json.JSONDecodeError, AssertionError) as e:
                    print(f"   ❌ Line {line_num}: {e}")
                    error_count += 1
        
        print(f"\n📊 Validation Results:")
        print(f"   ✅ Valid requests: {valid_count}")
        print(f"   ❌ Invalid requests: {error_count}")
        
        return error_count == 0
    
    def step4_submit_batch(self, batch_file, dry_run=True):
        """Submit the batch to OpenAI (optional)"""
        print_step(4, "Submitting Batch to OpenAI")
        
        if dry_run:
            print("🔸 DRY RUN MODE - Not actually submitting")
            print("   To submit for real, run with --submit flag")
            return None
        
        # Check for API key
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY not found!")
            print("   Set it in .env file or environment")
            return None
        
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        print(f"📤 Uploading batch file...")
        
        try:
            # Upload file
            with open(batch_file, "rb") as f:
                batch_input_file = client.files.create(file=f, purpose="batch")
            
            print(f"   File ID: {batch_input_file.id}")
            
            # Create batch
            batch = client.batches.create(
                input_file_id=batch_input_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={"description": f"Chameleon Test Batch - {datetime.now().isoformat()}"}
            )
            
            print(f"\n✅ Batch submitted successfully!")
            print(f"   Batch ID: {batch.id}")
            print(f"   Status: {batch.status}")
            
            # Save batch info
            batch_info = {
                'batch_id': batch.id,
                'file_id': batch_input_file.id,
                'submitted_at': datetime.now().isoformat(),
                'status': batch.status
            }
            
            info_file = self.test_results_dir / "test_batch_info.json"
            with open(info_file, 'w') as f:
                json.dump(batch_info, f, indent=2)
            
            print(f"\n💾 Batch info saved to: {info_file}")
            print(f"\n📊 Monitor with:")
            print(f"   python3 chameleon.py monitor")
            
            return batch.id
            
        except Exception as e:
            print(f"❌ Submission failed: {e}")
            return None
    
    def step5_estimate_cost(self, num_requests):
        """Estimate API cost"""
        print_step(5, "Cost Estimation")
        
        # Rough estimates for gpt-4o-mini
        input_tokens_per_request = 300  # Approximate
        output_tokens_per_request = 5   # Just a letter
        
        total_input = num_requests * input_tokens_per_request
        total_output = num_requests * output_tokens_per_request
        
        # gpt-4o-mini pricing (as of 2024)
        input_cost = (total_input / 1_000_000) * 0.15   # $0.15 per 1M input tokens
        output_cost = (total_output / 1_000_000) * 0.60  # $0.60 per 1M output tokens
        total_cost = input_cost + output_cost
        
        print(f"📊 Estimated Cost (gpt-4o-mini):")
        print(f"   Requests: {num_requests}")
        print(f"   Input tokens: ~{total_input:,}")
        print(f"   Output tokens: ~{total_output:,}")
        print(f"   Estimated cost: ${total_cost:.4f}")
        
        return total_cost
    
    def run_full_test(self, submit=False):
        """Run the complete test flow"""
        print("\n")
        print("╔" + "═" * 58 + "╗")
        print("║" + " " * 58 + "║")
        print("║" + "  🦎 CHAMELEON - MINIMAL FLOW TEST".center(58) + "║")
        print("║" + " " * 58 + "║")
        print("║" + f"  Questions: {self.num_questions}".ljust(58) + "║")
        print("║" + f"  μ Levels: {self.miu_levels}".ljust(58) + "║")
        print("║" + f"  Mode: {'SUBMIT' if submit else 'DRY RUN'}".ljust(58) + "║")
        print("║" + " " * 58 + "║")
        print("╚" + "═" * 58 + "╝")
        
        # Step 1: Create subset
        df = self.step1_create_subset()
        
        # Step 2: Create batch requests
        batch_file, requests = self.step2_create_batch_requests(df)
        
        # Step 3: Validate format
        is_valid = self.step3_validate_batch_format(batch_file)
        
        if not is_valid:
            print("\n❌ Batch validation failed! Fix errors before submitting.")
            return False
        
        # Step 4: Submit (or dry run)
        batch_id = self.step4_submit_batch(batch_file, dry_run=not submit)
        
        # Step 5: Cost estimate
        self.step5_estimate_cost(len(requests))
        
        # Summary
        print_header("🎉 Test Complete!")
        print(f"\n📁 Generated files:")
        print(f"   • {self.test_csv}")
        print(f"   • {batch_file}")
        
        if batch_id:
            print(f"\n🚀 Batch submitted: {batch_id}")
        else:
            print(f"\n💡 To submit for real:")
            print(f"   python3 test_flow_minimal.py --submit")
        
        return True


def main():
    parser = argparse.ArgumentParser(description='Chameleon Minimal Flow Test')
    parser.add_argument('--questions', '-n', type=int, default=50,
                        help='Number of questions to test (default: 50)')
    parser.add_argument('--miu', '-m', type=float, nargs='+', 
                        default=[0.0, 0.3, 0.6, 0.9],
                        help='μ levels to test (default: 0.0 0.3 0.6 0.9)')
    parser.add_argument('--submit', action='store_true',
                        help='Actually submit to OpenAI (default: dry run)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Dry run - do not submit (default)')
    
    args = parser.parse_args()
    
    test = MinimalFlowTest(
        num_questions=args.questions,
        miu_levels=args.miu
    )
    
    test.run_full_test(submit=args.submit)


if __name__ == "__main__":
    main()
