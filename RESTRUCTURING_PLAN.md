# 🦎 CHAMELEON PROJECT - COMPREHENSIVE CODEBASE RESTRUCTURING PLAN

## CRITICAL CONTEXT FOR AI AGENT EXECUTOR

This document provides a **complete restructuring plan** for the Chameleon research project codebase. The goal is to transform a cluttered, confusing directory structure into a clean, well-organized codebase that is easy for both humans and AI language models to navigate and understand.

---

## 📋 EXECUTIVE SUMMARY

### The Core Problem

The Chameleon project has **two separate workflows that have accumulated over time:**

1. **LEGACY "MMLU/Chameleon" workflow** (root-level files):
   - Uses `distortions/chameleon_dataset.csv` for data
   - Uses root-level `modules/`, `config/`, `batches/` folders
   - Was designed for testing GPT-5 on MMLU multiple-choice questions with 10 distortion levels (μ 0.0-0.9)
   - **STATUS: LEGACY - NOT THE ACTIVE WORKFLOW**

2. **CURRENT "OmniMath" workflow** (in `omnimath_distortion_workflow/`):
   - Uses `omnimath_distortion_workflow/data/by_difficulty/` for data
   - Uses `omnimath_distortion_workflow/modules/` for modules
   - Uses `omnimath_distortion_workflow/evaluation/` for results
   - Tests multiple models (GPT-4o, GPT-5, GPT-5-mini, Mistral) on OmniMath math problems with 4 distortion levels (μ 0.2, 0.5, 0.7, 0.9)
   - **STATUS: ACTIVE - THIS IS THE CURRENT WORKFLOW**

Additionally, `omnimath_distortion_workflow/flows/` contains **22 Python scripts**, but only ~6 are essential for ongoing work. The other 16 were one-time scripts used during setup, data collection, or evaluation phases that have already completed.

---

## 🗂️ CURRENT DIRECTORY STRUCTURE (BEFORE RESTRUCTURING)

```
Chameleon/
├── .github/workflows/ci.yml              # CI config (references LEGACY files!)
├── _backup_original_files_omnimath_workflow/  # Development backup (DELETE)
├── analysis_plots/                        # LEGACY workflow output (RELOCATE)
├── batches/                               # LEGACY workflow batches (DELETE)
│   ├── metadata/project_metadata.json
│   ├── requests/all_openai_requests.jsonl
│   ├── test/test_batch.jsonl
│   └── tracking/batch_info.json
├── config/                                # LEGACY workflow config (DELETE)
│   └── config.yaml
├── distortions/                           # LEGACY workflow data (DELETE)
│   ├── chameleon_dataset.csv (11MB)
│   └── test_subset_dataset.csv
├── modules/                               # LEGACY workflow modules (DELETE)
│   ├── data_preparation.py
│   ├── gpt5_batch_processor.py
│   └── mistral_server.py
├── omnimath_distortion_workflow/          # CURRENT ACTIVE WORKFLOW (KEEP/RESTRUCTURE)
│   ├── data/by_difficulty/                # Source distortion data (ESSENTIAL DATA)
│   ├── evaluation/                        # Evaluation results (ESSENTIAL DATA)
│   │   ├── baseline_results/              # 8 model/difficulty combinations
│   │   └── distortion_results/            # 8 model/difficulty combinations
│   ├── flows/                             # 22 Python scripts (CLEAN UP - KEEP 6, ARCHIVE 16)
│   ├── modules/                           # Core modules (ESSENTIAL)
│   ├── statistical_analysis_report/       # Analysis output (KEEP)
│   ├── tests/                             # Unit tests (KEEP)
│   ├── verify_all_data.py                 # Data verification (ESSENTIAL)
│   └── *.md                               # Documentation (UPDATE)
├── venv/                                  # Virtual environment (IGNORE - gitignored)
├── chameleon.py                           # LEGACY main entry point (DELETE)
├── gpt5_manager.py                        # LEGACY batch manager (DELETE)
├── monitor_repair.py                      # LEGACY repair monitor (DELETE)
├── clean_gpt5_answers.py                  # LEGACY answer cleaner (DELETE)
├── create_visualizations.py               # LEGACY visualizations (RELOCATE or DELETE)
├── statistical_analysis.py                # LEGACY statistics (RELOCATE or DELETE)
├── Chameleon_Analysis_Report.md           # LEGACY report (RELOCATE or DELETE)
├── README.md                              # Describes LEGACY workflow! (REWRITE)
├── CONTRIBUTING.md                        # Contribution guide (UPDATE)
├── LICENSE                                # MIT License (KEEP)
├── requirements.txt                       # Dependencies (UPDATE)
└── requirements-dev.txt                   # Dev dependencies (KEEP)
```

---

## 🎯 TARGET DIRECTORY STRUCTURE (AFTER RESTRUCTURING)

```
Chameleon/
├── .github/workflows/ci.yml               # UPDATED CI config
├── src/                                   # Source code
│   ├── __init__.py
│   ├── modules/                           # Core reusable modules
│   │   ├── __init__.py
│   │   ├── answer_comparator.py           # Answer comparison logic
│   │   ├── batch_converter.py             # Batch conversion utilities
│   │   ├── distortion_validator.py        # Distortion validation
│   │   ├── evaluation_prompt.py           # Evaluation prompt generation
│   │   ├── math_distortion_prompts.py     # Distortion prompt templates
│   │   ├── omnimath_loader.py             # OmniMath dataset loader
│   │   └── results_parser.py              # Results parsing utilities
│   ├── flows/                             # Core workflow scripts
│   │   ├── __init__.py
│   │   ├── generate_distortions.py        # Generate distorted questions
│   │   ├── evaluate_baseline.py           # Evaluate models on originals
│   │   ├── evaluate_distortions.py        # Evaluate models on distorted
│   │   ├── analyze_results.py             # Analyze and compare results
│   │   ├── verify_data.py                 # Verify data integrity
│   │   └── review_corrections.py          # Review/correct string matching
│   └── analysis/                          # Analysis and visualization
│       ├── __init__.py
│       ├── statistical_analysis.py        # McNemar's test and statistics
│       └── visualizations.py              # Chart/plot generation
├── data/                                  # All data files
│   ├── source/                            # Source distortion data
│   │   ├── difficulty_1.0/                # Easy questions (100)
│   │   │   ├── baseline_questions.json
│   │   │   ├── distortions.json
│   │   │   └── metadata.json
│   │   └── difficulty_1.5/                # Slightly harder (100)
│   │       ├── baseline_questions.json
│   │       ├── distortions.json
│   │       └── metadata.json
│   └── results/                           # Evaluation results
│       ├── baseline/                      # Baseline evaluation results
│       │   ├── gpt_5_difficulty_1_0/
│       │   ├── gpt_5_difficulty_1_5/
│       │   ├── gpt_4o_difficulty_1_0/
│       │   ├── gpt_4o_difficulty_1_5/
│       │   ├── gpt_5_mini_difficulty_1_0/
│       │   ├── gpt_5_mini_difficulty_1_5/
│       │   ├── mistral_large_latest_difficulty_1_0/
│       │   └── mistral_large_latest_difficulty_1_5/
│       └── distortion/                    # Distortion evaluation results
│           ├── gpt_5_difficulty_1_0/
│           ├── gpt_5_difficulty_1_5/
│           ├── gpt_4o_difficulty_1_0/
│           ├── gpt_4o_difficulty_1_5/
│           ├── gpt_5_mini_difficulty_1_0/
│           ├── gpt_5_mini_difficulty_1_5/
│           ├── mistral_large_latest_difficulty_1_0/
│           └── mistral_large_latest_difficulty_1_5/
├── output/                                # Generated output
│   ├── plots/                             # All visualization images
│   ├── reports/                           # Analysis reports
│   │   ├── STATISTICAL_ANALYSIS_REPORT.md
│   │   └── data_verification_report.json
│   └── exports/                           # CSV/JSON exports
├── tests/                                 # All tests
│   ├── __init__.py
│   └── test_answer_comparator.py
├── archive/                               # Archived legacy/one-time scripts
│   ├── README.md                          # Explains what's archived
│   ├── legacy_mmlu_workflow/              # Old MMLU workflow files
│   │   ├── chameleon.py
│   │   ├── gpt5_manager.py
│   │   ├── config.yaml
│   │   └── ...
│   └── onetime_scripts/                   # One-time setup scripts
│       ├── batch_generator.py
│       ├── filter_miu_levels.py
│       ├── migrate_batch.py
│       └── ...
├── docs/                                  # Documentation
│   ├── README.md                          # Main documentation
│   ├── WORKFLOW.md                        # Workflow explanation
│   └── DATA_FORMAT.md                     # Data format documentation
├── README.md                              # Project overview (REWRITTEN)
├── CONTRIBUTING.md                        # Contribution guidelines
├── LICENSE                                # MIT License
├── requirements.txt                       # Core dependencies
├── requirements-dev.txt                   # Development dependencies
└── pyproject.toml                         # Optional: Modern Python project config
```

---

## 📝 DETAILED RESTRUCTURING ACTIONS

### PHASE 1: DELETE UNNECESSARY FILES AND FOLDERS

**Action: DELETE the following (these are LEGACY workflow files that are no longer used):**

```bash
# Legacy workflow files at root level
DELETE: chameleon.py
DELETE: gpt5_manager.py  
DELETE: monitor_repair.py
DELETE: clean_gpt5_answers.py
DELETE: create_visualizations.py
DELETE: statistical_analysis.py
DELETE: Chameleon_Analysis_Report.md

# Legacy workflow directories
DELETE ENTIRE FOLDER: modules/
DELETE ENTIRE FOLDER: config/
DELETE ENTIRE FOLDER: batches/
DELETE ENTIRE FOLDER: distortions/

# Development backup (not needed)
DELETE ENTIRE FOLDER: _backup_original_files_omnimath_workflow/
```

### PHASE 2: ARCHIVE ONE-TIME SCRIPTS

**These scripts in `omnimath_distortion_workflow/flows/` were used once and are no longer needed for regular workflow. Move them to `archive/onetime_scripts/`:**

```bash
# Data collection phase scripts (COMPLETE - 100 questions per difficulty collected)
ARCHIVE: flows/batch_generator.py           # Generated distortions in batches
ARCHIVE: flows/migrate_batch.py             # Migrated validated batches to final location
ARCHIVE: flows/filter_miu_levels.py         # Filtered from 10 to 4 MIU levels

# Evaluation completion scripts (COMPLETE - all evaluations done)
ARCHIVE: flows/complete_baseline_evaluation.py   # Filled in missing baselines
ARCHIVE: flows/direct_api_retry.py               # Retried token-limit failures
ARCHIVE: flows/retry_and_baseline_batch.py       # GPT-5 retry and baseline creation
ARCHIVE: flows/run_all_distortion_evaluations.py # Master coordination script
ARCHIVE: flows/generate_eval_batches.py          # Converted batches to JSONL
ARCHIVE: flows/submit_eval_batches.py            # Submitted JSONL to Batch API
ARCHIVE: flows/evaluate_direct.py                # Alternative direct GPT-5 evaluation

# Model-specific evaluation scripts (COMPLETE)
ARCHIVE: flows/evaluate_mistral_direct.py        # Mistral direct API evaluation
ARCHIVE: flows/evaluate_mistral_batch.py         # Mistral batch API evaluation
ARCHIVE: flows/evaluate_mistral_baseline.py      # Mistral baseline evaluation
ARCHIVE: flows/evaluate_gemini.py                # Gemini evaluation

# Outdated scripts
ARCHIVE: flows/generate_comparison_format.py     # References old file structure
ARCHIVE: flows/score_results.py                  # Older scoring pipeline
```

### PHASE 3: KEEP AND REORGANIZE ESSENTIAL FILES

**Essential Flow Scripts (Keep in `src/flows/`):**
```
KEEP AND RENAME: flows/omnimath_distortion_generator.py → src/flows/generate_distortions.py
KEEP AND RENAME: flows/evaluate_baseline.py → src/flows/evaluate_baseline.py  
KEEP AND RENAME: flows/evaluate_distortions_direct.py → src/flows/evaluate_distortions.py
KEEP AND RENAME: flows/evaluate_distortions_batch.py → MERGE into evaluate_distortions.py or ARCHIVE
KEEP AND RENAME: flows/analyze_distortion_results.py → src/flows/analyze_results.py
KEEP AND RENAME: flows/review_and_correct_results.py → src/flows/review_corrections.py
KEEP AND RENAME: verify_all_data.py → src/flows/verify_data.py
```

**Essential Modules (Move to `src/modules/`):**
```
MOVE: omnimath_distortion_workflow/modules/answer_comparator.py
MOVE: omnimath_distortion_workflow/modules/batch_converter.py
MOVE: omnimath_distortion_workflow/modules/distortion_validator.py
MOVE: omnimath_distortion_workflow/modules/evaluation_prompt.py
MOVE: omnimath_distortion_workflow/modules/math_distortion_prompts.py
MOVE: omnimath_distortion_workflow/modules/omnimath_loader.py
MOVE: omnimath_distortion_workflow/modules/results_parser.py
```

**Essential Data (Move to `data/`):**
```
MOVE: omnimath_distortion_workflow/data/by_difficulty/difficulty_1/ → data/source/difficulty_1.0/
MOVE: omnimath_distortion_workflow/data/by_difficulty/difficulty_1.5/ → data/source/difficulty_1.5/

MOVE: omnimath_distortion_workflow/evaluation/baseline_results/ → data/results/baseline/
MOVE: omnimath_distortion_workflow/evaluation/distortion_results/ → data/results/distortion/
```

**Analysis Output (Move to `output/`):**
```
MOVE: omnimath_distortion_workflow/statistical_analysis_report/*.png → output/plots/
MOVE: omnimath_distortion_workflow/statistical_analysis_report/*.md → output/reports/
MOVE: omnimath_distortion_workflow/statistical_analysis_report/*.json → output/reports/
MOVE: omnimath_distortion_workflow/statistical_analysis_report/*.py → src/analysis/
MOVE: analysis_plots/ → output/plots/legacy_analysis/
```

**Tests (Move to `tests/`):**
```
MOVE: omnimath_distortion_workflow/tests/test_answer_comparator.py → tests/
```

### PHASE 4: UPDATE IMPORT PATHS

After moving files, update all import statements in the Python files:

**Old import pattern:**
```python
from omnimath_distortion_workflow.modules.answer_comparator import compare_answers
from omnimath_distortion_workflow.modules.evaluation_prompt import create_evaluation_prompt
```

**New import pattern:**
```python
from src.modules.answer_comparator import compare_answers
from src.modules.evaluation_prompt import create_evaluation_prompt
```

**Files that need import updates:**
- All files in `src/flows/`
- All files in `src/analysis/`
- All test files in `tests/`

### PHASE 5: UPDATE CONFIGURATION FILES

**Update `.github/workflows/ci.yml`:**
- Remove references to `chameleon.py`, `gpt5_manager.py`, `monitor_repair.py`
- Update paths from `modules/` to `src/modules/`
- Update test paths from `tests/` to the new location

**Update `requirements.txt`:**
- Review and ensure all needed dependencies are listed
- Remove any unused dependencies

### PHASE 6: REWRITE README.md

Create a new README.md that accurately describes the OmniMath workflow:

```markdown
# 🦎 Chameleon: LLM Robustness Testing on OmniMath

A framework for testing large language model robustness under lexical distortion 
using mathematical questions from the OmniMath dataset.

## Project Overview

This project evaluates how well different LLMs (GPT-4o, GPT-5, GPT-5-mini, Mistral) 
maintain mathematical reasoning when questions are paraphrased at different 
distortion levels (μ = 0.2, 0.5, 0.7, 0.9).

## Quick Start

[... updated instructions for the new structure ...]
```

### PHASE 7: CREATE ARCHIVE README

Create `archive/README.md` explaining what's in the archive:

```markdown
# Archived Files

This folder contains files that are no longer part of the active workflow 
but are preserved for reference.

## legacy_mmlu_workflow/
Original MMLU-based distortion workflow files. These used a different 
data format and evaluation pipeline.

## onetime_scripts/
Scripts that were used once during project setup but are not needed 
for regular workflow operation. Preserved in case re-running is needed.
```

---

## 📊 FILE INVENTORY WITH ACTIONS

### ROOT LEVEL FILES

| File | Action | Reason |
|------|--------|--------|
| `chameleon.py` | **DELETE** | Legacy MMLU workflow entry point |
| `gpt5_manager.py` | **DELETE** | Legacy batch manager |
| `monitor_repair.py` | **DELETE** | Legacy repair monitor |
| `clean_gpt5_answers.py` | **DELETE** | Legacy answer cleaner |
| `create_visualizations.py` | **DELETE** | Legacy visualizations |
| `statistical_analysis.py` | **DELETE** | Legacy statistics |
| `Chameleon_Analysis_Report.md` | **DELETE** | Legacy report |
| `README.md` | **REWRITE** | Currently describes legacy workflow |
| `CONTRIBUTING.md` | **UPDATE** | Update paths |
| `LICENSE` | **KEEP** | MIT License |
| `requirements.txt` | **UPDATE** | Review dependencies |
| `requirements-dev.txt` | **KEEP** | Dev dependencies |

### ROOT LEVEL DIRECTORIES

| Directory | Action | Reason |
|-----------|--------|--------|
| `.github/workflows/` | **UPDATE** | Fix CI references |
| `_backup_original_files_omnimath_workflow/` | **DELETE** | Development backup |
| `analysis_plots/` | **MOVE** → `output/plots/legacy_analysis/` | Keep for reference |
| `batches/` | **DELETE** | Legacy workflow |
| `config/` | **DELETE** | Legacy workflow |
| `distortions/` | **DELETE** | Legacy workflow (11MB CSV) |
| `modules/` | **DELETE** | Legacy workflow modules |
| `omnimath_distortion_workflow/` | **RESTRUCTURE** | Active workflow - reorganize |
| `venv/` | **IGNORE** | Virtual environment (gitignored) |

### OMNIMATH_DISTORTION_WORKFLOW/FLOWS/ (22 files)

| File | Action | New Location | Reason |
|------|--------|--------------|--------|
| `omnimath_distortion_generator.py` | **KEEP** | `src/flows/generate_distortions.py` | Core distortion generation |
| `evaluate_baseline.py` | **KEEP** | `src/flows/evaluate_baseline.py` | Core baseline evaluation |
| `evaluate_distortions_direct.py` | **KEEP** | `src/flows/evaluate_distortions.py` | Core distortion evaluation |
| `evaluate_distortions_batch.py` | **ARCHIVE** | `archive/onetime_scripts/` | Batch API alternative |
| `analyze_distortion_results.py` | **KEEP** | `src/flows/analyze_results.py` | Core analysis |
| `review_and_correct_results.py` | **KEEP** | `src/flows/review_corrections.py` | String matching corrections |
| `batch_generator.py` | **ARCHIVE** | `archive/onetime_scripts/` | Data collection complete |
| `migrate_batch.py` | **ARCHIVE** | `archive/onetime_scripts/` | Data collection complete |
| `filter_miu_levels.py` | **ARCHIVE** | `archive/onetime_scripts/` | Already ran |
| `complete_baseline_evaluation.py` | **ARCHIVE** | `archive/onetime_scripts/` | Baselines complete |
| `direct_api_retry.py` | **ARCHIVE** | `archive/onetime_scripts/` | Retries done |
| `retry_and_baseline_batch.py` | **ARCHIVE** | `archive/onetime_scripts/` | Done |
| `run_all_distortion_evaluations.py` | **ARCHIVE** | `archive/onetime_scripts/` | Evaluations complete |
| `generate_eval_batches.py` | **ARCHIVE** | `archive/onetime_scripts/` | Conversion done |
| `submit_eval_batches.py` | **ARCHIVE** | `archive/onetime_scripts/` | Submissions done |
| `evaluate_direct.py` | **ARCHIVE** | `archive/onetime_scripts/` | Alternative to batch |
| `evaluate_mistral_direct.py` | **ARCHIVE** | `archive/onetime_scripts/` | Mistral eval done |
| `evaluate_mistral_batch.py` | **ARCHIVE** | `archive/onetime_scripts/` | Mistral eval done |
| `evaluate_mistral_baseline.py` | **ARCHIVE** | `archive/onetime_scripts/` | Mistral baseline done |
| `evaluate_gemini.py` | **ARCHIVE** | `archive/onetime_scripts/` | Gemini eval done |
| `generate_comparison_format.py` | **ARCHIVE** | `archive/onetime_scripts/` | Outdated file refs |
| `score_results.py` | **ARCHIVE** | `archive/onetime_scripts/` | Older scoring |

### OMNIMATH_DISTORTION_WORKFLOW/MODULES/ (7 files)

| File | Action | New Location |
|------|--------|--------------|
| `answer_comparator.py` | **MOVE** | `src/modules/answer_comparator.py` |
| `batch_converter.py` | **MOVE** | `src/modules/batch_converter.py` |
| `distortion_validator.py` | **MOVE** | `src/modules/distortion_validator.py` |
| `evaluation_prompt.py` | **MOVE** | `src/modules/evaluation_prompt.py` |
| `math_distortion_prompts.py` | **MOVE** | `src/modules/math_distortion_prompts.py` |
| `omnimath_loader.py` | **MOVE** | `src/modules/omnimath_loader.py` |
| `results_parser.py` | **MOVE** | `src/modules/results_parser.py` |

---

## ⚠️ IMPORTANT NOTES FOR EXECUTOR

1. **BACKUP FIRST**: Before making any changes, ensure you have a backup or that the repository is committed to git.

2. **DATA FILES ARE CRITICAL**: The files in `evaluation/baseline_results/` and `evaluation/distortion_results/` contain the actual evaluation results. Handle with care.

3. **IMPORT PATH UPDATES**: After moving files, you MUST update all import statements. Use search-and-replace:
   - `from omnimath_distortion_workflow.modules.` → `from src.modules.`
   - `from omnimath_distortion_workflow.flows.` → `from src.flows.`

4. **CI/CD**: The GitHub Actions workflow references legacy files. Update `.github/workflows/ci.yml` to remove references to deleted files.

5. **VERIFY AFTER RESTRUCTURING**: After restructuring, run `python -m src.flows.verify_data` to ensure all data is still accessible.

6. **RELATIVE PATH UPDATES**: Some scripts use `Path(__file__).parent.parent` patterns. These will need adjustment based on new file locations.

---

## 🔄 EXECUTION ORDER

1. **Create new directory structure** (`src/`, `data/`, `output/`, `archive/`, `docs/`)
2. **Move essential modules** to `src/modules/`
3. **Move essential flow scripts** to `src/flows/`
4. **Move data files** to `data/`
5. **Move analysis output** to `output/`
6. **Archive one-time scripts** to `archive/onetime_scripts/`
7. **Archive legacy files** to `archive/legacy_mmlu_workflow/`
8. **Delete unnecessary files** (after archiving what should be archived)
9. **Update import paths** in all Python files
10. **Update CI/CD** configuration
11. **Rewrite README.md**
12. **Test** that scripts still work
13. **Commit** changes

---

## ✅ SUCCESS CRITERIA

After restructuring:

- [ ] All essential scripts run without import errors
- [ ] Data files are accessible from new locations
- [ ] No legacy workflow files at root level
- [ ] Clear separation between `src/` (code), `data/` (data), `output/` (generated)
- [ ] Archive folder contains documented legacy/one-time scripts
- [ ] README.md accurately describes the current OmniMath workflow
- [ ] CI/CD passes (or is appropriately updated)
- [ ] Any AI agent can understand the project structure at a glance

---

**End of Restructuring Plan**


