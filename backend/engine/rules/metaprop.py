"""
metaprop 命令 — 率的 Meta 分析
Stata: metaprop events total, random
"""
METAPROP_RULES = {
    "command": "metaprop",
    "python_package": "numpy+scipy",
    "model_map": {
        "random": "DL",
        "randomi": "DL",
        "fixed": "FE",
        "fixedi": "FE",
    },
    "option_map": {
        "lcols": "label_cols",
        "by": "subgroup",
        "xlabel": "xlim",
        "cimethod": "ci_method",
        "ftt": "freeman_tukey",    # Freeman-Tukey 双重反正弦变换
        "logit": "logit",
        "exact": "exact",
    },
    "code_template": '''# -*- coding: utf-8 -*-
"""Auto-generated from Stata metaprop — proportion meta-analysis"""
import numpy as np
from scipy import stats

# 数据 ====
{data_block}

events = np.array([{events_values}])
totals = np.array([{totals_values}])
raw_props = events / totals

# 使用 Freeman-Tukey 双重反正弦变换（推荐方法）
t = np.arcsin(np.sqrt(events / (totals + 1))) + np.arcsin(np.sqrt((events + 1) / (totals + 1)))
se_t = np.sqrt(1.0 / (totals + 0.5))

# 逆变换函数
inv_ft = lambda t, n: 0.5 * (1 - np.sign(np.cos(t)) * np.sqrt(1 - (np.sin(t) + (np.sin(t) - 1/np.sin(t))/n)**2))

# Meta 分析 ====
weights = 1.0 / (se_t ** 2)
Q = np.sum(weights * (t - np.average(t, weights=weights))**2)
df = len(t) - 1
I_squared = max(0, (Q - df) / Q * 100) if Q > 0 else 0
p_hetero = 1 - stats.chi2.cdf(Q, df) if df > 0 else 1.0

if "{model}" == "DL":
    C = np.sum(weights) - np.sum(weights**2) / np.sum(weights)
    tau2 = max(0, (Q - df) / C) if Q > df else 0
    w_star = 1.0 / (se_t**2 + tau2)
    pooled_t = np.sum(w_star * t) / np.sum(w_star)
    se_pooled = np.sqrt(1.0 / np.sum(w_star))
elif "{model}" == "FE":
    w_star = weights
    pooled_t = np.sum(w_star * t) / np.sum(w_star)
    se_pooled = np.sqrt(1.0 / np.sum(w_star))
    tau2 = 0
else:
    tau2 = max(0, (Q - df) / (np.sum(weights) - np.sum(weights**2)/np.sum(weights)))
    w_star = 1.0 / (se_t**2 + tau2)
    pooled_t = np.sum(w_star * t) / np.sum(w_star)
    se_pooled = np.sqrt(1.0 / np.sum(w_star))

# 反变换回比例
pooled_prop = (np.sin(pooled_t / 2)) ** 2
t_ci_lower = pooled_t - 1.96 * se_pooled
t_ci_upper = pooled_t + 1.96 * se_pooled
ci_lower = (np.sin(t_ci_lower / 2)) ** 2
ci_upper = (np.sin(t_ci_upper / 2)) ** 2
z_score = pooled_t / se_pooled
p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

H_squared = Q / df if df > 0 else 1.0
if "{model}" == "FE":
    pi_lower, pi_upper = ci_lower, ci_upper
else:
    pi_se = np.sqrt(tau2 + se_pooled**2)
    pi_lower = max(0.0, (np.sin((pooled_t - 1.96 * pi_se) / 2)) ** 2)
    pi_upper = min(1.0, (np.sin((pooled_t + 1.96 * pi_se) / 2)) ** 2)

print("=== Meta-Analysis of Proportions ===")
print(f"Number of studies: {len(t)}")
print(f"Model: {model_desc}")
print(f"Effect-size label: {effect_measure}")
print(f"Method: {'Freeman-Tukey Double Arcsine'}")
print(f"Pooled Proportion: {pooled_prop:.{dp}f}")
print(f"95% CI: [{ci_lower:.{dp}f}, {ci_upper:.{dp}f}]")
print(f"Prediction Interval: [{pi_lower:.{dp}f}, {pi_upper:.{dp}f}]")
print(f"z = {z_score:.2f}, p = {p_value:.{dp}f}")
print(f"I-squared = {I_squared:.1f}%")
print(f"H-squared = {H_squared:.2f}")
print(f"Q = {Q:.2f}, df = {df}, p = {p_hetero:.{dp}f}")
print(f"tau-squared = {tau2:.{dp}f}")
print(f"Study Proportions: {np.round(raw_props, {dp})}")
''',
}