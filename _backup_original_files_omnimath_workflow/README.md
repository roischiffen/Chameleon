# Backup of Original Files - OmniMath Distortion Workflow

## ⚠️ IMPORTANT: This is a Backup Directory

**DO NOT DELETE** - These files are kept as backups of the original locations before organizing into `omnimath_distortion_workflow/`.

**All active files are now in:** `omnimath_distortion_workflow/`

## Purpose

This directory contains the original files that were duplicated and organized into the `omnimath_distortion_workflow/` directory structure. These files are kept as backups to:
- Preserve original file locations
- Allow rollback if needed
- Maintain git history references
- Avoid disrupting existing references temporarily

## Contents

### Root Files
- `omnimath_distortion_generator.py` - Main distortion generator (now in `omnimath_distortion_workflow/flows/`)
- `test_omnimath_distortion.py` - OmniMath test script (now in `omnimath_distortion_workflow/flows/`)
- `test_chameleon_pipeline.py` - Pipeline test script (now in `omnimath_distortion_workflow/flows/`)
- `test_flow_minimal.py` - Minimal flow test (now in `omnimath_distortion_workflow/flows/`)
- `requirements-test.txt` - Test dependencies (now in `omnimath_distortion_workflow/`)

### Directories
- `omnimath_distorted_dataset/` - Generated dataset (now in `omnimath_distortion_workflow/data/batches/`)
- `test_omnimath_results/` - Test outputs (now in `omnimath_distortion_workflow/test-outputs/`)

### Modules
- `modules/math_distortion_prompts.py` - Distortion prompts (now in `omnimath_distortion_workflow/modules/`)
- `modules/omnimath_loader.py` - OmniMath loader (now in `omnimath_distortion_workflow/modules/`)
- `modules/distortion_validator.py` - Validator module (now in `omnimath_distortion_workflow/modules/`)

### Config
- `config/test_config.yaml` - Test config (now in `omnimath_distortion_workflow/config/`)

### Batches
- `batches/test/test_batch.jsonl` - Test batch (now in `omnimath_distortion_workflow/batches/test/`)

## When Can This Be Deleted?

You can safely delete this backup directory after:
1. ✅ Verifying all files work correctly from `omnimath_distortion_workflow/`
2. ✅ Confirming no scripts reference the old paths
3. ✅ Testing that imports and file paths work correctly
4. ✅ Committing the new structure to git

## Migration Date

Files moved: December 5, 2024
Reason: Organizing OmniMath distortion workflow into a dedicated directory structure

