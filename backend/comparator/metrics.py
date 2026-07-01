"""Meta 分析指标提取器"""
from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class MetaMetrics:
    """一次 Meta 分析的核心指标"""
    # 基本/模型信息
    number_of_studies: int = 0
    model: str = "DL"
    model_method: str = ""
    effect_measure: str = ""

    # 合并效应
    pooled_effect: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    p_value: float = 0.0
    z_score: float = 0.0

    # 异质性
    i_squared: float = 0.0
    h_squared: float = 0.0
    q_statistic: float = 0.0
    q_df: int = 0
    q_p_value: float = 0.0
    tau_squared: float = 0.0

    # 预测区间（随机效应模型）
    prediction_interval_lower: float = 0.0
    prediction_interval_upper: float = 0.0

    # 研究级信息
    study_weights: list[float] = field(default_factory=list)
    study_effects: list[float] = field(default_factory=list)

    # 发表偏倚 / 漏斗图
    egger_intercept: float = 0.0
    egger_se: float = 0.0
    egger_t: float = 0.0
    egger_p: float = 0.0

    # Meta 回归
    covariates: str = ""
    metareg_coefficients: list[dict] = field(default_factory=list)
    metareg_r_squared: float = 0.0
    metareg_wald_chi2: float = 0.0
    metareg_wald_p: float = 0.0
    residual_q: float = 0.0
    residual_q_p_value: float = 0.0

    # 亚组分析
    subgroup_results: list[dict] = field(default_factory=list)
    subgroup_between_q: float = 0.0
    subgroup_between_p: float = 0.0

    # 发表偏倚扩展（Stata meta bias / metabias）
    begg_z: float = 0.0
    begg_p: float = 0.0
    harbord_beta1: float = 0.0
    harbord_se: float = 0.0
    harbord_z: float = 0.0
    harbord_p: float = 0.0

    # Trim-and-fill 填补后结果
    trimfill_missing_studies: int = 0
    trimfill_adjusted_effect: float = 0.0
    trimfill_adjusted_ci_lower: float = 0.0
    trimfill_adjusted_ci_upper: float = 0.0

    # 敏感性分析 / 累积 Meta
    leave_one_out_results: list[dict] = field(default_factory=list)
    cumulative_results: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "number_of_studies": self.number_of_studies,
            "model": self.model,
            "model_method": self.model_method,
            "effect_measure": self.effect_measure,
            "pooled_effect": self.pooled_effect,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "p_value": self.p_value,
            "z_score": self.z_score,
            "i_squared": self.i_squared,
            "h_squared": self.h_squared,
            "q_statistic": self.q_statistic,
            "q_df": self.q_df,
            "q_p_value": self.q_p_value,
            "tau_squared": self.tau_squared,
            "prediction_interval_lower": self.prediction_interval_lower,
            "prediction_interval_upper": self.prediction_interval_upper,
            "study_weights": self.study_weights,
            "study_effects": self.study_effects,
            "egger_intercept": self.egger_intercept,
            "egger_se": self.egger_se,
            "egger_t": self.egger_t,
            "egger_p": self.egger_p,
            "metareg_coefficients": self.metareg_coefficients,
            "metareg_r_squared": self.metareg_r_squared,
            "metareg_wald_chi2": self.metareg_wald_chi2,
            "metareg_wald_p": self.metareg_wald_p,
            "residual_q": self.residual_q,
            "residual_q_p_value": self.residual_q_p_value,
            "subgroup_results": self.subgroup_results,
            "subgroup_between_q": self.subgroup_between_q,
            "subgroup_between_p": self.subgroup_between_p,
            "begg_z": self.begg_z,
            "begg_p": self.begg_p,
            "harbord_beta1": self.harbord_beta1,
            "harbord_se": self.harbord_se,
            "harbord_z": self.harbord_z,
            "harbord_p": self.harbord_p,
            "trimfill_missing_studies": self.trimfill_missing_studies,
            "trimfill_adjusted_effect": self.trimfill_adjusted_effect,
            "trimfill_adjusted_ci_lower": self.trimfill_adjusted_ci_lower,
            "trimfill_adjusted_ci_upper": self.trimfill_adjusted_ci_upper,
            "leave_one_out_results": self.leave_one_out_results,
            "cumulative_results": self.cumulative_results,
        }


def _to_float(value: str | float | None, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _to_int(value: str | int | None, default: int = 0) -> int:
    """安全转换为整数"""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def extract_metrics_from_output(stdout: str) -> MetaMetrics:
    """从 Python 执行输出中提取 Meta 分析指标"""
    metrics = MetaMetrics()
    text = stdout or ""

    # Number of studies
    m = re.search(r'Number\s+of\s+(?:studies|obs)\s*[:=]\s*(\d+)', text, re.IGNORECASE)
    if not m:
        # 从 Study Weights / Study Effects 列表长度推断
        wm = re.search(r'Study\s+Weights\s*[:=]\s*\[([^\]]+)\]', text)
        if wm:
            try:
                metrics.number_of_studies = len([x for x in wm.group(1).split() if x.strip()])
            except ValueError:
                pass
    if m:
        metrics.number_of_studies = _to_int(m.group(1))

    # Model / Method
    m = re.search(r'Model:\s*(.+?)(?:\n|$)', text)
    if m:
        model_line = m.group(1).strip()
        metrics.model = model_line
        # 尝试提取 Method，例如 "Random-effects REML" 或 "Fixed-effects"
        method_m = re.search(r'(?:Method|model):\s*([A-Za-z\-]+)', text, re.IGNORECASE)
        if method_m:
            metrics.model_method = method_m.group(1).strip()
        # 标准化 model 字段
        if "Fixed" in model_line or model_line == "FE":
            metrics.model = "FE"
        elif "REML" in model_line:
            metrics.model = "REML"
        elif "ML" in model_line:
            metrics.model = "ML"
        elif "Common" in model_line or model_line == "CE":
            metrics.model = "CE"
        elif "Random" in model_line or "DL" in model_line:
            metrics.model = "DL"

    # Effect measure
    m = re.search(r'Effect-size label:\s*(.+?)(?:\n|$)', text)
    if m:
        metrics.effect_measure = m.group(1).strip()

    # Pooled Effect Size — 优先匹配 Overall 部分
    m = re.search(r'Overall.*?Pooled\s+(?:Effect\s+Size|ES|Proportion)\s*[:=]\s*([\-\d.eE]+)', text, re.DOTALL | re.IGNORECASE)
    if not m:
        m = re.search(r'Pooled\s+(?:Effect\s+Size|Proportion|ES)\s*[:=]\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics.pooled_effect = _to_float(m.group(1))

    # 95% CI — 优先匹配 Overall 部分
    m = re.search(r'Overall.*?([\d.]+)%\s*CI\s*[:=]\s*\[([\-\d.eE]+),\s*([\-\d.eE]+)\]', text, re.DOTALL | re.IGNORECASE)
    if not m:
        m = re.search(r'([\d.]+)%\s*CI\s*[:=]\s*\[([\-\d.eE]+),\s*([\-\d.eE]+)\]', text, re.IGNORECASE)
    if m:
        metrics.ci_lower = _to_float(m.group(2))
        metrics.ci_upper = _to_float(m.group(3))

    # z-score
    m = re.search(r'z\s*[:=]\s*([\-\d.eE]+)', text)
    if m:
        metrics.z_score = _to_float(m.group(1))

    # p-value — 优先匹配整体效应的 p（避免误吸 Q 同行的 p）
    # 先匹配 "z = ..., p = ..." 或单独一行 "p = ..." 作为整体效应 p
    m = re.search(r'z\s*[:=]\s*[\-\d.eE]+\s*,?\s*p\s*[:=]\s*([\-\d.eE]+)', text)
    if not m:
        m = re.search(r'Pooled.*?p\s*[:=]\s*([\-\d.eE]+)', text, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.search(r'p\s*[:=]\s*([\-\d.eE]+)', text)
    if m:
        metrics.p_value = _to_float(m.group(1))

    # I-squared
    m = re.search(r'I[- ]?squared\s*[:=]\s*([\d.eE]+)\s*%?', text, re.IGNORECASE)
    if m:
        metrics.i_squared = _to_float(m.group(1))

    # H-squared
    m = re.search(r'H[- ]?2\s*[:=]\s*([\d.eE]+)', text, re.IGNORECASE)
    if not m:
        m = re.search(r'H[- ]?squared\s*[:=]\s*([\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics.h_squared = _to_float(m.group(1))

    # Q statistic + df + p
    m = re.search(r'Q\s*[:=]?\s*chi2?\s*\((\d+)\)\s*[:=]?\s*([\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics.q_df = _to_int(m.group(1))
        metrics.q_statistic = _to_float(m.group(2))
        # 同行的 p
        pm = re.search(r'Q\s*[:=]?\s*chi2?\s*\(\d+\)\s*[:=]?\s*[\d.eE]+[^\n]*?p\s*[:=]\s*([\-\d.eE]+)', text, re.IGNORECASE)
        if pm:
            metrics.q_p_value = _to_float(pm.group(1))
    else:
        m = re.search(r'Q\s*[:=]\s*([\d.eE]+)', text)
        if m:
            metrics.q_statistic = _to_float(m.group(1))
        m = re.search(r'df\s*[:=]\s*(\d+)', text)
        if m:
            metrics.q_df = _to_int(m.group(1))

    # p for Q (homogeneity)
    # 优先匹配 "Q = ... df = ... p = ..." 同行格式
    pm = re.search(r'Q\s*[:=]\s*[\d.eE]+\s*,?\s*df\s*[:=]\s*\d+\s*,?\s*p\s*[:=]\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if not pm:
        pm = re.search(r'Q\s*[:=]?\s*chi2?\s*\(\d+\)\s*[:=]?\s*[\d.eE]+[^\n]*?p\s*[:=]\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if not pm:
        pm = re.search(r'(?:p hetero|Prob > Q|p\s*for\s+Q|homogeneity).*?p\s*[:=]\s*([\-\d.eE]+)', text, re.IGNORECASE | re.DOTALL)
    if pm:
        metrics.q_p_value = _to_float(pm.group(1))

    # tau-squared
    m = re.search(r'tau[- ]?squared\s*[:=]\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics.tau_squared = _to_float(m.group(1))

    # Prediction Interval
    m = re.search(r'Prediction\s+Interval\s*[:=]\s*\[([\-\d.eE]+),\s*([\-\d.eE]+)\]', text, re.IGNORECASE)
    if m:
        metrics.prediction_interval_lower = _to_float(m.group(1))
        metrics.prediction_interval_upper = _to_float(m.group(2))

    # Study Weights
    wm = re.search(r'Study\s+Weights\s*[:=]\s*\[([^\]]+)\]', text)
    if wm:
        try:
            metrics.study_weights = [_to_float(x) for x in wm.group(1).split() if x.strip()]
        except ValueError:
            pass

    # Study Effects
    em = re.search(r'Study\s+Effects\s*[:=]\s*\[([^\]]+)\]', text)
    if em:
        try:
            metrics.study_effects = [_to_float(x) for x in em.group(1).split() if x.strip()]
        except ValueError:
            pass

    # Egger's test
    m = re.search(r"Egger.*?intercept\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.egger_intercept = _to_float(m.group(1))
    m = re.search(r"Egger.*?SE\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.egger_se = _to_float(m.group(1))
    m = re.search(r"Egger.*?t\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.egger_t = _to_float(m.group(1))
    m = re.search(r"Egger.*?p\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.egger_p = _to_float(m.group(1))

    # Meta-regression coefficients: Coef. Std. Err. z P>|z| [95% Conf. Interval]
    # 匹配 "name  Coef  SE  z  p  CI_lower  CI_upper" 行
    metareg_pattern = re.compile(
        r'^\s*([\w_\.]+)\s+([\-\d.eE]+)\s+([\-\d.eE]+)\s+([\-\d.eE]+)\s+([\-\d.eE]+)\s+\[?([\-\d.eE]+)\s*,\s*([\-\d.eE]+)\]?',
        re.MULTILINE,
    )
    for m in metareg_pattern.finditer(text):
        metrics.metareg_coefficients.append({
            "name": m.group(1).strip(),
            "coef": _to_float(m.group(2)),
            "se": _to_float(m.group(3)),
            "z": _to_float(m.group(4)),
            "p": _to_float(m.group(5)),
            "ci_lower": _to_float(m.group(6)),
            "ci_upper": _to_float(m.group(7)),
        })

    # Meta-regression R-squared
    m = re.search(r'R[- ]?squared\s*\(%\)\s*[:=]\s*([\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics.metareg_r_squared = _to_float(m.group(1))

    # Meta-regression Wald chi2 / p
    m = re.search(r'Wald\s+chi2\((\d+)\)\s*[:=]\s*([\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics.metareg_wald_chi2 = _to_float(m.group(2))
    m = re.search(r'Prob\s*>\s*chi2\s*[:=]\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics.metareg_wald_p = _to_float(m.group(1))

    # Residual Q
    m = re.search(r'Q_res\s*[:=]?\s*chi2?\s*\((\d+)\)\s*[:=]?\s*([\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics.residual_q = _to_float(m.group(2))
    m = re.search(r'residual\s+homogeneity.*?p\s*[:=]\s*([\-\d.eE]+)', text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.residual_q_p_value = _to_float(m.group(1))

    # 亚组结果提取
    subgroup_pattern = r'--- Subgroup:\s*(.+?)\s*---\s*' \
                       r'.*?Pooled ES:\s*([\-\d.eE]+).*?' \
                       r'([\d.]+)%\s*CI:\s*\[([\-\d.eE]+),\s*([\-\d.eE]+)\]' \
                       r'.*?I[- ]?squared\s*[:=]\s*([\d.eE]+)%' \
                       r'.*?Q\s*[:=]\s*([\d.eE]+).*?p\s*[:=]\s*([\-\d.eE]+)'
    for m in re.finditer(subgroup_pattern, text, re.DOTALL | re.IGNORECASE):
        metrics.subgroup_results.append({
            "name": m.group(1).strip(),
            "pooled_effect": _to_float(m.group(2)),
            "ci_lower": _to_float(m.group(4)),
            "ci_upper": _to_float(m.group(5)),
            "i_squared": _to_float(m.group(6)),
            "q_statistic": _to_float(m.group(7)),
            "q_p_value": _to_float(m.group(8)),
        })

    # 亚组间差异 Q_b
    m = re.search(r'Q_b\s*[:=]?\s*chi2?\s*\((\d+)\)\s*[:=]?\s*([\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics.subgroup_between_q = _to_float(m.group(2))
        pm = re.search(r'Q_b\s*[:=]?\s*chi2?\s*\(\d+\)\s*[:=]?\s*[\d.eE]+[^\n]*?p\s*[:=]\s*([\-\d.eE]+)', text, re.IGNORECASE)
        if pm:
            metrics.subgroup_between_p = _to_float(pm.group(1))

    # Begg's test
    m = re.search(r"Begg.*?z\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.begg_z = _to_float(m.group(1))
    m = re.search(r"Begg.*?p\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.begg_p = _to_float(m.group(1))

    # Harbord regression-based test
    m = re.search(r"Harbord.*?beta1\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.harbord_beta1 = _to_float(m.group(1))
    m = re.search(r"Harbord.*?SE\s+of\s+beta1\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.search(r"Harbord.*?SE\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.harbord_se = _to_float(m.group(1))
    m = re.search(r"Harbord.*?z\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.harbord_z = _to_float(m.group(1))
    m = re.search(r"Harbord.*?p\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.harbord_p = _to_float(m.group(1))

    # Trim-and-fill
    m = re.search(r"Trim[- ]?and[- ]?fill.*?missing\s+studies\s*[:=]\s*(\d+)", text, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.search(r"Missing\s+studies\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        metrics.trimfill_missing_studies = _to_int(m.group(1))
    m = re.search(r"Trim[- ]?and[- ]?fill.*?adjusted\s+effect\s*[:=]\s*([\-\d.eE]+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.trimfill_adjusted_effect = _to_float(m.group(1))
    m = re.search(r"Trim[- ]?and[- ]?fill.*?adjusted\s+.*?(?:CI|interval)\s*[:=]?\s*\[([\-\d.eE]+)\s*,\s*([\-\d.eE]+)\]", text, re.IGNORECASE | re.DOTALL)
    if m:
        metrics.trimfill_adjusted_ci_lower = _to_float(m.group(1))
        metrics.trimfill_adjusted_ci_upper = _to_float(m.group(2))

    # 敏感性分析：leave-one-out
    loo_pattern = re.compile(
        r'Omitted:\s*(.+?)\s*Pooled\s+ES\s*[:=]\s*([\-\d.eE]+)\s*(?:CI|ci)\s*[:=]?\s*\[([\-\d.eE]+)\s*,\s*([\-\d.eE]+)\]',
        re.IGNORECASE | re.DOTALL,
    )
    for m in loo_pattern.finditer(text):
        metrics.leave_one_out_results.append({
            "omitted": m.group(1).strip(),
            "pooled_effect": _to_float(m.group(2)),
            "ci_lower": _to_float(m.group(3)),
            "ci_upper": _to_float(m.group(4)),
        })

    # 累积 Meta
    cum_pattern = re.compile(
        r'Cumulative\s+.*?(\d+)\s+studies.*?Pooled\s+ES\s*[:=]\s*([\-\d.eE]+)\s*(?:CI|ci)\s*[:=]?\s*\[([\-\d.eE]+)\s*,\s*([\-\d.eE]+)\]',
        re.IGNORECASE | re.DOTALL,
    )
    for m in cum_pattern.finditer(text):
        metrics.cumulative_results.append({
            "studies": _to_int(m.group(1)),
            "pooled_effect": _to_float(m.group(2)),
            "ci_lower": _to_float(m.group(3)),
            "ci_upper": _to_float(m.group(4)),
        })

    return metrics
