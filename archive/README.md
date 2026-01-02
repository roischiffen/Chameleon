# Archived Files

This folder contains files that are no longer part of the active workflow but are preserved for reference.

## Structure

### `legacy_mmlu_workflow/`

Original MMLU-based distortion workflow files. These files were part of an earlier version of the Chameleon project that:

- Used the **MMLU (Massive Multitask Language Understanding)** benchmark
- Tested GPT-5 on 20 academic subjects
- Used 10 distortion levels (μ = 0.0 to 0.9)
- Processed 18,200 questions total

**Files archived:**
- `chameleon.py` - Main orchestration script
- `gpt5_manager.py` - GPT-5 batch management
- `monitor_repair.py` - Monitoring and repair utilities
- `clean_gpt5_answers.py` - Answer cleaning and validation
- `create_visualizations.py` - Visualization generation
- `statistical_analysis.py` - Statistical analysis (McNemar's test)
- `Chameleon_Analysis_Report.md` - Analysis report
- `modules/` - Legacy modules (data_preparation, gpt5_batch_processor, mistral_server)
- `config/` - Legacy configuration files

**Status**: These files are preserved for reference but are not maintained or used in the current OmniMath workflow.

### `onetime_scripts/`

Scripts that were used once during project setup but are not needed for regular workflow operation. These scripts were used for:

1. **Data Collection Phase** (Complete - 100 questions per difficulty collected)
   - `batch_generator.py` - Generated distortions in batches
   - `migrate_batch.py` - Migrated validated batches to final location
   - `filter_miu_levels.py` - Filtered from 10 to 4 MIU levels

2. **Evaluation Completion** (Complete - all evaluations done)
   - `complete_baseline_evaluation.py` - Filled in missing baselines
   - `direct_api_retry.py` - Retried token-limit failures
   - `retry_and_baseline_batch.py` - GPT-5 retry and baseline creation
   - `run_all_distortion_evaluations.py` - Master coordination script
   - `generate_eval_batches.py` - Converted batches to JSONL
   - `submit_eval_batches.py` - Submitted JSONL to Batch API
   - `evaluate_direct.py` - Alternative direct GPT-5 evaluation

3. **Model-Specific Evaluation** (Complete)
   - `evaluate_mistral_direct.py` - Mistral direct API evaluation
   - `evaluate_mistral_batch.py` - Mistral batch API evaluation
   - `evaluate_mistral_baseline.py` - Mistral baseline evaluation
   - `evaluate_gemini.py` - Gemini evaluation

4. **Outdated Scripts**
   - `generate_comparison_format.py` - References old file structure
   - `score_results.py` - Older scoring pipeline
   - `evaluate_distortions_batch.py` - Batch API alternative (not used)

**Status**: These scripts are preserved in case re-running is needed, but they are not part of the regular workflow. The current workflow uses the scripts in `src/flows/`.

## Why Archive?

These files are archived rather than deleted to:

1. **Preserve History**: Maintain a record of the project's evolution
2. **Reference**: Allow developers to understand previous approaches
3. **Recovery**: Enable recovery if needed for debugging or comparison
4. **Documentation**: Provide context for the current workflow design decisions

## Current Workflow

The active workflow uses:

- **Source code**: `src/modules/` and `src/flows/`
- **Data**: `data/source/` and `data/results/`
- **Output**: `output/plots/` and `output/reports/`

See the main [README.md](../README.md) for details on the current OmniMath workflow.

