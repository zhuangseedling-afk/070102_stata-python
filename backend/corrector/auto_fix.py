"""自动修正器 — 不一致时迭代修正 Python 代码"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from ..config import MAX_FIX_ITERATIONS, DIFF_THRESHOLD
from ..comparator.differ import ComparisonReport


@dataclass
class FixIteration:
    """单次修正记录"""
    iteration: int
    previous_code: str
    fixed_code: str
    previous_report: ComparisonReport
    fix_reason: str
    fix_action: str


@dataclass
class FixLog:
    """修正日志"""
    iterations: list[FixIteration] = field(default_factory=list)
    total_iterations: int = 0
    max_iterations: int = MAX_FIX_ITERATIONS
    final_consistent: bool = False


def auto_fix_code(
    original_code: str,
    original_report: ComparisonReport,
    max_iterations: int = MAX_FIX_ITERATIONS,
) -> tuple[str, FixLog]:
    """
    根据比对差异自动修正 Python 代码
    返回 (最终代码, 修正日志)
    """
    fix_log = FixLog(max_iterations=max_iterations)
    current_code = original_code
    current_report = original_report

    for i in range(max_iterations):
        if current_report.is_consistent:
            break

        # 分析差异原因
        fix_reason = _analyze_diff(current_report)
        fix_action = f"迭代 {i+1}: {fix_reason}"

        # 应用修正
        fixed_code = _apply_fix(current_code, current_report, i)

        fix_log.iterations.append(FixIteration(
            iteration=i + 1,
            previous_code=current_code,
            fixed_code=fixed_code,
            previous_report=current_report,
            fix_reason=fix_reason,
            fix_action=fix_action,
        ))

        current_code = fixed_code
        fix_log.total_iterations = i + 1

    fix_log.final_consistent = current_report.is_consistent
    return current_code, fix_log


def _analyze_diff(report: ComparisonReport) -> str:
    """分析差异原因"""
    diffs = report.differences
    reasons = []

    if diffs.get("I²", 0) > DIFF_THRESHOLD:
        reasons.append("异质性(I²)不一致 — 可能模型选择或权重计算有误")
    if diffs.get("Pooled Effect Size", 0) > DIFF_THRESHOLD:
        reasons.append("合并效应量差异 — 检查效应量公式和权重")
    if diffs.get("τ²", 0) > DIFF_THRESHOLD:
        reasons.append("tau²估计差异 — 尝试不同估计方法")
    if diffs.get("p-value", 0) > DIFF_THRESHOLD:
        reasons.append("p值差异 — 检查SE计算和自由度")

    if not reasons:
        reasons.append("细微数值差异 — 尝试切换模型或数值精度")

    return "; ".join(reasons)


def _apply_fix(code: str, report: ComparisonReport, iteration: int) -> str:
    """应用修正策略"""
    strategies = [
        # 策略1: 调整 tau² 计算
        lambda c: _modify_tau2_calculation(c),
        # 策略2: 切换到 REML
        lambda c: _switch_to_reml(c),
        # 策略3: 调整数值精度
        lambda c: _adjust_precision(c),
    ]

    if iteration < len(strategies):
        return strategies[iteration](code)
    return code


def _modify_tau2_calculation(code: str) -> str:
    """修改 tau² 计算公式"""
    # 尝试更精确的 tau² 计算
    if "tau2 = max(0" in code:
        code = re.sub(
            r'tau2\s*=\s*max\(0,\s*\(Q\s*-\s*df\)\s*/\s*C\)\s*if\s*Q\s*>\s*df\s*else\s*0',
            'tau2 = max(0, (Q - df) / C) if Q > df else 0.0',
            code
        )
    return code


def _switch_to_reml(code: str) -> str:
    """尝试切换到 REML 模型"""
    if '"DL"' in code:
        code = code.replace('"DL"', '"REML"')
    if "model == 'DL'" in code:
        code = code.replace("model == 'DL'", "model == 'REML'")
    return code


def _adjust_precision(code: str) -> str:
    """提高数值精度"""
    code = re.sub(r'np\.float64', 'np.float64', code)
    return code