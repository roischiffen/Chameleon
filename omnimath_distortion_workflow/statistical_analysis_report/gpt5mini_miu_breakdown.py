#!/usr/bin/env python3
"""
GPT-5-mini Per-MIU Accuracy Breakdown Visualization
Shows the dramatic degradation at each MIU level for both difficulties.
"""

import matplotlib.pyplot as plt
import numpy as np

# GPT-5-mini data from analysis_data.json
data = {
    "Difficulty 1.0": {
        "Baseline": 96.0,
        "MIU 0.2": 84.0,
        "MIU 0.5": 81.4,
        "MIU 0.7": 87.0,
        "MIU 0.9": 81.0
    },
    "Difficulty 1.5": {
        "Baseline": 89.0,
        "MIU 0.2": 68.0,
        "MIU 0.5": 65.3,
        "MIU 0.7": 65.0,
        "MIU 0.9": 59.6
    }
}

# Statistical significance (McNemar p-values)
p_values = {
    "Difficulty 1.0": {
        "MIU 0.2": 0.0018,
        "MIU 0.5": 0.00027,
        "MIU 0.7": 0.012,
        "MIU 0.9": 0.00027
    },
    "Difficulty 1.5": {
        "MIU 0.2": 5.7e-6,
        "MIU 0.5": 1.1e-5,
        "MIU 0.7": 6.5e-6,
        "MIU 0.9": 4.9e-7
    }
}

# Setup
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150
plt.rcParams['font.family'] = 'DejaVu Sans'

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('GPT-5-mini: Accuracy Degradation by MIU Level\n(All comparisons statistically significant, p<0.05)', 
             fontsize=14, fontweight='bold', y=1.02)

conditions = ["Baseline", "MIU 0.2", "MIU 0.5", "MIU 0.7", "MIU 0.9"]
colors = ['#2E86AB', '#F18F01', '#F18F01', '#F18F01', '#C73E1D']  # Blue baseline, Orange MIUs, Red worst

for idx, (diff_name, diff_data) in enumerate(data.items()):
    ax = axes[idx]
    
    accuracies = [diff_data[c] for c in conditions]
    baseline = accuracies[0]
    
    # Create bars
    x = np.arange(len(conditions))
    bars = ax.bar(x, accuracies, color=colors, edgecolor='black', linewidth=1.5)
    
    # Add baseline reference line
    ax.axhline(y=baseline, color='#2E86AB', linestyle='--', linewidth=2, alpha=0.7, 
               label=f'Baseline: {baseline:.0f}%')
    
    # Add value labels and degradation
    for i, (bar, acc) in enumerate(zip(bars, accuracies)):
        height = bar.get_height()
        
        # Accuracy value
        ax.annotate(f'{acc:.1f}%',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 5), textcoords="offset points",
                   ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        # Degradation label (skip baseline)
        if i > 0:
            degradation = baseline - acc
            ax.annotate(f'↓{degradation:.1f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height - 3),
                       xytext=(0, -15), textcoords="offset points",
                       ha='center', va='top', fontsize=9, color='darkred', fontweight='bold')
            
            # Significance stars
            p = p_values[diff_name][conditions[i]]
            if p < 0.001:
                stars = '***'
            elif p < 0.01:
                stars = '**'
            else:
                stars = '*'
            ax.annotate(stars,
                       xy=(bar.get_x() + bar.get_width() / 2, height + 8),
                       ha='center', va='bottom', fontsize=10, color='red')
    
    # Formatting
    ax.set_xlabel('Condition', fontsize=12)
    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_title(f'{diff_name}', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(conditions, rotation=0, fontsize=10)
    ax.set_ylim(0, 110)
    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=0.3)
    
    # Color the baseline bar differently
    bars[0].set_color('#2E86AB')
    bars[0].set_hatch('')
    
    # Add hatching to distortion bars
    for bar in bars[1:]:
        bar.set_hatch('///')

# Add summary stats at bottom
total_d10 = data["Difficulty 1.0"]["Baseline"] - np.mean([data["Difficulty 1.0"][f"MIU {m}"] for m in [0.2, 0.5, 0.7, 0.9]])
total_d15 = data["Difficulty 1.5"]["Baseline"] - np.mean([data["Difficulty 1.5"][f"MIU {m}"] for m in [0.2, 0.5, 0.7, 0.9]])

fig.text(0.5, -0.02, 
         f'Average Degradation:  D1.0 = {total_d10:.1f}%  |  D1.5 = {total_d15:.1f}%  |  Overall = {(total_d10+total_d15)/2:.1f}%\n'
         f'Significance: * p<0.05, ** p<0.01, *** p<0.001 (McNemar\'s test)',
         ha='center', fontsize=10, style='italic')

plt.tight_layout()
plt.savefig('/Users/schiffen/RESEARCH-PROJECT-REPO/Chameleon/omnimath_distortion_workflow/statistical_analysis_report/gpt5mini_miu_breakdown.png', 
            bbox_inches='tight', facecolor='white')
plt.close()

print("✅ Saved: gpt5mini_miu_breakdown.png")
print(f"\nGPT-5-mini Summary:")
print(f"  Difficulty 1.0: {data['Difficulty 1.0']['Baseline']:.0f}% → {np.mean([data['Difficulty 1.0'][f'MIU {m}'] for m in [0.2, 0.5, 0.7, 0.9]]):.1f}% avg ({total_d10:.1f}% drop)")
print(f"  Difficulty 1.5: {data['Difficulty 1.5']['Baseline']:.0f}% → {np.mean([data['Difficulty 1.5'][f'MIU {m}'] for m in [0.2, 0.5, 0.7, 0.9]]):.1f}% avg ({total_d15:.1f}% drop)")



