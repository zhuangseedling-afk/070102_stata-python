"""
forest 命令 — 森林图
Stata: forest es lci uci, lcols(study year)
"""
FOREST_RULES = {
    "command": "forest",
    "python_package": "matplotlib",
    "option_map": {
        "lcols": "label_cols",
        "rcols": "right_cols",
        "xlabel": "xlab",
        "title": "title",
        "diamond": "diamond_color",
        "boxsca": "box_scale",
        "texts": "text_size",
    },
    "code_template": '''# -*- coding: utf-8 -*-
"""Auto-generated from Stata forest — forest plot"""
import numpy as np
import matplotlib.pyplot as plt

# 数据 ====
{data_block}

es = np.array([{es_values}])
lci = np.array([{lci_values}])
uci = np.array([{uci_values}])
labels = {labels_array}

# 森林图 ====
fig, ax = plt.subplots(figsize=(10, {fig_height}))

n_studies = len(es)
y_positions = list(range(n_studies))

for i in range(n_studies):
    ax.plot([lci[i], uci[i]], [i, i], 'k-', linewidth=1.5)
    size = max(20, 1.0 / (uci[i] - lci[i])**2 * 10)
    ax.scatter(es[i], i, s=size, c='steelblue', edgecolors='black', linewidth=0.5, zorder=3)

# 汇总效应（菱形）
weights = 1.0 / ((uci - lci) / (2 * 1.96))**2
pooled_es = np.sum(weights * es) / np.sum(weights)
se_pooled = np.sqrt(1.0 / np.sum(weights))
ci_pooled = [pooled_es - 1.96 * se_pooled, pooled_es + 1.96 * se_pooled]

y_diamond = -1
ax.plot(ci_pooled, [y_diamond, y_diamond], 'k-', linewidth=1.5)
ax.scatter(pooled_es, y_diamond, marker='D', s=80, c='red', edgecolors='black', zorder=4)

# 零线
ax.axvline(0, color='gray', linewidth=0.8, linestyle='--')

# 标签
ax.set_yticks([-1] + y_positions)
ax.set_yticklabels(['Summary'] + list(labels))
ax.set_xlabel("Effect Size")
ax.set_title("Forest Plot")
ax.invert_yaxis()
plt.tight_layout()
plt.savefig("forest_plot.png", dpi=150)
print("Forest plot saved to forest_plot.png")
print(f"Pooled ES: {pooled_es:.4f}, 95% CI: [{ci_pooled[0]:.4f}, {ci_pooled[1]:.4f}]")
''',
}