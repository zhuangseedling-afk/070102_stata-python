"""比对器 — 比较 Stata 模拟输出 vs Python 实测输出"""
from __future__ import annotations
from dataclasses import dataclass, field
from .metrics import MetaMetrics, extract_metrics_from_output
from ..config import DIFF_THRESHOLD


@dataclass
class ComparisonReport:
    """比对报告"""
    stata_metrics: MetaMetrics = field(default_factory=MetaMetrics)
    python_metrics: MetaMetrics = field(default_factory=MetaMetrics)
    differences: dict[str, float] = field(default_factory=dict)
    is_consistent: bool = False
    threshold: float = DIFF_THRESHOLD
    detail: str = ""


def compare_outputs(stata_output: str, python_output: str) -> ComparisonReport:
    """
    比对 Stata 模拟输出 与 Python 实测输出
    """
    stata_metrics = extract_metrics_from_output(stata_output)
    python_metrics = extract_metrics_from_output(python_output)

    return compare_metrics(stata_metrics, python_metrics)


def _relative_diff(sv: float, pv: float) -> float:
    """计算相对差异，处理接近零的情况"""
    if sv == 0 and pv == 0:
        return 0.0
    elif abs(sv) < 1e-10:
        return 1.0 if abs(pv) > 1e-10 else 0.0
    else:
        return abs(sv - pv) / max(abs(sv), 1e-10)


def _string_diff(sv: str, pv: str) -> float:
    """字符串字段差异：完全一致为 0，否则为 1"""
    return 0.0 if str(sv).strip().lower() == str(pv).strip().lower() else 1.0


def compare_metrics(stata_metrics: MetaMetrics, python_metrics: MetaMetrics) -> ComparisonReport:
    """直接比对两个 MetaMetrics 对象"""
    differences = {}
    is_consistent = True

    # 模型与样本信息（含字符串字段）
    sv_n = getattr(stata_metrics, "number_of_studies", 0) or 0
    pv_n = getattr(python_metrics, "number_of_studies", 0) or 0
    diff = _relative_diff(float(sv_n), float(pv_n))
    differences["Number of studies"] = round(diff, 6)
    if diff > DIFF_THRESHOLD:
        is_consistent = False

    for attr, label in [
        ("model", "Model"),
        ("model_method", "Method"),
        ("effect_measure", "Effect measure"),
    ]:
        diff = _string_diff(getattr(stata_metrics, attr, ""), getattr(python_metrics, attr, ""))
        differences[label] = round(diff, 6)
        if diff > DIFF_THRESHOLD:
            is_consistent = False

    # 核心合并效应指标
    key_metrics = [
        ("pooled_effect", "Pooled Effect Size"),
        ("ci_lower", "CI Lower"),
        ("ci_upper", "CI Upper"),
        ("p_value", "p-value (overall)"),
        ("z_score", "z-score"),
    ]

    for attr, label in key_metrics:
        sv = getattr(stata_metrics, attr, 0) or 0
        pv = getattr(python_metrics, attr, 0) or 0
        diff = _relative_diff(sv, pv)
        differences[label] = round(diff, 6)
        if diff > DIFF_THRESHOLD:
            is_consistent = False

    # 异质性指标
    hetero_metrics = [
        ("i_squared", "I² (%)"),
        ("h_squared", "H²"),
        ("q_statistic", "Q Statistic"),
        ("q_p_value", "p-value for Q"),
        ("tau_squared", "τ²"),
    ]

    for attr, label in hetero_metrics:
        sv = getattr(stata_metrics, attr, 0) or 0
        pv = getattr(python_metrics, attr, 0) or 0
        diff = _relative_diff(sv, pv)
        differences[label] = round(diff, 6)
        if diff > DIFF_THRESHOLD:
            is_consistent = False

    # 预测区间
    pi_metrics = [
        ("prediction_interval_lower", "Prediction Interval Lower"),
        ("prediction_interval_upper", "Prediction Interval Upper"),
    ]
    for attr, label in pi_metrics:
        sv = getattr(stata_metrics, attr, 0) or 0
        pv = getattr(python_metrics, attr, 0) or 0
        diff = _relative_diff(sv, pv)
        differences[label] = round(diff, 6)
        if diff > DIFF_THRESHOLD:
            is_consistent = False

    # 发表偏倚 Egger
    egger_metrics = [
        ("egger_t", "Egger's t"),
        ("egger_p", "Egger's p"),
    ]
    for attr, label in egger_metrics:
        sv = getattr(stata_metrics, attr, 0) or 0
        pv = getattr(python_metrics, attr, 0) or 0
        diff = _relative_diff(sv, pv)
        differences[label] = round(diff, 6)
        if diff > DIFF_THRESHOLD:
            is_consistent = False

    # Meta 回归系数
    s_coefs = {c["name"]: c for c in stata_metrics.metareg_coefficients}
    p_coefs = {c["name"]: c for c in python_metrics.metareg_coefficients}
    for name in set(s_coefs.keys()) | set(p_coefs.keys()):
        s_c = s_coefs.get(name, {})
        p_c = p_coefs.get(name, {})
        for field_name, field_label in [("coef", "Coef"), ("se", "SE"), ("z", "z"), ("p", "p")]:
            sv = s_c.get(field_name, 0) or 0
            pv = p_c.get(field_name, 0) or 0
            label = f"Metareg {name} {field_label}"
            diff = _relative_diff(sv, pv)
            differences[label] = round(diff, 6)
            if diff > DIFF_THRESHOLD:
                is_consistent = False

    # Meta 回归 R² / Wald
    metareg_metrics = [
        ("metareg_r_squared", "Meta-regression R² (%)"),
        ("metareg_wald_chi2", "Meta-regression Wald χ²"),
        ("metareg_wald_p", "Meta-regression Wald p"),
        ("residual_q", "Residual Q"),
        ("residual_q_p_value", "Residual Q p-value"),
    ]
    for attr, label in metareg_metrics:
        sv = getattr(stata_metrics, attr, 0) or 0
        pv = getattr(python_metrics, attr, 0) or 0
        diff = _relative_diff(sv, pv)
        differences[label] = round(diff, 6)
        if diff > DIFF_THRESHOLD:
            is_consistent = False

    # 亚组结果
    s_sg = stata_metrics.subgroup_results
    p_sg = python_metrics.subgroup_results
    if s_sg or p_sg:
        max_sg = max(len(s_sg), len(p_sg))
        for i in range(max_sg):
            s_name = s_sg[i]["name"] if i < len(s_sg) else f"missing_{i}"
            p_name = p_sg[i]["name"] if i < len(p_sg) else f"missing_{i}"
            sg_label = f"Subgroup {s_name} ES"
            sv = s_sg[i]["pooled_effect"] if i < len(s_sg) else 0
            pv = p_sg[i]["pooled_effect"] if i < len(p_sg) else 0
            diff = _relative_diff(sv, pv)
            differences[sg_label] = round(diff, 6)
            if diff > DIFF_THRESHOLD:
                is_consistent = False

    # 亚组间差异
    if stata_metrics.subgroup_between_q or python_metrics.subgroup_between_q:
        diff = _relative_diff(stata_metrics.subgroup_between_q, python_metrics.subgroup_between_q)
        differences["Subgroup between-Q"] = round(diff, 6)
        if diff > DIFF_THRESHOLD:
            is_consistent = False
    if stata_metrics.subgroup_between_p or python_metrics.subgroup_between_p:
        diff = _relative_diff(stata_metrics.subgroup_between_p, python_metrics.subgroup_between_p)
        differences["Subgroup between-p"] = round(diff, 6)
        if diff > DIFF_THRESHOLD:
            is_consistent = False

    # 发表偏倚扩展
    bias_metrics = [
        ("begg_z", "Begg's z"),
        ("begg_p", "Begg's p"),
        ("harbord_beta1", "Harbord beta1"),
        ("harbord_se", "Harbord SE"),
        ("harbord_z", "Harbord z"),
        ("harbord_p", "Harbord p"),
    ]
    for attr, label in bias_metrics:
        sv = getattr(stata_metrics, attr, 0) or 0
        pv = getattr(python_metrics, attr, 0) or 0
        diff = _relative_diff(sv, pv)
        differences[label] = round(diff, 6)
        if diff > DIFF_THRESHOLD:
            is_consistent = False

    # Trim-and-fill
    trimfill_metrics = [
        ("trimfill_missing_studies", "Trim-and-fill missing studies"),
        ("trimfill_adjusted_effect", "Trim-and-fill adjusted effect"),
        ("trimfill_adjusted_ci_lower", "Trim-and-fill adjusted CI lower"),
        ("trimfill_adjusted_ci_upper", "Trim-and-fill adjusted CI upper"),
    ]
    for attr, label in trimfill_metrics:
        sv = getattr(stata_metrics, attr, 0) or 0
        pv = getattr(python_metrics, attr, 0) or 0
        diff = _relative_diff(float(sv), float(pv))
        differences[label] = round(diff, 6)
        if diff > DIFF_THRESHOLD:
            is_consistent = False

    # 生成细节描述
    detail_parts = []
    for label, diff in differences.items():
        status = "✓" if diff <= DIFF_THRESHOLD else "✗"
        detail_parts.append(f"  {status} {label}: {diff:.4%}")

    report = ComparisonReport(
        stata_metrics=stata_metrics,
        python_metrics=python_metrics,
        differences=differences,
        is_consistent=is_consistent,
        detail="\n".join(detail_parts),
    )

    return report


def get_consistency_score(report: ComparisonReport) -> float:
    """计算一致性评分 0-100"""
    if not report.differences:
        return 100.0
    avg_diff = sum(report.differences.values()) / len(report.differences)
    return max(0, 100 * (1 - avg_diff))
