# 🦎 Chameleon: LLM Robustness Testing on OmniMath

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A framework for testing large language model robustness under lexical distortion using mathematical questions from the OmniMath dataset.

## 🎯 Project Overview

The Chameleon project evaluates how well different LLMs maintain mathematical reasoning when questions are paraphrased at different distortion levels. This research tests **GPT-4o, GPT-5, GPT-5-mini, and Mistral-Large** on **OmniMath competition mathematics problems** with **4 distortion levels** (μ = 0.2, 0.5, 0.7, 0.9).

### Key Features

- 🔬 **Systematic Distortion Testing**: 4 distortion levels (μ = 0.2, 0.5, 0.7, 0.9)
- 📚 **Multi-Model Evaluation**: Tests GPT-4o, GPT-5, GPT-5-mini, and Mistral-Large
- 🧮 **Mathematical Focus**: Uses OmniMath competition problems at two difficulty levels
- 📊 **Comprehensive Analysis**: Statistical evaluation with McNemar's test and visualizations
- 🔄 **Reproducible Pipeline**: End-to-end automation with data verification

## 📊 Dataset Structure

The project uses **100 questions × 2 difficulties × 4 models × (baseline + 4 MIU levels)**:

- **Source Data**: `data/source/difficulty_1.0/` and `data/source/difficulty_1.5/`
  - Baseline questions (original OmniMath problems)
  - Distorted versions at 4 μ-levels
  - Metadata files

- **Results**: `data/results/baseline/` and `data/results/distortion/`
  - Evaluation results for each model/difficulty combination
  - JSON format with detailed answer comparisons

## 🏗️ Project Structure

```
Chameleon/
├── src/                          # Source code
│   ├── modules/                  # Core reusable modules
│   │   ├── answer_comparator.py      # Answer comparison logic
│   │   ├── batch_converter.py         # Batch conversion utilities
│   │   ├── distortion_validator.py   # Distortion validation
│   │   ├── evaluation_prompt.py      # Evaluation prompt generation
│   │   ├── math_distortion_prompts.py # Distortion prompt templates
│   │   ├── omnimath_loader.py         # OmniMath dataset loader
│   │   └── results_parser.py          # Results parsing utilities
│   ├── flows/                   # Core workflow scripts
│   │   ├── generate_distortions.py   # Generate distorted questions
│   │   ├── evaluate_baseline.py      # Evaluate models on originals
│   │   ├── evaluate_distortions.py   # Evaluate models on distorted
│   │   ├── analyze_results.py        # Analyze and compare results
│   │   ├── review_corrections.py     # Review/correct string matching
│   │   └── verify_data.py            # Verify data integrity
│   └── analysis/                # Analysis and visualization
│       ├── run_analysis.py           # Statistical analysis
│       └── gpt5mini_miu_breakdown.py # Model-specific analysis
├── data/                        # All data files
│   ├── source/                  # Source distortion data
│   │   ├── difficulty_1.0/      # Easy questions (100)
│   │   └── difficulty_1.5/      # Slightly harder (100)
│   └── results/                 # Evaluation results
│       ├── baseline/            # Baseline evaluation results
│       └── distortion/          # Distortion evaluation results
├── output/                      # Generated output
│   ├── plots/                   # Visualization images
│   ├── reports/                 # Analysis reports
│   └── exports/                 # CSV/JSON exports
├── tests/                       # Unit tests
├── archive/                     # Archived legacy/one-time scripts
│   ├── legacy_mmlu_workflow/    # Old MMLU workflow files
│   └── onetime_scripts/         # One-time setup scripts
└── docs/                        # Documentation
```

## 🚀 Quick Start

### Prerequisites

```bash
# Required Python packages
pip install -r requirements.txt

# OpenAI API key (for GPT models)
export OPENAI_API_KEY="your-api-key-here"

# Mistral API key (for Mistral models)
export MISTRAL_API_KEY="your-api-key-here"
```

### Basic Usage

```bash
# 1. Generate distorted questions (if needed)
python -m src.flows.generate_distortions --pilot

# 2. Evaluate baseline performance
python -m src.flows.evaluate_baseline --difficulty 1.0 --model gpt-5

# 3. Evaluate distorted questions
python -m src.flows.evaluate_distortions --difficulty 1.0 --model gpt-5

# 4. Analyze results
python -m src.flows.analyze_results

# 5. Verify data integrity
python -m src.flows.verify_data
```

## 📈 Key Results

### Baseline Accuracy

| Model | Difficulty 1.0 | Difficulty 1.5 |
|-------|----------------|----------------|
| GPT-5 | 97% | 90% |
| GPT-4o | 75% | 57% |
| GPT-5-mini | 96% | 89% |
| Mistral-Large | 69% | 49% |

### Distortion Impact

**Most Resilient**: GPT-4o with only 1.7% average accuracy degradation across all distortion levels.

**Most Vulnerable**: GPT-5-mini with 18.6% average accuracy degradation.

**Key Finding**: GPT-5-mini shows statistically significant degradation (p<0.01) at all distortion levels, particularly at difficulty 1.5.

## 🔬 Statistical Analysis

The project uses **McNemar's test** for paired comparisons between baseline and distorted conditions:

- **Paired data**: Same questions tested under baseline and distorted conditions
- **Binary outcomes**: Each answer is either correct or incorrect
- **Non-parametric**: No assumptions about underlying distribution

See `output/reports/STATISTICAL_ANALYSIS_REPORT.md` for detailed statistical results.

## 📚 Workflow

### 1. Generate Distortions

```bash
python -m src.flows.generate_distortions --full --count 100
```

Generates distorted versions of OmniMath questions at specified μ-levels using GPT-4o for high-quality mathematical paraphrasing.

### 2. Evaluate Baseline

```bash
python -m src.flows.evaluate_baseline --difficulty 1.0 --model gpt-5 --full
```

Evaluates models on original (non-distorted) questions to establish baseline performance.

### 3. Evaluate Distortions

```bash
python -m src.flows.evaluate_distortions --difficulty 1.0 --model gpt-5
```

Evaluates models on distorted questions across all μ-levels.

### 4. Analyze Results

```bash
python -m src.flows.analyze_results
```

Performs statistical analysis comparing baseline vs. distorted performance using McNemar's test.

### 5. Review Corrections

```bash
python -m src.flows.review_corrections
```

Reviews and corrects string matching issues in answer comparisons.

## 🔧 Configuration

### Model Configuration

Models are configured in the flow scripts with appropriate API endpoints and parameters:

- **GPT models**: Use OpenAI API
- **Mistral models**: Use Mistral API

### Distortion Levels

The project uses 4 distortion levels:
- **μ = 0.2**: Light lexical distortion
- **μ = 0.5**: Moderate lexical distortion
- **μ = 0.7**: Heavy lexical distortion
- **μ = 0.9**: Maximum lexical distortion (near-paraphrase)

## 📊 Output Files

### Results

- **Baseline results**: `data/results/baseline/{model}_difficulty_{difficulty}/`
  - `results.json`: Detailed evaluation results
  - `summary.json`: Summary statistics

- **Distortion results**: `data/results/distortion/{model}_difficulty_{difficulty}/`
  - `results.jsonl`: Detailed evaluation results (one per line)
  - `summary.json`: Summary statistics

### Analysis

- **Statistical report**: `output/reports/STATISTICAL_ANALYSIS_REPORT.md`
- **Visualizations**: `output/plots/*.png`
- **Analysis data**: `output/reports/analysis_data.json`

## 🧪 Testing

```bash
# Run tests
python -m pytest tests/ -v

# Test specific module
python -m pytest tests/test_answer_comparator.py -v
```

## 📋 Requirements

### System Requirements

- **Python**: 3.9 or higher
- **Memory**: 8GB RAM minimum
- **Storage**: 2GB free space for datasets and results
- **Network**: Stable internet connection for API calls

### Python Dependencies

See `requirements.txt` for core dependencies:
- `openai` - OpenAI API client
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `matplotlib` - Visualization
- `scipy` - Statistical analysis (McNemar's test)

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OmniMath**: Competition mathematics problem dataset
- **OpenAI**: GPT-4o, GPT-5, GPT-5-mini API access
- **Mistral AI**: Mistral-Large API access

## 🔬 Research Foundation

This project evaluates LLM robustness under lexical distortion, inspired by research on model dependence on surface-level linguistic patterns versus genuine understanding.

**Key Research Question**: How robust are large language models to lexical variations in mathematical problem-solving tasks?

## 📚 Citations

If you use Chameleon in your research, please cite:

```bibtex
@software{chameleon2024,
  title={Chameleon: LLM Robustness Testing Framework},
  author={Chameleon Framework},
  year={2024},
  url={https://github.com/your-username/chameleon}
}
```

---

**Built with ❤️ for the AI research community**
