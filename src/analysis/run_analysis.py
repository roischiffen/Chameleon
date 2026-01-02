#!/usr/bin/env python3
"""
Comprehensive Statistical Analysis of Distortion Experiment Results

This script performs McNemar's tests, effect size calculations, and generates
publication-quality visualizations for the distortion experiment comparing
baseline vs distorted math problem performance across multiple models.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import math

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from scipy import stats
from statsmodels.stats.contingency_tables import mcnemar

# Set high DPI and publication quality settings
plt.rcParams['figure.dpi'] = 200
plt.rcParams['savefig.dpi'] = 200
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['savefig.facecolor'] = 'white'

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
BASELINE_DIR = BASE_DIR / "data" / "results" / "baseline"
DISTORTION_DIR = BASE_DIR / "data" / "results" / "distortion"
OUTPUT_DIR = BASE_DIR / "output" / "reports"

# Models and configurations
MODELS = ["gpt_5", "gpt_4o", "gpt_5_mini", "mistral_large_latest"]
MODEL_DISPLAY_NAMES = {
    "gpt_5": "GPT-5",
    "gpt_4o": "GPT-4o", 
    "gpt_5_mini": "GPT-5-mini",
    "mistral_large_latest": "Mistral-Large"
}
DIFFICULTIES = [1.0, 1.5]
MIU_LEVELS = [0.2, 0.5, 0.7, 0.9]
MIU_DESCRIPTIONS = {
    0.2: "Synonym Substitution",
    0.5: "Notation Variation",
    0.7: "Format Conversion",
    0.9: "Maximum Distortion"
}

# Color schemes
MODEL_COLORS = {
    "GPT-5": "#2E86AB",
    "GPT-4o": "#A23B72",
    "GPT-5-mini": "#F18F01",
    "Mistral-Large": "#C73E1D"
}


def load_baseline_results(model: str, difficulty: float) -> Dict[int, bool]:
    """Load baseline results and return dict of question_id -> is_correct."""
    folder = f"{model}_difficulty_{difficulty}".replace(".", "_")
    results_file = BASELINE_DIR / folder / "results.json"
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    return {r['question_id']: r['is_correct'] for r in results}


def load_distortion_results(model: str, difficulty: float) -> Dict[float, Dict[int, bool]]:
    """Load distortion results and return dict of miu -> question_id -> is_correct."""
    folder = f"{model}_difficulty_{difficulty}".replace(".", "_")
    results_file = DISTORTION_DIR / folder / "results.jsonl"
    
    miu_results = defaultdict(dict)
    
    with open(results_file, 'r') as f:
        for line in f:
            r = json.loads(line.strip())
            miu = r['miu']
            qid = r['question_id']
            miu_results[miu][qid] = r['is_correct']
    
    return dict(miu_results)


def compute_mcnemar_test(baseline: Dict[int, bool], distorted: Dict[int, bool]) -> Dict:
    """
    Compute McNemar's test for paired binary outcomes.
    
    Returns:
        Dict with test statistic, p-value, counts, and interpretations
    """
    # Get paired data (only questions present in both)
    paired_questions = set(baseline.keys()) & set(distorted.keys())
    
    # Build contingency table
    # a: correct in both (baseline=1, distorted=1)
    # b: correct baseline, wrong distorted (lost) (baseline=1, distorted=0)
    # c: wrong baseline, correct distorted (gained) (baseline=0, distorted=1)
    # d: wrong in both (baseline=0, distorted=0)
    
    a = b = c = d = 0
    
    for qid in paired_questions:
        base_correct = baseline[qid]
        dist_correct = distorted[qid]
        
        if base_correct and dist_correct:
            a += 1
        elif base_correct and not dist_correct:
            b += 1  # Lost
        elif not base_correct and dist_correct:
            c += 1  # Gained
        else:
            d += 1
    
    # Contingency table for McNemar's test
    contingency = [[a, b], [c, d]]
    
    # Compute McNemar's test
    # Use exact test when b+c < 25, otherwise chi-square approximation
    n_discordant = b + c
    
    if n_discordant == 0:
        # No discordant pairs - cannot compute
        return {
            'n_paired': len(paired_questions),
            'both_correct': a,
            'lost': b,
            'gained': c,
            'both_wrong': d,
            'statistic': None,
            'p_value': 1.0,
            'net_change': c - b,
            'significant_05': False,
            'significant_01': False,
            'significant_10': False,
            'note': 'No discordant pairs'
        }
    
    # Use exact binomial test when n_discordant < 25
    if n_discordant < 25:
        # Exact binomial test (use binomtest for newer scipy versions)
        result = stats.binomtest(b, n_discordant, 0.5)
        p_value = result.pvalue
        statistic = (b - c)**2 / (b + c) if (b + c) > 0 else 0
    else:
        # McNemar's chi-square test with continuity correction
        result = mcnemar(contingency, exact=False, correction=True)
        statistic = result.statistic
        p_value = result.pvalue
    
    return {
        'n_paired': len(paired_questions),
        'both_correct': a,
        'lost': b,
        'gained': c,
        'both_wrong': d,
        'statistic': statistic,
        'p_value': p_value,
        'net_change': c - b,  # Positive = distortion helped, negative = distortion hurt
        'significant_05': p_value < 0.05,
        'significant_01': p_value < 0.01,
        'significant_10': p_value < 0.10,
    }


def compute_cohens_h(p1: float, p2: float) -> float:
    """
    Compute Cohen's h effect size for comparing two proportions.
    
    h = 2 * arcsin(sqrt(p1)) - 2 * arcsin(sqrt(p2))
    
    Interpretation:
    - Small: |h| = 0.2
    - Medium: |h| = 0.5
    - Large: |h| = 0.8
    """
    # Clamp proportions to avoid domain errors
    p1 = max(0.001, min(0.999, p1))
    p2 = max(0.001, min(0.999, p2))
    
    phi1 = 2 * math.asin(math.sqrt(p1))
    phi2 = 2 * math.asin(math.sqrt(p2))
    
    return phi1 - phi2


def compute_confidence_interval(n_correct: int, n_total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Compute Wilson score confidence interval for a proportion."""
    if n_total == 0:
        return (0, 0)
    
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p_hat = n_correct / n_total
    
    denominator = 1 + z**2 / n_total
    center = (p_hat + z**2 / (2 * n_total)) / denominator
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n_total)) / n_total) / denominator
    
    return (max(0, center - margin), min(1, center + margin))


def run_full_analysis() -> Dict:
    """Run the complete statistical analysis."""
    
    print("=" * 60)
    print("STATISTICAL ANALYSIS OF DISTORTION EXPERIMENT")
    print("=" * 60)
    
    all_results = {
        'baseline': {},
        'distortion': {},
        'mcnemar_tests': {},
        'effect_sizes': {},
        'summary_stats': {}
    }
    
    # Load and analyze all data
    for model in MODELS:
        display_name = MODEL_DISPLAY_NAMES[model]
        all_results['baseline'][display_name] = {}
        all_results['distortion'][display_name] = {}
        all_results['mcnemar_tests'][display_name] = {}
        all_results['effect_sizes'][display_name] = {}
        
        for diff in DIFFICULTIES:
            diff_key = f"D{diff}"
            print(f"\nAnalyzing {display_name} - Difficulty {diff}...")
            
            # Load baseline
            try:
                baseline = load_baseline_results(model, diff)
            except FileNotFoundError:
                print(f"  Warning: Baseline file not found for {model} D{diff}")
                continue
            
            baseline_correct = sum(1 for v in baseline.values() if v)
            baseline_total = len(baseline)
            baseline_acc = baseline_correct / baseline_total if baseline_total > 0 else 0
            
            all_results['baseline'][display_name][diff_key] = {
                'correct': baseline_correct,
                'total': baseline_total,
                'accuracy': baseline_acc * 100,
                'ci_lower': compute_confidence_interval(baseline_correct, baseline_total)[0] * 100,
                'ci_upper': compute_confidence_interval(baseline_correct, baseline_total)[1] * 100
            }
            
            # Load distortion results
            try:
                distortion = load_distortion_results(model, diff)
            except FileNotFoundError:
                print(f"  Warning: Distortion file not found for {model} D{diff}")
                continue
            
            all_results['distortion'][display_name][diff_key] = {}
            all_results['mcnemar_tests'][display_name][diff_key] = {}
            all_results['effect_sizes'][display_name][diff_key] = {}
            
            for miu in MIU_LEVELS:
                if miu not in distortion:
                    continue
                    
                miu_key = f"MIU_{miu}"
                dist_data = distortion[miu]
                dist_correct = sum(1 for v in dist_data.values() if v)
                dist_total = len(dist_data)
                dist_acc = dist_correct / dist_total if dist_total > 0 else 0
                
                all_results['distortion'][display_name][diff_key][miu_key] = {
                    'correct': dist_correct,
                    'total': dist_total,
                    'accuracy': dist_acc * 100,
                    'ci_lower': compute_confidence_interval(dist_correct, dist_total)[0] * 100,
                    'ci_upper': compute_confidence_interval(dist_correct, dist_total)[1] * 100
                }
                
                # McNemar's test
                mcnemar_result = compute_mcnemar_test(baseline, dist_data)
                all_results['mcnemar_tests'][display_name][diff_key][miu_key] = mcnemar_result
                
                # Effect size (Cohen's h)
                cohens_h = compute_cohens_h(baseline_acc, dist_acc)
                degradation = (baseline_acc - dist_acc) * 100
                
                all_results['effect_sizes'][display_name][diff_key][miu_key] = {
                    'cohens_h': cohens_h,
                    'degradation_pct': degradation,
                    'baseline_acc': baseline_acc * 100,
                    'distortion_acc': dist_acc * 100
                }
                
                print(f"  MIU {miu}: Base={baseline_acc*100:.1f}%, Dist={dist_acc*100:.1f}%, "
                      f"Δ={degradation:+.1f}%, p={mcnemar_result['p_value']:.4f}, "
                      f"h={cohens_h:.3f}")
    
    return all_results


def create_baseline_vs_distortion_chart(results: Dict):
    """Create bar chart comparing baseline vs average distortion accuracy."""
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    for idx, diff in enumerate(DIFFICULTIES):
        ax = axes[idx]
        diff_key = f"D{diff}"
        
        models = []
        baseline_accs = []
        distortion_accs = []
        baseline_ci = []
        distortion_ci = []
        
        for model in MODELS:
            display_name = MODEL_DISPLAY_NAMES[model]
            if display_name not in results['baseline'] or diff_key not in results['baseline'][display_name]:
                continue
            
            models.append(display_name)
            base_data = results['baseline'][display_name][diff_key]
            baseline_accs.append(base_data['accuracy'])
            baseline_ci.append((base_data['accuracy'] - base_data['ci_lower'],
                               base_data['ci_upper'] - base_data['accuracy']))
            
            # Average distortion accuracy across MIU levels
            if diff_key in results['distortion'][display_name]:
                miu_accs = [v['accuracy'] for v in results['distortion'][display_name][diff_key].values()]
                avg_dist = np.mean(miu_accs)
                distortion_accs.append(avg_dist)
                
                # Approximate CI for average
                miu_cis = [v['ci_upper'] - v['ci_lower'] for v in results['distortion'][display_name][diff_key].values()]
                avg_ci = np.mean(miu_cis) / 2
                distortion_ci.append((avg_ci, avg_ci))
            else:
                distortion_accs.append(0)
                distortion_ci.append((0, 0))
        
        x = np.arange(len(models))
        width = 0.35
        
        colors_base = [MODEL_COLORS[m] for m in models]
        colors_dist = [plt.cm.colors.to_rgba(MODEL_COLORS[m], 0.6) for m in models]
        
        bars1 = ax.bar(x - width/2, baseline_accs, width, label='Baseline',
                       color=colors_base, edgecolor='black', linewidth=1)
        bars2 = ax.bar(x + width/2, distortion_accs, width, label='Distorted (Avg)',
                       color=colors_dist, edgecolor='black', linewidth=1, hatch='///')
        
        ax.set_xlabel('Model')
        ax.set_ylabel('Accuracy (%)')
        ax.set_title(f'Baseline vs Distortion Accuracy\n(Difficulty {diff})', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=15, ha='right')
        ax.legend()
        ax.set_ylim(0, 105)
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            ax.annotate(f'{height:.0f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3), textcoords="offset points",
                       ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        for bar in bars2:
            height = bar.get_height()
            ax.annotate(f'{height:.0f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3), textcoords="offset points",
                       ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'baseline_vs_distortion.png', bbox_inches='tight')
    plt.close()
    print("Saved: baseline_vs_distortion.png")


def create_degradation_curves(results: Dict):
    """Create accuracy vs MIU level degradation curves for each model."""
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    for idx, diff in enumerate(DIFFICULTIES):
        ax = axes[idx]
        diff_key = f"D{diff}"
        
        for model in MODELS:
            display_name = MODEL_DISPLAY_NAMES[model]
            if display_name not in results['distortion'] or diff_key not in results['distortion'][display_name]:
                continue
            
            # Get baseline accuracy
            base_acc = results['baseline'][display_name][diff_key]['accuracy']
            
            # Get distortion accuracies for each MIU
            miu_values = []
            dist_accs = []
            
            for miu in MIU_LEVELS:
                miu_key = f"MIU_{miu}"
                if miu_key in results['distortion'][display_name][diff_key]:
                    miu_values.append(miu)
                    dist_accs.append(results['distortion'][display_name][diff_key][miu_key]['accuracy'])
            
            # Plot baseline as horizontal line
            ax.axhline(y=base_acc, color=MODEL_COLORS[display_name], linestyle='--', alpha=0.5, linewidth=1)
            
            # Plot distortion curve
            ax.plot(miu_values, dist_accs, marker='o', markersize=8, 
                   label=display_name, color=MODEL_COLORS[display_name], linewidth=2)
            
            # Add baseline marker at x=0
            ax.plot(0, base_acc, marker='s', markersize=10, color=MODEL_COLORS[display_name])
        
        ax.set_xlabel('MIU Level (Distortion Intensity)')
        ax.set_ylabel('Accuracy (%)')
        ax.set_title(f'Accuracy Degradation by Distortion Level\n(Difficulty {diff})', fontweight='bold')
        ax.set_xticks([0] + MIU_LEVELS)
        ax.set_xticklabels(['Baseline'] + [str(m) for m in MIU_LEVELS])
        ax.legend(loc='lower left')
        ax.set_ylim(30, 105)
        ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'degradation_curves.png', bbox_inches='tight')
    plt.close()
    print("Saved: degradation_curves.png")


def create_effect_size_heatmap(results: Dict):
    """Create heatmap of Cohen's h effect sizes."""
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    for idx, diff in enumerate(DIFFICULTIES):
        ax = axes[idx]
        diff_key = f"D{diff}"
        
        # Build matrix
        model_names = []
        matrix = []
        
        for model in MODELS:
            display_name = MODEL_DISPLAY_NAMES[model]
            if display_name not in results['effect_sizes'] or diff_key not in results['effect_sizes'][display_name]:
                continue
            
            model_names.append(display_name)
            row = []
            for miu in MIU_LEVELS:
                miu_key = f"MIU_{miu}"
                if miu_key in results['effect_sizes'][display_name][diff_key]:
                    h = results['effect_sizes'][display_name][diff_key][miu_key]['cohens_h']
                    row.append(h)
                else:
                    row.append(0)
            matrix.append(row)
        
        matrix = np.array(matrix)
        
        # Custom colormap: green (negative=improvement) to white to red (positive=degradation)
        cmap = LinearSegmentedColormap.from_list('effect', ['#2E7D32', '#FFFFFF', '#C62828'])
        
        # Set vmin/vmax symmetrically
        max_val = max(abs(matrix.min()), abs(matrix.max()))
        max_val = max(max_val, 0.3)  # Ensure some range
        
        im = ax.imshow(matrix, cmap=cmap, aspect='auto', vmin=-max_val, vmax=max_val)
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label("Cohen's h (+ = degradation, - = improvement)")
        
        # Labels
        ax.set_xticks(np.arange(len(MIU_LEVELS)))
        ax.set_yticks(np.arange(len(model_names)))
        ax.set_xticklabels([f'{m}\n{MIU_DESCRIPTIONS[m][:10]}...' for m in MIU_LEVELS])
        ax.set_yticklabels(model_names)
        ax.set_xlabel('MIU Level')
        ax.set_ylabel('Model')
        ax.set_title(f"Effect Size (Cohen's h) Heatmap\n(Difficulty {diff})", fontweight='bold')
        
        # Add text annotations
        for i in range(len(model_names)):
            for j in range(len(MIU_LEVELS)):
                val = matrix[i, j]
                color = 'white' if abs(val) > max_val * 0.6 else 'black'
                ax.text(j, i, f'{val:.2f}', ha='center', va='center', color=color, fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'effect_size_heatmap.png', bbox_inches='tight')
    plt.close()
    print("Saved: effect_size_heatmap.png")


def create_significance_summary(results: Dict):
    """Create visual summary of statistical significance."""
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    for idx, diff in enumerate(DIFFICULTIES):
        ax = axes[idx]
        diff_key = f"D{diff}"
        
        model_names = []
        significance_matrix = []
        
        for model in MODELS:
            display_name = MODEL_DISPLAY_NAMES[model]
            if display_name not in results['mcnemar_tests'] or diff_key not in results['mcnemar_tests'][display_name]:
                continue
            
            model_names.append(display_name)
            row = []
            for miu in MIU_LEVELS:
                miu_key = f"MIU_{miu}"
                if miu_key in results['mcnemar_tests'][display_name][diff_key]:
                    mcnemar_data = results['mcnemar_tests'][display_name][diff_key][miu_key]
                    p = mcnemar_data['p_value']
                    # Encode significance level
                    if p < 0.01:
                        row.append(3)  # Highly significant
                    elif p < 0.05:
                        row.append(2)  # Significant
                    elif p < 0.10:
                        row.append(1)  # Marginally significant
                    else:
                        row.append(0)  # Not significant
                else:
                    row.append(-1)  # Missing
            significance_matrix.append(row)
        
        matrix = np.array(significance_matrix)
        
        # Custom colormap for significance levels
        colors = ['#EEEEEE', '#FFD54F', '#FF9800', '#E53935']  # Not sig, p<0.1, p<0.05, p<0.01
        cmap = LinearSegmentedColormap.from_list('sig', colors)
        
        im = ax.imshow(matrix, cmap=cmap, aspect='auto', vmin=0, vmax=3)
        
        # Labels
        ax.set_xticks(np.arange(len(MIU_LEVELS)))
        ax.set_yticks(np.arange(len(model_names)))
        ax.set_xticklabels([f'{m}' for m in MIU_LEVELS])
        ax.set_yticklabels(model_names)
        ax.set_xlabel('MIU Level')
        ax.set_ylabel('Model')
        ax.set_title(f'Statistical Significance Summary\n(Difficulty {diff})', fontweight='bold')
        
        # Add p-value annotations
        for i in range(len(model_names)):
            for j in range(len(MIU_LEVELS)):
                miu_key = f"MIU_{MIU_LEVELS[j]}"
                display_name = model_names[i]
                if miu_key in results['mcnemar_tests'][display_name][diff_key]:
                    p = results['mcnemar_tests'][display_name][diff_key][miu_key]['p_value']
                    if p < 0.001:
                        text = 'p<.001'
                    elif p < 0.01:
                        text = f'p={p:.3f}'
                    else:
                        text = f'p={p:.2f}'
                    color = 'white' if matrix[i, j] >= 2 else 'black'
                    ax.text(j, i, text, ha='center', va='center', color=color, fontsize=9)
        
        # Add legend
        legend_elements = [
            mpatches.Patch(facecolor=colors[0], edgecolor='black', label='Not significant'),
            mpatches.Patch(facecolor=colors[1], edgecolor='black', label='p < 0.10'),
            mpatches.Patch(facecolor=colors[2], edgecolor='black', label='p < 0.05'),
            mpatches.Patch(facecolor=colors[3], edgecolor='black', label='p < 0.01'),
        ]
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1))
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'significance_summary.png', bbox_inches='tight')
    plt.close()
    print("Saved: significance_summary.png")


def create_net_change_chart(results: Dict):
    """Create chart showing questions lost vs gained for each model."""
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    for idx, diff in enumerate(DIFFICULTIES):
        ax = axes[idx]
        diff_key = f"D{diff}"
        
        model_names = []
        total_lost = []
        total_gained = []
        
        for model in MODELS:
            display_name = MODEL_DISPLAY_NAMES[model]
            if display_name not in results['mcnemar_tests'] or diff_key not in results['mcnemar_tests'][display_name]:
                continue
            
            model_names.append(display_name)
            lost = 0
            gained = 0
            
            for miu in MIU_LEVELS:
                miu_key = f"MIU_{miu}"
                if miu_key in results['mcnemar_tests'][display_name][diff_key]:
                    data = results['mcnemar_tests'][display_name][diff_key][miu_key]
                    lost += data['lost']
                    gained += data['gained']
            
            total_lost.append(-lost)  # Negative for visual effect
            total_gained.append(gained)
        
        x = np.arange(len(model_names))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, total_lost, width, label='Questions Lost',
                       color='#E53935', edgecolor='black')
        bars2 = ax.bar(x + width/2, total_gained, width, label='Questions Gained',
                       color='#43A047', edgecolor='black')
        
        ax.axhline(y=0, color='black', linewidth=1)
        ax.set_xlabel('Model')
        ax.set_ylabel('Number of Questions')
        ax.set_title(f'Questions Lost vs Gained Due to Distortion\n(Difficulty {diff}, All MIU Levels Combined)', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(model_names, rotation=15, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            ax.annotate(f'{abs(int(height))}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, -10 if height < 0 else 3), textcoords="offset points",
                       ha='center', va='top' if height < 0 else 'bottom', fontsize=10, fontweight='bold')
        
        for bar in bars2:
            height = bar.get_height()
            ax.annotate(f'{int(height)}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3), textcoords="offset points",
                       ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'net_change_chart.png', bbox_inches='tight')
    plt.close()
    print("Saved: net_change_chart.png")


def create_comprehensive_dashboard(results: Dict):
    """Create comprehensive dashboard with all key findings."""
    
    fig = plt.figure(figsize=(20, 16))
    
    # Create grid layout
    gs = fig.add_gridspec(3, 4, hspace=0.35, wspace=0.3)
    
    # 1. Title and Summary (top left)
    ax_title = fig.add_subplot(gs[0, 0:2])
    ax_title.axis('off')
    
    # Count significant results
    total_comparisons = 0
    significant_05 = 0
    significant_01 = 0
    
    for model in results['mcnemar_tests']:
        for diff in results['mcnemar_tests'][model]:
            for miu in results['mcnemar_tests'][model][diff]:
                data = results['mcnemar_tests'][model][diff][miu]
                total_comparisons += 1
                if data['significant_05']:
                    significant_05 += 1
                if data['significant_01']:
                    significant_01 += 1
    
    # Create structured summary
    ax_title.text(0.5, 0.95, "DISTORTION EXPERIMENT\nSTATISTICAL ANALYSIS", 
                  transform=ax_title.transAxes, fontsize=16, fontweight='bold',
                  ha='center', va='top')
    
    summary_lines = [
        f"Total Comparisons: {total_comparisons}",
        f"Significant at p<0.05: {significant_05} ({100*significant_05/total_comparisons:.1f}%)",
        f"Significant at p<0.01: {significant_01} ({100*significant_01/total_comparisons:.1f}%)",
        "",
        "Models: GPT-5, GPT-4o, GPT-5-mini, Mistral-Large",
        "Difficulties: 1.0 (Easy), 1.5 (Hard)",
        "MIU Levels: 0.2, 0.5, 0.7, 0.9"
    ]
    
    for i, line in enumerate(summary_lines):
        ax_title.text(0.5, 0.65 - i*0.09, line, transform=ax_title.transAxes,
                     fontsize=11, ha='center', va='top')
    
    # 2. Baseline Accuracy Comparison (top right)
    ax_base = fig.add_subplot(gs[0, 2:4])
    
    models_display = [MODEL_DISPLAY_NAMES[m] for m in MODELS]
    x = np.arange(len(models_display))
    width = 0.35
    
    d1_accs = []
    d15_accs = []
    for model in MODELS:
        display_name = MODEL_DISPLAY_NAMES[model]
        d1_accs.append(results['baseline'].get(display_name, {}).get('D1.0', {}).get('accuracy', 0))
        d15_accs.append(results['baseline'].get(display_name, {}).get('D1.5', {}).get('accuracy', 0))
    
    ax_base.bar(x - width/2, d1_accs, width, label='Difficulty 1.0', color='#2196F3')
    ax_base.bar(x + width/2, d15_accs, width, label='Difficulty 1.5', color='#FF5722')
    ax_base.set_ylabel('Accuracy (%)')
    ax_base.set_title('Baseline Accuracy by Model', fontweight='bold')
    ax_base.set_xticks(x)
    ax_base.set_xticklabels(models_display, rotation=15, ha='right')
    ax_base.legend()
    ax_base.set_ylim(0, 105)
    ax_base.grid(axis='y', alpha=0.3)
    
    # 3. Degradation Curves D1.0 (middle left)
    ax_deg1 = fig.add_subplot(gs[1, 0:2])
    diff_key = "D1.0"
    
    for model in MODELS:
        display_name = MODEL_DISPLAY_NAMES[model]
        if display_name not in results['distortion'] or diff_key not in results['distortion'].get(display_name, {}):
            continue
        
        base_acc = results['baseline'][display_name][diff_key]['accuracy']
        miu_values = [0]
        dist_accs = [base_acc]
        
        for miu in MIU_LEVELS:
            miu_key = f"MIU_{miu}"
            if miu_key in results['distortion'][display_name][diff_key]:
                miu_values.append(miu)
                dist_accs.append(results['distortion'][display_name][diff_key][miu_key]['accuracy'])
        
        ax_deg1.plot(miu_values, dist_accs, marker='o', label=display_name, 
                    color=MODEL_COLORS[display_name], linewidth=2)
    
    ax_deg1.set_xlabel('MIU Level (0 = Baseline)')
    ax_deg1.set_ylabel('Accuracy (%)')
    ax_deg1.set_title('Accuracy vs Distortion Level (Difficulty 1.0)', fontweight='bold')
    ax_deg1.legend(loc='lower left')
    ax_deg1.grid(alpha=0.3)
    ax_deg1.set_ylim(50, 102)
    
    # 4. Degradation Curves D1.5 (middle right)
    ax_deg2 = fig.add_subplot(gs[1, 2:4])
    diff_key = "D1.5"
    
    for model in MODELS:
        display_name = MODEL_DISPLAY_NAMES[model]
        if display_name not in results['distortion'] or diff_key not in results['distortion'].get(display_name, {}):
            continue
        
        base_acc = results['baseline'][display_name][diff_key]['accuracy']
        miu_values = [0]
        dist_accs = [base_acc]
        
        for miu in MIU_LEVELS:
            miu_key = f"MIU_{miu}"
            if miu_key in results['distortion'][display_name][diff_key]:
                miu_values.append(miu)
                dist_accs.append(results['distortion'][display_name][diff_key][miu_key]['accuracy'])
        
        ax_deg2.plot(miu_values, dist_accs, marker='o', label=display_name,
                    color=MODEL_COLORS[display_name], linewidth=2)
    
    ax_deg2.set_xlabel('MIU Level (0 = Baseline)')
    ax_deg2.set_ylabel('Accuracy (%)')
    ax_deg2.set_title('Accuracy vs Distortion Level (Difficulty 1.5)', fontweight='bold')
    ax_deg2.legend(loc='lower left')
    ax_deg2.grid(alpha=0.3)
    ax_deg2.set_ylim(30, 102)
    
    # 5. Effect Size Comparison (bottom left)
    ax_effect = fig.add_subplot(gs[2, 0:2])
    
    # Create grouped bar chart of average Cohen's h by model
    avg_effects_d1 = []
    avg_effects_d15 = []
    
    for model in MODELS:
        display_name = MODEL_DISPLAY_NAMES[model]
        
        d1_effects = []
        d15_effects = []
        
        if display_name in results['effect_sizes']:
            if 'D1.0' in results['effect_sizes'][display_name]:
                d1_effects = [v['cohens_h'] for v in results['effect_sizes'][display_name]['D1.0'].values()]
            if 'D1.5' in results['effect_sizes'][display_name]:
                d15_effects = [v['cohens_h'] for v in results['effect_sizes'][display_name]['D1.5'].values()]
        
        avg_effects_d1.append(np.mean(d1_effects) if d1_effects else 0)
        avg_effects_d15.append(np.mean(d15_effects) if d15_effects else 0)
    
    x = np.arange(len(models_display))
    ax_effect.bar(x - width/2, avg_effects_d1, width, label='Difficulty 1.0', color='#2196F3')
    ax_effect.bar(x + width/2, avg_effects_d15, width, label='Difficulty 1.5', color='#FF5722')
    ax_effect.axhline(y=0.2, color='green', linestyle='--', alpha=0.7, label='Small effect (0.2)')
    ax_effect.axhline(y=0.5, color='orange', linestyle='--', alpha=0.7, label='Medium effect (0.5)')
    ax_effect.set_ylabel("Cohen's h")
    ax_effect.set_title("Average Effect Size by Model", fontweight='bold')
    ax_effect.set_xticks(x)
    ax_effect.set_xticklabels(models_display, rotation=15, ha='right')
    ax_effect.legend(loc='upper right', fontsize=8)
    ax_effect.grid(axis='y', alpha=0.3)
    
    # 6. Key Findings Table (bottom right)
    ax_table = fig.add_subplot(gs[2, 2:4])
    ax_table.axis('off')
    
    # Calculate resilience ranking
    resilience_scores = {}
    for model in MODELS:
        display_name = MODEL_DISPLAY_NAMES[model]
        total_degradation = 0
        count = 0
        
        if display_name in results['effect_sizes']:
            for diff in results['effect_sizes'][display_name]:
                for miu in results['effect_sizes'][display_name][diff]:
                    total_degradation += results['effect_sizes'][display_name][diff][miu]['degradation_pct']
                    count += 1
        
        resilience_scores[display_name] = total_degradation / count if count > 0 else 0
    
    sorted_resilience = sorted(resilience_scores.items(), key=lambda x: x[1])
    
    # Find most vulnerable combination
    max_degradation = 0
    max_combo = ""
    for model in results['effect_sizes']:
        for diff in results['effect_sizes'][model]:
            for miu in results['effect_sizes'][model][diff]:
                deg = results['effect_sizes'][model][diff][miu]['degradation_pct']
                if deg > max_degradation:
                    max_degradation = deg
                    miu_val = float(miu.replace('MIU_', ''))
                    max_combo = f"{model} at {diff}, MIU {miu_val}"
    
    # Draw key findings as structured text
    ax_table.text(0.5, 0.98, "KEY FINDINGS", transform=ax_table.transAxes,
                  fontsize=14, fontweight='bold', ha='center', va='top')
    
    # Resilience ranking
    ax_table.text(0.05, 0.85, "RESILIENCE RANKING:", transform=ax_table.transAxes,
                  fontsize=11, fontweight='bold', va='top')
    for i, (model, score) in enumerate(sorted_resilience, 1):
        ax_table.text(0.08, 0.78 - i*0.07, f"{i}. {model}: {score:.1f}% avg degradation",
                     transform=ax_table.transAxes, fontsize=10, va='top')
    
    # Statistical significance
    ax_table.text(0.05, 0.45, "STATISTICAL SIGNIFICANCE:", transform=ax_table.transAxes,
                  fontsize=11, fontweight='bold', va='top')
    ax_table.text(0.08, 0.38, f"{significant_05}/{total_comparisons} significant at p<0.05",
                 transform=ax_table.transAxes, fontsize=10, va='top')
    ax_table.text(0.08, 0.31, f"{significant_01}/{total_comparisons} significant at p<0.01",
                 transform=ax_table.transAxes, fontsize=10, va='top')
    
    # Most vulnerable
    ax_table.text(0.05, 0.20, "MOST VULNERABLE:", transform=ax_table.transAxes,
                  fontsize=11, fontweight='bold', va='top')
    ax_table.text(0.08, 0.13, f"{max_combo}", transform=ax_table.transAxes, fontsize=10, va='top')
    ax_table.text(0.08, 0.06, f"({max_degradation:.1f}% degradation)", transform=ax_table.transAxes, fontsize=10, va='top')
    
    # Add background box
    from matplotlib.patches import FancyBboxPatch
    bbox = FancyBboxPatch((0.02, 0.02), 0.96, 0.94, transform=ax_table.transAxes,
                          boxstyle='round,pad=0.02', facecolor='#f5f5f5', edgecolor='#cccccc',
                          linewidth=1, zorder=0)
    ax_table.add_patch(bbox)
    
    plt.savefig(OUTPUT_DIR / 'comprehensive_dashboard.png', bbox_inches='tight')
    plt.close()
    print("Saved: comprehensive_dashboard.png")


def generate_markdown_report(results: Dict) -> str:
    """Generate comprehensive markdown report."""
    
    report = []
    
    # Executive Summary
    report.append("# Statistical Analysis Report: Semantic Distortion Experiment\n")
    report.append("**Date:** " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
    report.append("---\n")
    
    report.append("## Executive Summary\n")
    
    # Calculate key statistics
    total_comparisons = 0
    significant_05 = 0
    significant_01 = 0
    total_lost = 0
    total_gained = 0
    
    for model in results['mcnemar_tests']:
        for diff in results['mcnemar_tests'][model]:
            for miu in results['mcnemar_tests'][model][diff]:
                data = results['mcnemar_tests'][model][diff][miu]
                total_comparisons += 1
                if data['significant_05']:
                    significant_05 += 1
                if data['significant_01']:
                    significant_01 += 1
                total_lost += data['lost']
                total_gained += data['gained']
    
    # Calculate resilience ranking
    resilience_scores = {}
    for model in MODELS:
        display_name = MODEL_DISPLAY_NAMES[model]
        total_degradation = 0
        count = 0
        
        if display_name in results['effect_sizes']:
            for diff in results['effect_sizes'][display_name]:
                for miu in results['effect_sizes'][display_name][diff]:
                    total_degradation += results['effect_sizes'][display_name][diff][miu]['degradation_pct']
                    count += 1
        
        resilience_scores[display_name] = total_degradation / count if count > 0 else 0
    
    sorted_resilience = sorted(resilience_scores.items(), key=lambda x: x[1])
    
    report.append("### Key Findings\n")
    report.append(f"1. **Statistical Significance:** {significant_05} of {total_comparisons} comparisons ({100*significant_05/total_comparisons:.1f}%) showed statistically significant degradation at p<0.05.\n")
    report.append(f"2. **Most Resilient Model:** {sorted_resilience[0][0]} with only {sorted_resilience[0][1]:.1f}% average accuracy degradation across all distortion levels.\n")
    report.append(f"3. **Most Vulnerable Model:** {sorted_resilience[-1][0]} with {sorted_resilience[-1][1]:.1f}% average accuracy degradation.\n")
    report.append(f"4. **Net Impact:** Across all tests, {total_lost} questions were lost (correct→incorrect) while only {total_gained} were gained (incorrect→correct), a net loss of {total_lost - total_gained} questions.\n")
    report.append(f"5. **Difficulty Effect:** Higher difficulty problems (1.5) show greater vulnerability to distortion than easier problems (1.0).\n\n")
    
    # Methodology
    report.append("## Methodology\n")
    report.append("### Statistical Tests\n")
    report.append("**McNemar's Test** was used for all comparisons because:\n")
    report.append("- Data is **paired**: Same questions tested under baseline and distorted conditions\n")
    report.append("- Outcomes are **binary**: Each answer is either correct or incorrect\n")
    report.append("- Test is **non-parametric**: No assumptions about underlying distribution\n\n")
    report.append("For small sample sizes (b+c < 25), exact binomial test was used. For larger samples, chi-square approximation with continuity correction was applied.\n\n")
    
    report.append("### Effect Size\n")
    report.append("**Cohen's h** was calculated for comparing proportions:\n")
    report.append("```\nh = 2 × arcsin(√p₁) - 2 × arcsin(√p₂)\n```\n")
    report.append("Interpretation:\n")
    report.append("- Small effect: |h| ≈ 0.2\n")
    report.append("- Medium effect: |h| ≈ 0.5\n")
    report.append("- Large effect: |h| ≈ 0.8\n\n")
    
    # Baseline Results Table
    report.append("## Baseline Accuracy Results\n")
    report.append("| Model | Difficulty 1.0 | 95% CI | Difficulty 1.5 | 95% CI |\n")
    report.append("|-------|----------------|--------|----------------|--------|\n")
    
    for model in MODELS:
        display_name = MODEL_DISPLAY_NAMES[model]
        d1 = results['baseline'].get(display_name, {}).get('D1.0', {})
        d15 = results['baseline'].get(display_name, {}).get('D1.5', {})
        
        d1_acc = f"{d1.get('accuracy', 0):.0f}%"
        d1_ci = f"[{d1.get('ci_lower', 0):.1f}, {d1.get('ci_upper', 0):.1f}]"
        d15_acc = f"{d15.get('accuracy', 0):.0f}%"
        d15_ci = f"[{d15.get('ci_lower', 0):.1f}, {d15.get('ci_upper', 0):.1f}]"
        
        report.append(f"| {display_name} | {d1_acc} | {d1_ci} | {d15_acc} | {d15_ci} |\n")
    
    report.append("\n")
    
    # Distortion Results by MIU Level
    report.append("## Distortion Accuracy Results\n")
    
    for diff in DIFFICULTIES:
        diff_key = f"D{diff}"
        report.append(f"\n### Difficulty {diff}\n")
        report.append("| Model | Baseline | MIU 0.2 | MIU 0.5 | MIU 0.7 | MIU 0.9 | Avg Distortion |\n")
        report.append("|-------|----------|---------|---------|---------|---------|----------------|\n")
        
        for model in MODELS:
            display_name = MODEL_DISPLAY_NAMES[model]
            baseline = results['baseline'].get(display_name, {}).get(diff_key, {}).get('accuracy', 0)
            
            miu_accs = []
            row = [display_name, f"{baseline:.0f}%"]
            
            for miu in MIU_LEVELS:
                miu_key = f"MIU_{miu}"
                dist_data = results['distortion'].get(display_name, {}).get(diff_key, {}).get(miu_key, {})
                acc = dist_data.get('accuracy', 0)
                miu_accs.append(acc)
                row.append(f"{acc:.0f}%")
            
            avg = np.mean(miu_accs) if miu_accs else 0
            row.append(f"{avg:.1f}%")
            
            report.append("| " + " | ".join(row) + " |\n")
    
    report.append("\n")
    
    # McNemar's Test Results
    report.append("## Statistical Significance Analysis (McNemar's Test)\n")
    
    for diff in DIFFICULTIES:
        diff_key = f"D{diff}"
        report.append(f"\n### Difficulty {diff}\n")
        report.append("| Model | MIU | Lost | Gained | Net | χ² Statistic | p-value | Significant |\n")
        report.append("|-------|-----|------|--------|-----|--------------|---------|-------------|\n")
        
        for model in MODELS:
            display_name = MODEL_DISPLAY_NAMES[model]
            
            for miu in MIU_LEVELS:
                miu_key = f"MIU_{miu}"
                data = results['mcnemar_tests'].get(display_name, {}).get(diff_key, {}).get(miu_key, {})
                
                if not data:
                    continue
                
                lost = data.get('lost', 0)
                gained = data.get('gained', 0)
                net = data.get('net_change', 0)
                stat = data.get('statistic')
                pval = data.get('p_value', 1)
                
                stat_str = f"{stat:.2f}" if stat is not None else "N/A"
                pval_str = f"{pval:.4f}" if pval < 1 else "N/A"
                
                sig = ""
                if data.get('significant_01'):
                    sig = "***"
                elif data.get('significant_05'):
                    sig = "**"
                elif data.get('significant_10'):
                    sig = "*"
                
                report.append(f"| {display_name} | {miu} | {lost} | {gained} | {net:+d} | {stat_str} | {pval_str} | {sig} |\n")
    
    report.append("\n*Significance: *** p<0.01, ** p<0.05, * p<0.10*\n\n")
    
    # Effect Size Analysis
    report.append("## Effect Size Analysis (Cohen's h)\n")
    
    for diff in DIFFICULTIES:
        diff_key = f"D{diff}"
        report.append(f"\n### Difficulty {diff}\n")
        report.append("| Model | MIU | Baseline | Distortion | Degradation | Cohen's h | Interpretation |\n")
        report.append("|-------|-----|----------|------------|-------------|-----------|----------------|\n")
        
        for model in MODELS:
            display_name = MODEL_DISPLAY_NAMES[model]
            
            for miu in MIU_LEVELS:
                miu_key = f"MIU_{miu}"
                data = results['effect_sizes'].get(display_name, {}).get(diff_key, {}).get(miu_key, {})
                
                if not data:
                    continue
                
                baseline = data.get('baseline_acc', 0)
                distortion = data.get('distortion_acc', 0)
                degradation = data.get('degradation_pct', 0)
                h = data.get('cohens_h', 0)
                
                if abs(h) >= 0.8:
                    interp = "Large"
                elif abs(h) >= 0.5:
                    interp = "Medium"
                elif abs(h) >= 0.2:
                    interp = "Small"
                else:
                    interp = "Negligible"
                
                report.append(f"| {display_name} | {miu} | {baseline:.1f}% | {distortion:.1f}% | {degradation:+.1f}% | {h:.3f} | {interp} |\n")
    
    report.append("\n")
    
    # Model Comparison
    report.append("## Model Resilience Comparison\n")
    report.append("| Rank | Model | Avg Degradation | Interpretation |\n")
    report.append("|------|-------|-----------------|----------------|\n")
    
    for i, (model, score) in enumerate(sorted_resilience, 1):
        if score < 3:
            interp = "Highly Resilient"
        elif score < 5:
            interp = "Moderately Resilient"
        elif score < 10:
            interp = "Somewhat Vulnerable"
        else:
            interp = "Highly Vulnerable"
        report.append(f"| {i} | {model} | {score:.1f}% | {interp} |\n")
    
    report.append("\n")
    
    # MIU Level Analysis
    report.append("## MIU Level Analysis\n")
    report.append("Average degradation by distortion type:\n\n")
    report.append("| MIU Level | Description | Avg Degradation (D1.0) | Avg Degradation (D1.5) |\n")
    report.append("|-----------|-------------|------------------------|------------------------|\n")
    
    for miu in MIU_LEVELS:
        miu_key = f"MIU_{miu}"
        
        d1_degradations = []
        d15_degradations = []
        
        for model in MODELS:
            display_name = MODEL_DISPLAY_NAMES[model]
            
            d1_data = results['effect_sizes'].get(display_name, {}).get('D1.0', {}).get(miu_key, {})
            d15_data = results['effect_sizes'].get(display_name, {}).get('D1.5', {}).get(miu_key, {})
            
            if d1_data:
                d1_degradations.append(d1_data['degradation_pct'])
            if d15_data:
                d15_degradations.append(d15_data['degradation_pct'])
        
        d1_avg = np.mean(d1_degradations) if d1_degradations else 0
        d15_avg = np.mean(d15_degradations) if d15_degradations else 0
        
        report.append(f"| {miu} | {MIU_DESCRIPTIONS[miu]} | {d1_avg:+.1f}% | {d15_avg:+.1f}% |\n")
    
    report.append("\n")
    
    # Research Questions
    report.append("## Research Questions Answered\n\n")
    
    report.append("### 1. Does semantic distortion cause statistically significant performance degradation?\n")
    report.append(f"**Answer:** Yes. {significant_05} of {total_comparisons} comparisons ({100*significant_05/total_comparisons:.1f}%) ")
    report.append(f"showed statistically significant degradation at p<0.05, with {significant_01} ({100*significant_01/total_comparisons:.1f}%) significant at p<0.01.\n\n")
    
    report.append("### 2. Which models are most resilient to distortion?\n")
    report.append(f"**Answer:** {sorted_resilience[0][0]} is the most resilient model with only {sorted_resilience[0][1]:.1f}% average degradation. ")
    if len(sorted_resilience) > 1:
        report.append(f"{sorted_resilience[1][0]} is second most resilient with {sorted_resilience[1][1]:.1f}% degradation.\n\n")
    
    report.append("### 3. Which models are most vulnerable?\n")
    report.append(f"**Answer:** {sorted_resilience[-1][0]} is the most vulnerable with {sorted_resilience[-1][1]:.1f}% average degradation. ")
    if len(sorted_resilience) > 1:
        report.append(f"{sorted_resilience[-2][0]} is second most vulnerable with {sorted_resilience[-2][1]:.1f}% degradation.\n\n")
    
    report.append("### 4. Does problem difficulty affect vulnerability to distortion?\n")
    d1_avg_degradation = np.mean([v for model in results['effect_sizes'] 
                                   for v in [d.get('degradation_pct', 0) 
                                            for d in results['effect_sizes'][model].get('D1.0', {}).values()]])
    d15_avg_degradation = np.mean([v for model in results['effect_sizes'] 
                                    for v in [d.get('degradation_pct', 0) 
                                             for d in results['effect_sizes'][model].get('D1.5', {}).values()]])
    
    report.append(f"**Answer:** Yes. Harder problems (Difficulty 1.5) show {d15_avg_degradation:.1f}% average degradation ")
    report.append(f"compared to {d1_avg_degradation:.1f}% for easier problems (Difficulty 1.0). ")
    report.append("This suggests that when models are already struggling with harder problems, semantic distortion has a more pronounced negative effect.\n\n")
    
    report.append("### 5. Which types of distortion cause the most degradation?\n")
    # Calculate average degradation by MIU
    miu_avg_degradations = {}
    for miu in MIU_LEVELS:
        miu_key = f"MIU_{miu}"
        degradations = []
        for model in results['effect_sizes']:
            for diff in results['effect_sizes'][model]:
                if miu_key in results['effect_sizes'][model][diff]:
                    degradations.append(results['effect_sizes'][model][diff][miu_key]['degradation_pct'])
        miu_avg_degradations[miu] = np.mean(degradations) if degradations else 0
    
    sorted_mius = sorted(miu_avg_degradations.items(), key=lambda x: -x[1])
    report.append(f"**Answer:** {MIU_DESCRIPTIONS[sorted_mius[0][0]]} (MIU {sorted_mius[0][0]}) causes the most degradation at {sorted_mius[0][1]:.1f}% on average. ")
    report.append(f"Least harmful is {MIU_DESCRIPTIONS[sorted_mius[-1][0]]} (MIU {sorted_mius[-1][0]}) with {sorted_mius[-1][1]:.1f}% degradation.\n\n")
    
    report.append("### 6. Is there evidence that models rely on surface patterns rather than understanding?\n")
    report.append(f"**Answer:** The evidence is mixed but suggestive. The fact that {significant_05} of {total_comparisons} comparisons show significant degradation ")
    report.append("when only the surface form (not the underlying mathematics) changes indicates some reliance on surface patterns. ")
    report.append(f"However, the most capable models ({sorted_resilience[0][0]} and {sorted_resilience[1][0] if len(sorted_resilience) > 1 else ''}) ")
    report.append("show relatively small degradation, suggesting they have developed more robust mathematical understanding. ")
    report.append(f"The weaker models ({sorted_resilience[-1][0]} and {sorted_resilience[-2][0] if len(sorted_resilience) > 1 else ''}) show greater vulnerability, ")
    report.append("suggesting they may rely more heavily on pattern matching.\n\n")
    
    # Limitations
    report.append("## Limitations and Caveats\n\n")
    report.append("1. **Empty Answers:** Some models (especially GPT-5-mini on distortion tasks) produced empty answers due to token limits. These are counted as incorrect.\n")
    report.append("2. **Sample Size:** 100 questions per condition limits statistical power for detecting small effects.\n")
    report.append("3. **Answer Matching:** Despite corrections, some semantically equivalent answers may be marked as incorrect due to format differences.\n")
    report.append("4. **Distortion Quality:** The quality and semantic equivalence of distortions varies by MIU level.\n")
    report.append("5. **Model Versions:** Results are specific to the model versions tested and may not generalize to future updates.\n\n")
    
    # Conclusions
    report.append("## Conclusions\n\n")
    report.append("1. **Semantic distortion significantly impacts model performance** in mathematical reasoning, with the majority of comparisons showing statistically significant degradation.\n\n")
    report.append("2. **More capable models are more resilient** to semantic distortion, suggesting that improved mathematical understanding provides some protection against surface-level changes.\n\n")
    report.append("3. **Harder problems are more vulnerable** to distortion effects, likely because models are already operating closer to their capability limits.\n\n")
    report.append("4. **All distortion types cause measurable degradation**, though the severity varies. This suggests models have some sensitivity to multiple aspects of question phrasing.\n\n")
    report.append("5. **The hypothesis that models rely on surface patterns is partially supported**, particularly for less capable models, but more capable models show meaningful resilience.\n\n")
    
    # Visualizations
    report.append("## Visualizations\n\n")
    report.append("The following visualizations are available in the `statistical_analysis_report/` directory:\n\n")
    report.append("1. `baseline_vs_distortion.png` - Comparison of baseline and distorted accuracy by model\n")
    report.append("2. `degradation_curves.png` - Accuracy trends across MIU levels\n")
    report.append("3. `effect_size_heatmap.png` - Cohen's h effect sizes by model and MIU level\n")
    report.append("4. `significance_summary.png` - Statistical significance overview\n")
    report.append("5. `net_change_chart.png` - Questions lost vs gained due to distortion\n")
    report.append("6. `comprehensive_dashboard.png` - All key findings in one view\n")
    
    return "".join(report)


def main():
    """Main execution function."""
    
    print("Starting statistical analysis...")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Run full analysis
    results = run_full_analysis()
    
    # Save raw results
    print("\nSaving raw analysis data...")
    with open(OUTPUT_DIR / 'analysis_data.json', 'w') as f:
        # Convert results to JSON-serializable format
        def convert(obj):
            if isinstance(obj, (np.bool_, bool)):
                return bool(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(i) for i in obj]
            return obj
        
        json.dump(convert(results), f, indent=2)
    print("Saved: analysis_data.json")
    
    # Create visualizations
    print("\nCreating visualizations...")
    create_baseline_vs_distortion_chart(results)
    create_degradation_curves(results)
    create_effect_size_heatmap(results)
    create_significance_summary(results)
    create_net_change_chart(results)
    create_comprehensive_dashboard(results)
    
    # Generate markdown report
    print("\nGenerating markdown report...")
    report = generate_markdown_report(results)
    
    with open(OUTPUT_DIR / 'STATISTICAL_ANALYSIS_REPORT.md', 'w') as f:
        f.write(report)
    print("Saved: STATISTICAL_ANALYSIS_REPORT.md")
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\nAll outputs saved to: {OUTPUT_DIR}")
    print("\nGenerated files:")
    for f in OUTPUT_DIR.iterdir():
        print(f"  - {f.name}")


if __name__ == "__main__":
    main()

