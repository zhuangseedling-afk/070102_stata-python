"""
metareg 命令 — Meta 回归
Stata: metareg es se, wsse(se) [covariates]
"""
METAREG_RULES = {
    "command": "metareg",
    "python_package": "statsmodels",
    "option_map": {
        "wsse": "se_var",
        "mm": "method_moments",
        "reml": "REML",
        "ml": "ML",
        "eb": "empirical_bayes",
    },
    "code_template": '''# -*- coding: utf-8 -*-
"""Auto-generated from Stata metareg — meta-regression"""
import numpy as np
import statsmodels.api as sm
from scipy import stats

# 数据 ====
{data_block}

es = np.array([{es_values}])
se = np.array([{se_values}])
X = np.column_stack([np.ones(len(es)), {covariate_arrays}])  # 截距 + 协变量
covariate_names = ["_cons"] + {covariate_names}

# 加权最小二乘（WLS）用逆方差为权重 ====
wls_model = sm.WLS(es, X, weights=1.0/(se**2))
results = wls_model.fit()

# 估计 tau²（矩估计/REML 简化）====
def estimate_tau2(residuals, se, X):
    Q = np.sum((residuals / se) ** 2)
    df_resid = len(es) - X.shape[1]
    if df_resid <= 0:
        return 0.0, Q, df_resid
    S1 = np.sum(1.0 / se**2)
    XtWX = X.T @ np.diag(1.0 / se**2) @ X
    denom = S1 - np.trace(XtWX) / S1
    tau2 = max(0, (Q - df_resid) / denom) if denom > 0 else 0.0
    return tau2, Q, df_resid

tau2, Q_res, df_res = estimate_tau2(results.resid, se, X)

# 调整权重（加 tau²）并重新拟合 ====
w_adj = 1.0 / (se**2 + tau2)
wls_model_adj = sm.WLS(es, X, weights=w_adj)
results_adj = wls_model_adj.fit()

# 计算总 tau²（仅截距模型）用于 R² ====
X_intercept = np.ones((len(es), 1))
wls_int = sm.WLS(es, X_intercept, weights=1.0/(se**2))
res_int = wls_int.fit()
tau2_total, _, _ = estimate_tau2(res_int.resid, se, X_intercept)
r_squared = 100 * (1 - tau2 / tau2_total) if tau2_total > 0 else 0.0

# Wald 检验 ====
# 排除截距后的联合显著性
if X.shape[1] > 1:
    R = np.eye(X.shape[1] - 1, X.shape[1])
    R[:, 1:] = np.eye(X.shape[1] - 1)
    wald = results_adj.wald_test(R, use_f=False)
    wald_chi2 = float(wald.statistic)
    wald_p = float(wald.pvalue)
else:
    wald_chi2 = 0.0
    wald_p = 1.0

# 输出 ====
print("=== Meta-Regression Results ===")
print(f"Number of obs: {len(es)}")
print(f"tau² (residual): {tau2:.{dp}f}")
print(f"I² (residual): {max(0, (Q_res - df_res) / Q_res * 100) if Q_res > 0 else 0:.1f}%")
print(f"R-squared (%): {r_squared:.{dp}f}")
print(f"Wald chi2({X.shape[1]-1}) = {wald_chi2:.2f}")
print(f"Prob > chi2 = {wald_p:.{dp}f}")
print("Coef. Std. Err. z P>|z| [95% Conf. Interval]")
for i, name in enumerate(covariate_names):
    coef = results_adj.params[i]
    se_coef = results_adj.bse[i]
    z = coef / se_coef
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    ci_l = coef - 1.96 * se_coef
    ci_u = coef + 1.96 * se_coef
    print(f"{name} {coef:.{dp}f} {se_coef:.{dp}f} {z:.2f} {p:.{dp}f} [{ci_l:.{dp}f}, {ci_u:.{dp}f}]")

print(f"\\nTest of residual homogeneity: Q_res = chi2({df_res}) = {Q_res:.2f} Prob > Q_res = {1 - stats.chi2.cdf(Q_res, df_res) if df_res > 0 else 1.0:.{dp}f}")
''',
}
