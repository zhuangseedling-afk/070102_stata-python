"""
funnel / metafunnel 命令 — 漏斗图
Stata: funnel es se
       metafunnel es se, by(subgroup)
"""
FUNNEL_RULES = {
    "command": "funnel",
    "python_package": "matplotlib",
    "option_map": {
        "xlabel": "xlab",
        "ylabel": "ylab",
        "by": "subgroup",
        "egger": "egger_test",
    },
    "code_template": '''# -*- coding: utf-8 -*-
"""Auto-generated from Stata funnel — funnel plot"""
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# 数据 ====
{data_block}

es = np.array([{es_values}])
se = np.array([{se_values}])

# 漏斗图 ====
fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(es, se, c='steelblue', s=60, edgecolors='white', zorder=3)

# 伪 95% 置信区间
es_pooled = np.average(es, weights=1.0/se**2)
se_range = np.linspace(0, max(se)*1.1, 100)
for z in [1.96, 1.0]:
    ax.plot(es_pooled - z * se_range, se_range, 'k--', linewidth=0.5, alpha=0.5)
    ax.plot(es_pooled + z * se_range, se_range, 'k--', linewidth=0.5, alpha=0.5)

ax.axvline(es_pooled, color='red', linewidth=1, linestyle='-', alpha=0.7)
ax.set_xlabel("Effect Size")
ax.set_ylabel("Standard Error")
ax.set_title("Funnel Plot")
ax.invert_yaxis()
plt.tight_layout()
plt.savefig("funnel_plot.png", dpi=150)
print("Funnel plot saved to funnel_plot.png")

# Egger 检验 ====
precision = 1.0 / se
SND = es / se
intercept = np.polyfit(precision, SND, 1)[0]
se_intercept = np.sqrt(np.sum((SND - np.polyval([intercept, np.mean(SND)], precision))**2) / (len(es)-2) / np.sum((precision - np.mean(precision))**2))
t_egger = intercept / se_intercept
p_egger = 2 * (1 - stats.t.cdf(abs(t_egger), len(es)-2))
print(f"Egger's test: intercept = {intercept:.4f}, SE = {se_intercept:.4f}, t = {t_egger:.2f}, p = {p_egger:.4f}")
''',
}