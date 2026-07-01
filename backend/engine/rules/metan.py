"""
metan 命令规则映射表 — 最常用的 Meta 分析命令

Stata 语法示例:
  metan es se, random lcols(author year) xlabel(0.1, 0.5, 1, 2, 5) texts(180)
"""
METAN_RULES = {
    "command": "metan",
    "python_package": "numpy+scipy",  # 基于 statsmodels 的 DIY 实现
    "model_map": {
        "random": "DL",       # DerSimonian-Laird 随机效应
        "randomi": "DL",
        "fixed": "FE",        # 固定效应（逆方差加权）
        "fixedi": "FE",
        "reml": "REML",       # Restricted Maximum Likelihood
        "ml": "ML",
    },
    "effect_measure_map": {
        "": "generic",        # 默认：通用效应量
        "or": "odds_ratio",
        "rr": "risk_ratio",
        "rd": "risk_difference",
        "smd": "std_mean_diff",
        "md": "mean_diff",
        "hr": "hazard_ratio",
    },
    "option_map": {
        "lcols": "study_labels",     # 研究标签列
        "rcols": "extra_cols",        # 右侧额外列
        "xlabel": "xlim",
        "texts": "text_size",
        "by": "subgroup",            # 亚组分析
        "sortby": "sort_col",
        "nostandard": "no_standard",  # 不显示标准图
        "nowt": "no_weights",        # 不显示权重
        "nograph": "no_graph",
        "effect": "effect_label",
        "label": "label_name",
        "lcols": "label_cols",
        "rcols": "right_cols",
        "astext": "annotate_size",
        "boxsca": "box_scale",
        "diamond": "diamond_color",
        "dp": "decimal_places",
    },
    "code_template": '''# -*- coding: utf-8 -*-
"""Auto-generated from Stata metan command"""
import numpy as np
from scipy import stats

# 数据 ====
{data_block}

# 效应量 (es) 和标准误 (se) ====
es = np.array([{es_values}])
se = np.array([{se_values}])

# 计算权重 ====
weights = 1.0 / (se ** 2)

# 异质性统计 ====
Q = np.sum(weights * (es - np.average(es, weights=weights))**2)
df = len(es) - 1
I_squared = max(0, (Q - df) / Q * 100) if Q > 0 else 0
p_hetero = 1 - stats.chi2.cdf(Q, df) if df > 0 else 1.0

# tau² 估计量选择 ====
tau2_est = "{tau2_estimator}"
S1 = np.sum(weights)
S2 = np.sum(weights**2)
if tau2_est == "DL":
    C = S1 - S2 / S1
    tau2 = max(0.0, (Q - df) / C) if Q > df else 0.0
elif tau2_est == "Hedges":
    C = S1 - S2 / S1
    tau2 = max(0.0, (Q - df) / C)
elif tau2_est in ("REML", "ML"):
    # 迭代 REML/ML 估计（固定效应为初始值）
    tau2 = max(0.0, (Q - df) / (S1 - S2 / S1))
    for _ in range(50):
        w_i = 1.0 / (se**2 + tau2)
        theta = np.sum(w_i * es) / np.sum(w_i)
        if tau2_est == "REML":
            denom = np.sum(w_i**2)
            num = np.sum(w_i**2 * ((es - theta)**2 - se**2))
            new_tau2 = max(0.0, num / denom)
        else:  # ML
            denom = np.sum(w_i**2)
            num = np.sum(w_i**2 * ((es - theta)**2 - se**2)) + 0.5 * np.sum((w_i**2) * (se**2) / (se**2 + tau2))
            new_tau2 = max(0.0, num / denom)
        if abs(new_tau2 - tau2) < 1e-6:
            break
        tau2 = new_tau2
elif tau2_est == "SJ":
    # Sidik-Jonkman
    theta_fe = np.sum(weights * es) / S1
    tau2 = max(0.0, np.sum((es - theta_fe)**2) / df - np.mean(se**2))
elif tau2_est == "HS":
    # Hunter-Schmidt 需要样本量；SE-only 场景退回到 DL
    C = S1 - S2 / S1
    tau2 = max(0.0, (Q - df) / C) if Q > df else 0.0
elif tau2_est == "EB":
    # Empirical Bayes（迭代）
    tau2 = max(0.0, (Q - df) / (S1 - S2 / S1))
    for _ in range(50):
        w_i = 1.0 / (se**2 + tau2)
        theta = np.sum(w_i * es) / np.sum(w_i)
        num = np.sum((w_i**2) * ((es - theta)**2 - se**2))
        denom = np.sum(w_i**2)
        new_tau2 = max(0.0, tau2 * num / denom)
        if abs(new_tau2 - tau2) < 1e-6:
            break
        tau2 = new_tau2
else:
    tau2 = 0.0

# 模型拟合 ====
if "{model}" in ("FE", "CE"):
    w_star = weights
    pooled_es = np.sum(w_star * es) / np.sum(w_star)
    se_pooled = np.sqrt(1.0 / np.sum(w_star))
    tau2 = 0.0
else:
    w_star = 1.0 / (se**2 + tau2)
    pooled_es = np.sum(w_star * es) / np.sum(w_star)
    se_pooled = np.sqrt(1.0 / np.sum(w_star))

# 置信区间 ====
confidence_level = {confidence_level}
z_alpha = {z_alpha}
ci_lower = pooled_es - z_alpha * se_pooled
ci_upper = pooled_es + z_alpha * se_pooled
z_score = pooled_es / se_pooled
p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

# eform 转换（OR/RR 场景）====
eform = {eform}
if eform:
    display_es = np.exp(pooled_es)
    display_ci_lower = np.exp(ci_lower)
    display_ci_upper = np.exp(ci_upper)
else:
    display_es = pooled_es
    display_ci_lower = ci_lower
    display_ci_upper = ci_upper

# H² 与预测区间 ====
H_squared = Q / df if df > 0 else 1.0
if "{model}" in ("FE", "CE"):
    pi_lower, pi_upper = display_ci_lower, display_ci_upper
else:
    pi_se = np.sqrt(tau2 + se_pooled**2)
    pi_lower = pooled_es - z_alpha * pi_se
    pi_upper = pooled_es + z_alpha * pi_se
    if eform:
        pi_lower = np.exp(pi_lower)
        pi_upper = np.exp(pi_upper)

# 输出 ====
print("=== Meta Analysis Results ===")
print(f"Number of studies: {len(es)}")
print(f"Model: {model_desc}")
print(f"Effect-size label: {effect_measure}")
print(f"Method: {tau2_est if '{model}' not in ('FE', 'CE') else 'Inverse-variance'}")
print(f"tau² estimator: {tau2_est}")
print(f"Confidence level: {confidence_level}%")
print(f"Pooled Effect Size: {display_es:.{dp}f}")
print(f"{confidence_level:.0f}% CI: [{display_ci_lower:.{dp}f}, {display_ci_upper:.{dp}f}]")
print(f"Prediction Interval: [{pi_lower:.{dp}f}, {pi_upper:.{dp}f}]")
print(f"z = {z_score:.2f}, p = {p_value:.{dp}f}")
print(f"I-squared = {I_squared:.1f}%")
print(f"H-squared = {H_squared:.2f}")
print(f"Q = {Q:.2f}, df = {df}, p = {p_hetero:.{dp}f}")
print(f"tau-squared = {tau2:.{dp}f}")
print(f"Study Weights: {np.round(w_star, {dp})}")
print(f"Study Effects: {np.round(es, {dp})}")
''',
}

# metan 子命令（如 metan es lci uci, ... 使用CI列而非SE列）
METAN_CI_RULES = {
    "command": "metan_ci",
    "python_package": "numpy+scipy",
    "option_map": {
        "random": "DL",
        "randomi": "DL",
        "fixed": "FE",
        "fixedi": "FE",
        "lcols": "label_cols",
        "by": "subgroup",
    },
    "code_template": '''# -*- coding: utf-8 -*-
"""Auto-generated from Stata metan (CI format)"""
import numpy as np
from scipy import stats

# 数据 ====
{data_block}

es = np.array([{es_values}])
lci = np.array([{lci_values}])
uci = np.array([{uci_values}])

# 从 CI 反推 SE（仅当无原始 SE 时使用）====
confidence_level = {confidence_level}
z_alpha_ref = {z_alpha}
se = (uci - lci) / (2 * z_alpha_ref)

# 后续同 metan ====
weights = 1.0 / (se ** 2)
Q = np.sum(weights * (es - np.average(es, weights=weights))**2)
df = len(es) - 1
I_squared = max(0, (Q - df) / Q * 100) if Q > 0 else 0
p_hetero = 1 - stats.chi2.cdf(Q, df) if df > 0 else 1.0

# tau² 估计量选择 ====
tau2_est = "{tau2_estimator}"
S1 = np.sum(weights)
S2 = np.sum(weights**2)
if tau2_est == "DL":
    C = S1 - S2 / S1
    tau2 = max(0.0, (Q - df) / C) if Q > df else 0.0
elif tau2_est == "Hedges":
    C = S1 - S2 / S1
    tau2 = max(0.0, (Q - df) / C)
elif tau2_est in ("REML", "ML"):
    tau2 = max(0.0, (Q - df) / (S1 - S2 / S1))
    for _ in range(50):
        w_i = 1.0 / (se**2 + tau2)
        theta = np.sum(w_i * es) / np.sum(w_i)
        if tau2_est == "REML":
            denom = np.sum(w_i**2)
            num = np.sum(w_i**2 * ((es - theta)**2 - se**2))
            new_tau2 = max(0.0, num / denom)
        else:
            denom = np.sum(w_i**2)
            num = np.sum(w_i**2 * ((es - theta)**2 - se**2)) + 0.5 * np.sum((w_i**2) * (se**2) / (se**2 + tau2))
            new_tau2 = max(0.0, num / denom)
        if abs(new_tau2 - tau2) < 1e-6:
            break
        tau2 = new_tau2
elif tau2_est == "SJ":
    theta_fe = np.sum(weights * es) / S1
    tau2 = max(0.0, np.sum((es - theta_fe)**2) / df - np.mean(se**2))
elif tau2_est == "HS":
    C = S1 - S2 / S1
    tau2 = max(0.0, (Q - df) / C) if Q > df else 0.0
elif tau2_est == "EB":
    tau2 = max(0.0, (Q - df) / (S1 - S2 / S1))
    for _ in range(50):
        w_i = 1.0 / (se**2 + tau2)
        theta = np.sum(w_i * es) / np.sum(w_i)
        num = np.sum((w_i**2) * ((es - theta)**2 - se**2))
        denom = np.sum(w_i**2)
        new_tau2 = max(0.0, tau2 * num / denom)
        if abs(new_tau2 - tau2) < 1e-6:
            break
        tau2 = new_tau2
else:
    tau2 = 0.0

if "{model}" in ("FE", "CE"):
    w_star = weights
    pooled_es = np.sum(w_star * es) / np.sum(w_star)
    se_pooled = np.sqrt(1.0 / np.sum(w_star))
    tau2 = 0.0
else:
    w_star = 1.0 / (se**2 + tau2)
    pooled_es = np.sum(w_star * es) / np.sum(w_star)
    se_pooled = np.sqrt(1.0 / np.sum(w_star))

z_alpha = z_alpha_ref
ci_lower = pooled_es - z_alpha * se_pooled
ci_upper = pooled_es + z_alpha * se_pooled
z_score = pooled_es / se_pooled
p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

eform = {eform}
if eform:
    display_es = np.exp(pooled_es)
    display_ci_lower = np.exp(ci_lower)
    display_ci_upper = np.exp(ci_upper)
else:
    display_es = pooled_es
    display_ci_lower = ci_lower
    display_ci_upper = ci_upper

# H² 与预测区间 ====
H_squared = Q / df if df > 0 else 1.0
if "{model}" in ("FE", "CE"):
    pi_lower, pi_upper = display_ci_lower, display_ci_upper
else:
    pi_se = np.sqrt(tau2 + se_pooled**2)
    pi_lower = pooled_es - z_alpha * pi_se
    pi_upper = pooled_es + z_alpha * pi_se
    if eform:
        pi_lower = np.exp(pi_lower)
        pi_upper = np.exp(pi_upper)

print("=== Meta Analysis Results ===")
print(f"Number of studies: {len(es)}")
print(f"Model: {model_desc}")
print(f"Effect-size label: {effect_measure}")
print(f"Method: {tau2_est if '{model}' not in ('FE', 'CE') else 'Inverse-variance'}")
print(f"tau² estimator: {tau2_est}")
print(f"Confidence level: {confidence_level}%")
print(f"Pooled Effect Size: {display_es:.{dp}f}")
print(f"{confidence_level:.0f}% CI: [{display_ci_lower:.{dp}f}, {display_ci_upper:.{dp}f}]")
print(f"Prediction Interval: [{pi_lower:.{dp}f}, {pi_upper:.{dp}f}]")
print(f"z = {z_score:.2f}, p = {p_value:.{dp}f}")
print(f"I-squared = {I_squared:.1f}%")
print(f"H-squared = {H_squared:.2f}")
print(f"Q = {Q:.2f}, df = {df}, p = {p_hetero:.{dp}f}")
print(f"tau-squared = {tau2:.{dp}f}")
print(f"Study Weights: {np.round(w_star, {dp})}")
print(f"Study Effects: {np.round(es, {dp})}")
''',
}

# metan 6-variable 格式: ne meane sde nc meanc sdc → 直接计算 MD 和 SE
METAN_RAW_MD_TEMPLATE = '''# -*- coding: utf-8 -*-
"""Auto-generated from Stata metan (raw data MD)"""
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 数据 ====
{data_block}

# 原始数据提取 ====
ne = np.array([{ne_values}])
meane = np.array([{meane_values}])
sde = np.array([{sde_values}])
nc = np.array([{nc_values}])
meanc = np.array([{meanc_values}])
sdc = np.array([{sdc_values}])

# 计算 MD 和 SE（从原始数据直接计算，无精度损失）====
es = meane - meanc
se = np.sqrt(sde**2 / ne + sdc**2 / nc)

# 计算权重 ====
weights = 1.0 / (se ** 2)

# 异质性统计 ====
Q = np.sum(weights * (es - np.average(es, weights=weights))**2)
df = len(es) - 1
I_squared = max(0, (Q - df) / Q * 100) if Q > 0 else 0
p_hetero = 1 - stats.chi2.cdf(Q, df) if df > 0 else 1.0

# tau² 估计量选择 ====
tau2_est = "{tau2_estimator}"
S1 = np.sum(weights)
S2 = np.sum(weights**2)
if tau2_est == "DL":
    C = S1 - S2 / S1
    tau2 = max(0.0, (Q - df) / C) if Q > df else 0.0
elif tau2_est == "Hedges":
    C = S1 - S2 / S1
    tau2 = max(0.0, (Q - df) / C)
elif tau2_est in ("REML", "ML"):
    tau2 = max(0.0, (Q - df) / (S1 - S2 / S1))
    for _ in range(50):
        w_i = 1.0 / (se**2 + tau2)
        theta = np.sum(w_i * es) / np.sum(w_i)
        if tau2_est == "REML":
            denom = np.sum(w_i**2)
            num = np.sum(w_i**2 * ((es - theta)**2 - se**2))
            new_tau2 = max(0.0, num / denom)
        else:
            denom = np.sum(w_i**2)
            num = np.sum(w_i**2 * ((es - theta)**2 - se**2)) + 0.5 * np.sum((w_i**2) * (se**2) / (se**2 + tau2))
            new_tau2 = max(0.0, num / denom)
        if abs(new_tau2 - tau2) < 1e-6:
            break
        tau2 = new_tau2
elif tau2_est == "SJ":
    theta_fe = np.sum(weights * es) / S1
    tau2 = max(0.0, np.sum((es - theta_fe)**2) / df - np.mean(se**2))
elif tau2_est == "HS":
    C = S1 - S2 / S1
    tau2 = max(0.0, (Q - df) / C) if Q > df else 0.0
elif tau2_est == "EB":
    tau2 = max(0.0, (Q - df) / (S1 - S2 / S1))
    for _ in range(50):
        w_i = 1.0 / (se**2 + tau2)
        theta = np.sum(w_i * es) / np.sum(w_i)
        num = np.sum((w_i**2) * ((es - theta)**2 - se**2))
        denom = np.sum(w_i**2)
        new_tau2 = max(0.0, tau2 * num / denom)
        if abs(new_tau2 - tau2) < 1e-6:
            break
        tau2 = new_tau2
else:
    tau2 = 0.0

# 模型拟合 ====
if "{model}" in ("FE", "CE"):
    w_star = weights
    pooled_es = np.sum(w_star * es) / np.sum(w_star)
    se_pooled = np.sqrt(1.0 / np.sum(w_star))
    tau2 = 0.0
else:
    w_star = 1.0 / (se**2 + tau2)
    pooled_es = np.sum(w_star * es) / np.sum(w_star)
    se_pooled = np.sqrt(1.0 / np.sum(w_star))

# 置信区间 ====
confidence_level = {confidence_level}
z_alpha = {z_alpha}
ci_lower = pooled_es - z_alpha * se_pooled
ci_upper = pooled_es + z_alpha * se_pooled
z_score = pooled_es / se_pooled
p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

eform = {eform}
if eform:
    display_es = np.exp(pooled_es)
    display_ci_lower = np.exp(ci_lower)
    display_ci_upper = np.exp(ci_upper)
else:
    display_es = pooled_es
    display_ci_lower = ci_lower
    display_ci_upper = ci_upper

# H² 与预测区间 ====
H_squared = Q / df if df > 0 else 1.0
if "{model}" in ("FE", "CE"):
    pi_lower, pi_upper = display_ci_lower, display_ci_upper
else:
    pi_se = np.sqrt(tau2 + se_pooled**2)
    pi_lower = pooled_es - z_alpha * pi_se
    pi_upper = pooled_es + z_alpha * pi_se
    if eform:
        pi_lower = np.exp(pi_lower)
        pi_upper = np.exp(pi_upper)

# 输出 ====
print("=== Meta Analysis Results (MD from raw data) ===")
print(f"Number of studies: {len(es)}")
print(f"Model: {model_desc}")
print(f"Effect-size label: {effect_measure}")
print(f"Method: {tau2_est if '{model}' not in ('FE', 'CE') else 'Inverse-variance'}")
print(f"tau² estimator: {tau2_est}")
print(f"Confidence level: {confidence_level}%")
print(f"Pooled Effect Size: {display_es:.{dp}f}")
print(f"{confidence_level:.0f}% CI: [{display_ci_lower:.{dp}f}, {display_ci_upper:.{dp}f}]")
print(f"Prediction Interval: [{pi_lower:.{dp}f}, {pi_upper:.{dp}f}]")
print(f"z = {z_score:.2f}, p = {p_value:.{dp}f}")
print(f"I-squared = {I_squared:.1f}%")
print(f"H-squared = {H_squared:.2f}")
print(f"Q = {Q:.2f}, df = {df}, p = {p_hetero:.{dp}f}")
print(f"tau-squared = {tau2:.{dp}f}")
print(f"Study Weights: {np.round(w_star, {dp})}")
print(f"Study Effects: {np.round(es, {dp})}")

# 森林图 ====
labels = {labels_array}
fig, ax = plt.subplots(figsize=(10, {fig_height}))
n_studies = len(es)
y_positions = list(range(n_studies))
for i in range(n_studies):
    ax.plot([es[i] - 1.96*se[i], es[i] + 1.96*se[i]], [i, i], 'k-', linewidth=1.5)
    size = max(20, 1.0 / (se[i]**2) * 5)
    ax.scatter(es[i], i, s=size, c='steelblue', edgecolors='black', linewidth=0.5, zorder=3)
y_diamond = -1
ax.plot([ci_lower, ci_upper], [y_diamond, y_diamond], 'k-', linewidth=1.5)
ax.scatter(pooled_es, y_diamond, marker='D', s=80, c='red', edgecolors='black', zorder=4)
ax.axvline(0, color='gray', linewidth=0.8, linestyle='--')
if labels:
    ax.set_yticks([-1] + y_positions)
    ax.set_yticklabels(['Summary'] + list(labels))
ax.set_xlabel("Mean Difference (MD)")
ax.set_title("Forest Plot")
ax.invert_yaxis()
plt.tight_layout()
plt.savefig("forest_plot.png", dpi=150)
print("Forest plot saved to forest_plot.png")
'''

# metan by() 分组模板: 按分组变量分别进行亚组分析
METAN_BY_TEMPLATE = '''# -*- coding: utf-8 -*-
"""Auto-generated from Stata metan (by subgroup)"""
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 数据 ====
{data_block}

# 原始数据提取 ====
ne = np.array([{ne_values}])
meane = np.array([{meane_values}])
sde = np.array([{sde_values}])
nc = np.array([{nc_values}])
meanc = np.array([{meanc_values}])
sdc = np.array([{sdc_values}])
subgroup = np.array([{subgroup_values}])
labels = np.array({labels_array})

# 计算 MD 和 SE ====
es = meane - meanc
se = np.sqrt(sde**2 / ne + sdc**2 / nc)

# 获取唯一分组 ====
unique_groups = np.unique(subgroup)

print("=" * 60)
print("=== Meta Analysis with Subgroups ===")
print("=" * 60)

# 存储各亚组结果用于森林图 ====
all_es = []
all_se = []
all_labels = []
all_ci_lower = []
all_ci_upper = []
group_pooled = []
group_ci_lower = []
group_ci_upper = []
group_names = []

# 对每个亚组分别进行 Meta 分析 ====
for grp in unique_groups:
    mask = subgroup == grp
    es_g = es[mask]
    se_g = se[mask]
    labels_g = labels[mask] if len(labels) > 0 else []
    
    print(f"\\n--- Subgroup: {grp} ---")
    
    weights_g = 1.0 / (se_g ** 2)
    Q_g = np.sum(weights_g * (es_g - np.average(es_g, weights=weights_g))**2)
    df_g = len(es_g) - 1
    I_squared_g = max(0, (Q_g - df_g) / Q_g * 100) if Q_g > 0 else 0
    H_squared_g = Q_g / df_g if df_g > 0 else 1.0
    p_hetero_g = 1 - stats.chi2.cdf(Q_g, df_g) if df_g > 0 else 1.0
    
    if "{model}" == "DL":
        C_g = np.sum(weights_g) - np.sum(weights_g**2) / np.sum(weights_g)
        tau2_g = max(0, (Q_g - df_g) / C_g) if Q_g > df_g else 0
        w_star_g = 1.0 / (se_g**2 + tau2_g)
        pooled_g = np.sum(w_star_g * es_g) / np.sum(w_star_g)
        se_pooled_g = np.sqrt(1.0 / np.sum(w_star_g))
    else:
        w_star_g = weights_g
        pooled_g = np.sum(w_star_g * es_g) / np.sum(w_star_g)
        se_pooled_g = np.sqrt(1.0 / np.sum(w_star_g))
        tau2_g = 0
    
    z_alpha_g = {z_alpha}
    ci_lower_g = pooled_g - z_alpha_g * se_pooled_g
    ci_upper_g = pooled_g + z_alpha_g * se_pooled_g
    z_g = pooled_g / se_pooled_g
    p_g = 2 * (1 - stats.norm.cdf(abs(z_g)))
    
    if {eform}:
        pooled_g_disp = np.exp(pooled_g)
        ci_lower_g_disp = np.exp(ci_lower_g)
        ci_upper_g_disp = np.exp(ci_upper_g)
    else:
        pooled_g_disp = pooled_g
        ci_lower_g_disp = ci_lower_g
        ci_upper_g_disp = ci_upper_g
    
    print(f"  Number of studies: {len(es_g)}")
    print(f"  Pooled ES: {pooled_g_disp:.{dp}f}, {confidence_level:.0f}% CI: [{ci_lower_g_disp:.{dp}f}, {ci_upper_g_disp:.{dp}f}]")
    print(f"  I-squared = {I_squared_g:.1f}%, H-squared = {H_squared_g:.2f}")
    print(f"  Q = {Q_g:.2f}, df = {df_g}, p = {p_hetero_g:.{dp}f}")
    print(f"  z = {z_g:.2f}, p = {p_g:.{dp}f}")
    
    all_es.extend(es_g.tolist())
    all_se.extend(se_g.tolist())
    all_labels.extend(labels_g.tolist() if len(labels_g) > 0 else [f"Study {{j+1}} ({grp})" for j in range(len(es_g))])
    all_ci_lower.extend((es_g - z_alpha_g*se_g).tolist())
    all_ci_upper.extend((es_g + z_alpha_g*se_g).tolist())
    group_pooled.append(pooled_g)
    group_ci_lower.append(ci_lower_g)
    group_ci_upper.append(ci_upper_g)
    group_names.append(str(grp))

# 整体汇总 ====
weights_all = 1.0 / (se ** 2)
Q_all = np.sum(weights_all * (es - np.average(es, weights=weights_all))**2)
df_all = len(es) - 1
I_squared_all = max(0, (Q_all - df_all) / Q_all * 100) if Q_all > 0 else 0
p_hetero_all = 1 - stats.chi2.cdf(Q_all, df_all) if df_all > 0 else 1.0

if "{model}" == "DL":
    C_all = np.sum(weights_all) - np.sum(weights_all**2) / np.sum(weights_all)
    tau2_all = max(0, (Q_all - df_all) / C_all) if Q_all > df_all else 0
    w_star_all = 1.0 / (se**2 + tau2_all)
    pooled_all = np.sum(w_star_all * es) / np.sum(w_star_all)
    se_pooled_all = np.sqrt(1.0 / np.sum(w_star_all))
else:
    w_star_all = weights_all
    pooled_all = np.sum(w_star_all * es) / np.sum(w_star_all)
    se_pooled_all = np.sqrt(1.0 / np.sum(w_star_all))
    tau2_all = 0

z_alpha_all = {z_alpha}
ci_lower_all = pooled_all - z_alpha_all * se_pooled_all
ci_upper_all = pooled_all + z_alpha_all * se_pooled_all
z_all = pooled_all / se_pooled_all
p_all = 2 * (1 - stats.norm.cdf(abs(z_all)))

if {eform}:
    pooled_all_disp = np.exp(pooled_all)
    ci_lower_all_disp = np.exp(ci_lower_all)
    ci_upper_all_disp = np.exp(ci_upper_all)
else:
    pooled_all_disp = pooled_all
    ci_lower_all_disp = ci_lower_all
    ci_upper_all_disp = ci_upper_all

H_squared_all = Q_all / df_all if df_all > 0 else 1.0

print(f"\n=== Overall (All Studies) ===")
print(f"Number of studies: {len(es)}")
print(f"Pooled Effect Size: {pooled_all_disp:.{dp}f}")
print(f"{confidence_level:.0f}% CI: [{ci_lower_all_disp:.{dp}f}, {ci_upper_all_disp:.{dp}f}]")
print(f"z = {z_all:.2f}, p = {p_all:.{dp}f}")
print(f"I-squared = {I_squared_all:.1f}%, H-squared = {H_squared_all:.2f}")
print(f"Q = {Q_all:.2f}, df = {df_all}, p = {p_hetero_all:.{dp}f}")
print(f"tau-squared = {tau2_all:.{dp}f}")

# 亚组间差异（简化计算：基于固定效应加权）
if len(unique_groups) > 1:
    theta_fe = np.sum(weights_all * es) / np.sum(weights_all)
    Q_between = np.sum([np.sum(weights_all[subgroup == g]) * (np.average(es[subgroup == g], weights=weights_all[subgroup == g]) - theta_fe)**2 for g in unique_groups])
    df_between = len(unique_groups) - 1
    p_between = 1 - stats.chi2.cdf(Q_between, df_between) if df_between > 0 else 1.0
    print(f"Test of group differences: Q_b = chi2({df_between}) = {Q_between:.2f} Prob > Q_b = {p_between:.{dp}f}")

# 森林图（含分组）====
all_es_arr = np.array(all_es)
all_se_arr = np.array(all_se)
all_ci_lower_arr = np.array(all_ci_lower)
all_ci_upper_arr = np.array(all_ci_upper)

fig, ax = plt.subplots(figsize=(10, {fig_height}))
n_total = len(all_es_arr)
y_positions = list(range(n_total))

for i in range(n_total):
    ax.plot([all_ci_lower_arr[i], all_ci_upper_arr[i]], [i, i], 'k-', linewidth=1.5)
    size = max(20, 1.0 / (all_se_arr[i]**2) * 5)
    ax.scatter(all_es_arr[i], i, s=size, c='steelblue', edgecolors='black', linewidth=0.5, zorder=3)

# 各亚组菱形
n_groups = len(group_pooled)
y_start = n_total
for g_idx in range(n_groups):
    y_g = y_start + g_idx
    ax.plot([group_ci_lower[g_idx], group_ci_upper[g_idx]], [y_g, y_g], 'k-', linewidth=1.5)
    ax.scatter(group_pooled[g_idx], y_g, marker='D', s=80, c='green', edgecolors='black', zorder=4)

# 整体汇总菱形
y_overall = y_start + n_groups
ax.plot([ci_lower_all, ci_upper_all], [y_overall, y_overall], 'k-', linewidth=2)
ax.scatter(pooled_all, y_overall, marker='D', s=100, c='red', edgecolors='black', zorder=4)

ax.axvline(0, color='gray', linewidth=0.8, linestyle='--')

all_tick_positions = y_positions + list(range(y_start, y_overall + 1))
all_tick_labels = list(all_labels) + [f"Subgroup: {{g}}" for g in group_names] + ['Overall']
ax.set_yticks(all_tick_positions)
ax.set_yticklabels(all_tick_labels)
ax.set_xlabel("Mean Difference (MD)")
ax.set_title("Forest Plot by Subgroup")
ax.invert_yaxis()
plt.tight_layout()
plt.savefig("forest_plot.png", dpi=150)
print("\\nForest plot saved to forest_plot.png")
'''