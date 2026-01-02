# Distortion Evaluation Guide

This guide explains how to evaluate GPT-4o and GPT-5-mini (o4-mini) on the distorted questions from difficulty levels 1.0 and 1.5.

## 📊 Evaluation Overview

| Difficulty | Questions | μ Levels               | Total per Model |
| ---------- | --------- | ---------------------- | --------------- |
| 1.0        | 100       | 4 (0.2, 0.5, 0.7, 0.9) | 400             |
| 1.5        | 100       | 4 (0.2, 0.5, 0.7, 0.9) | 400             |
| **Total**  | 200       | -                      | **800**         |

**For both models: 800 × 2 = 1,600 total API calls**

## 💰 Cost Optimization: Batch API (50% Discount!)

OpenAI's Batch API provides **50% discount** on all API calls:

| API Type                     | Cost per 1M tokens                | Discount    |
| ---------------------------- | --------------------------------- | ----------- |
| Standard API (synchronous)   | $2.50 input / $10 output (GPT-4o) | -           |
| **Batch API (asynchronous)** | $1.25 input / $5 output (GPT-4o)  | **50% off** |

**Estimated Cost for Full Evaluation:**

- With Batch API: **~$2-4** total
- Without Batch API: **~$4-8** total

## 🚀 Quick Start: Run All Evaluations

The simplest way to run everything:

```bash
cd /Users/schiffen/RESEARCH-PROJECT-REPO/Chameleon

# Run complete evaluation (prepare + submit + wait + download + analyze)
python omnimath_distortion_workflow/flows/run_all_distortion_evaluations.py --run-all
```

This will:

1. ✅ Prepare batch files for all 4 evaluations (2 models × 2 difficulties)
2. ✅ Submit all batches to OpenAI (50% discount)
3. ⏳ Wait for completion (1-24 hours, typically 1-6 hours)
4. ✅ Download results as they complete
5. ✅ Generate analysis reports

**You can safely Ctrl+C at any time** - progress is saved and you can resume with:

```bash
python omnimath_distortion_workflow/flows/run_all_distortion_evaluations.py --resume
```

## 📋 Step-by-Step Evaluation

If you prefer more control:

### Step 1: Prepare Batch Files (No API calls)

```bash
# Prepare all batches
python omnimath_distortion_workflow/flows/run_all_distortion_evaluations.py --prepare-all

# Or prepare individually:
python omnimath_distortion_workflow/flows/evaluate_distortions_batch.py --prepare --model gpt-4o --difficulty 1.0
python omnimath_distortion_workflow/flows/evaluate_distortions_batch.py --prepare --model gpt-4o --difficulty 1.5
python omnimath_distortion_workflow/flows/evaluate_distortions_batch.py --prepare --model gpt-5-mini --difficulty 1.0
python omnimath_distortion_workflow/flows/evaluate_distortions_batch.py --prepare --model gpt-5-mini --difficulty 1.5
```

### Step 2: Submit to OpenAI

```bash
# Submit all batches
python omnimath_distortion_workflow/flows/run_all_distortion_evaluations.py --submit-all

# Or submit individually:
python omnimath_distortion_workflow/flows/evaluate_distortions_batch.py --submit --model gpt-4o --difficulty 1.0
```

### Step 3: Check Status

```bash
# Check all batch statuses
python omnimath_distortion_workflow/flows/run_all_distortion_evaluations.py --status

# Or check individually:
python omnimath_distortion_workflow/flows/evaluate_distortions_batch.py --status --model gpt-4o --difficulty 1.0
```

### Step 4: Wait for Completion

```bash
# Wait and auto-download as batches complete
python omnimath_distortion_workflow/flows/run_all_distortion_evaluations.py --wait
```

### Step 5: Analyze Results

```bash
# Analyze all results
python omnimath_distortion_workflow/flows/run_all_distortion_evaluations.py --analyze

# Or analyze individually:
python omnimath_distortion_workflow/flows/analyze_distortion_results.py --model gpt-4o --difficulty 1.0 --compare --save
```

## ⚡ Alternative: Direct API (Faster, No Discount)

If you need immediate results and don't mind paying full price:

```bash
# Test with 10 questions first
python omnimath_distortion_workflow/flows/evaluate_distortions_direct.py --model gpt-4o --difficulty 1.0 --test 10

# Run full evaluation
python omnimath_distortion_workflow/flows/evaluate_distortions_direct.py --model gpt-4o --difficulty 1.0

# Evaluate specific μ levels only
python omnimath_distortion_workflow/flows/evaluate_distortions_direct.py --model gpt-4o --difficulty 1.0 --miu 0.2,0.9
```

**Note:** Direct API saves after EVERY question, so you never lose progress.

## 📁 Output Directory Structure

```
omnimath_distortion_workflow/evaluation/
├── baseline_results/          # Your existing baseline results
│   ├── gpt4o_results.json
│   └── gpt5_mini_results.json
├── distortion_results/
│   ├── gpt_4o_difficulty_1_0/
│   │   ├── batch_requests.jsonl
│   │   ├── checkpoint.json
│   │   ├── results.jsonl
│   │   └── summary.json
│   ├── gpt_4o_difficulty_1_5/
│   ├── gpt_5_mini_difficulty_1_0/
│   └── gpt_5_mini_difficulty_1_5/
└── analysis/
    ├── gpt_4o_difficulty_1_0_analysis.json
    ├── gpt_4o_difficulty_1_0_analysis.md
    └── ...
```

## 🔧 Troubleshooting

### Batch stuck in "processing" for too long

Batches typically complete within 1-6 hours. If stuck after 24 hours:

1. Check status: `python evaluate_distortions_batch.py --status --model MODEL --difficulty DIFF`
2. OpenAI may be experiencing delays - wait or contact support

### Resume after crash/interruption

All scripts save progress incrementally. Just run again:

```bash
python run_all_distortion_evaluations.py --resume
```

### Rate limits with direct API

The direct API script automatically handles rate limits with exponential backoff. If you keep hitting limits:

- Use the Batch API instead (recommended)
- Increase `INITIAL_DELAY` in the script

### Check what results exist

```bash
python analyze_distortion_results.py --list
```

## 📊 Understanding Results

The analysis report shows:

1. **Accuracy by μ level:**

   - μ=0.2: Minimal distortion (synonym substitution)
   - μ=0.5: Moderate distortion (notation variation)
   - μ=0.7: Strong distortion (format conversion)
   - μ=0.9: Maximum distortion (combined effects)

2. **Degradation from baseline:**

   - Absolute: How many percentage points accuracy dropped
   - Relative: What % of baseline accuracy was lost

3. **Robustness Score:**
   - 100% = No degradation from distortions
   - 50% = Half of baseline accuracy on distorted questions
   - Measures model resilience to semantic distortions

## 🎯 Expected Results

Based on baseline performance (~95% accuracy), you might expect:

- μ=0.2: ~90-95% accuracy (minimal impact)
- μ=0.5: ~85-92% accuracy (moderate impact)
- μ=0.7: ~75-88% accuracy (noticeable impact)
- μ=0.9: ~65-80% accuracy (significant impact)

The key research question: **Which model degrades more gracefully under increasing distortion?**

## 📞 Commands Reference

| Command                                       | Description                             |
| --------------------------------------------- | --------------------------------------- |
| `run_all_distortion_evaluations.py --run-all` | Complete workflow                       |
| `run_all_distortion_evaluations.py --resume`  | Resume from checkpoint                  |
| `run_all_distortion_evaluations.py --status`  | Check all statuses                      |
| `evaluate_distortions_batch.py --run`         | Single model/difficulty with Batch API  |
| `evaluate_distortions_direct.py`              | Single model/difficulty with Direct API |
| `analyze_distortion_results.py --all`         | Analyze all results                     |
