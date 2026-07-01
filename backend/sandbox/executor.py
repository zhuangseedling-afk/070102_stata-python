"""沙箱执行器 — 隔离执行 Python 代码"""
import subprocess
import tempfile
import os
import signal
import re
from ..config import SANDBOX_TIMEOUT, SANDBOX_MAX_MEMORY_MB


def execute_python_code(code: str) -> dict:
    """
    在沙箱中执行 Python 代码
    返回: {
        "success": bool,
        "stdout": str,
        "stderr": str,
        "exit_code": int,
        "timed_out": bool,
    }
    """
    result = {
        "success": False,
        "stdout": "",
        "stderr": "",
        "exit_code": -1,
        "timed_out": False,
    }

    try:
        # 写入临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name

        # 使用 subprocess 执行，限制时间和内存
        proc = subprocess.Popen(
            ["python3", tmp_path],    # 不隔离，以使用已安装的包
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )

        try:
            stdout, stderr = proc.communicate(timeout=SANDBOX_TIMEOUT)
            result["stdout"] = stdout[:50000]  # 限制输出大小
            result["stderr"] = stderr[:50000]
            result["exit_code"] = proc.returncode
            result["success"] = proc.returncode == 0
        except subprocess.TimeoutExpired:
            if hasattr(os, "killpg"):
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:
                proc.kill()
            proc.wait()
            result["timed_out"] = True
            result["stderr"] = f"Execution timed out after {SANDBOX_TIMEOUT}s"
            result["exit_code"] = -1

        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    except Exception as e:
        result["stderr"] = str(e)

    return result


def simulate_stata_output(parsed_command, python_metrics: dict) -> str:
    """
    模拟 Stata 输出格式，基于 Python 计算结果
    参数:
        parsed_command: ParsedStataCommand
        python_metrics: 从 Python 执行结果中提取的指标
    """
    metrics = python_metrics
    cmd = parsed_command.command.upper()

    lines = []
    lines.append("." + "─" * 78)

    if parsed_command.subgroup_col and "subgroup_results" in metrics:
        # 分组亚组输出
        lines.append(f"-> {cmd}: Meta-Analysis by {parsed_command.subgroup_col}")
        lines.append("")
        subgroup_results = metrics["subgroup_results"]
        for sg in subgroup_results:
            lines.append(f"  ───────────────┼─────────────────────────────────")
            lines.append(f"  Subgroup: {sg.get('name', '?')}        |")
            lines.append(f"  Pooled ES      |   {sg.get('pooled_effect', 0):.4f}")
            lines.append(f"  95% CI         |   [{sg.get('ci_lower', 0):.4f}, {sg.get('ci_upper', 0):.4f}]")
            lines.append(f"  I-squared      |   {sg.get('i_squared', 0):.1f}%")
            lines.append(f"  Q statistic    |   {sg.get('q_statistic', 0):.2f}")
            lines.append(f"  p-value        |   {sg.get('q_p_value', 0):.4f}")
        lines.append(f"  ───────────────┼─────────────────────────────────")
        lines.append(f"  Overall        |")
        lines.append(f"  Pooled ES      |   {metrics.get('pooled_effect', 0):.4f}")
        lines.append(f"  95% CI         |   [{metrics.get('ci_lower', 0):.4f}, {metrics.get('ci_upper', 0):.4f}]")
        lines.append(f"  ───────────────┼─────────────────────────────────")
        lines.append(f"  Heterogeneity  |")
        lines.append(f"    I-squared    |   {metrics.get('i_squared', 0):.1f}%")
        lines.append(f"    Q statistic  |   {metrics.get('q_statistic', 0):.2f}")
        lines.append(f"    p-value      |   {metrics.get('q_p_value', 0):.4f}")
        lines.append(f"    tau-squared  |   {metrics.get('tau_squared', 0):.4f}")
        lines.append(f"  ───────────────┼─────────────────────────────────")
        lines.append(f"  Test of ES=0   |")
        lines.append(f"    z            |   {metrics.get('z_score', 0):.2f}")
        lines.append(f"    p-value      |   {metrics.get('p_value', 0):.4f}")
        lines.append(f"  ───────────────┴─────────────────────────────────")
        model = "Random-effects (DerSimonian-Laird)" if metrics.get('model', '') == 'DL' else "Fixed-effects"
        lines.append(f"  Model: {model}")
    elif cmd == "METAN":
        lines.append(f"-> {cmd}: Meta-Analysis ")
        lines.append("")
        lines.append(f"  Study         |")
        lines.append(f"  ───────────────┼─────────────────────────────────")
        lines.append(f"  Pooled ES      |   {metrics.get('pooled_effect', 0):.4f}")
        lines.append(f"  95% CI         |   [{metrics.get('ci_lower', 0):.4f}, {metrics.get('ci_upper', 0):.4f}]")
        lines.append(f"  ───────────────┼─────────────────────────────────")
        lines.append(f"  Heterogeneity  |")
        lines.append(f"    I-squared    |   {metrics.get('i_squared', 0):.1f}%")
        lines.append(f"    Q statistic  |   {metrics.get('q_statistic', 0):.2f}")
        lines.append(f"    p-value      |   {metrics.get('q_p_value', 0):.4f}")
        lines.append(f"    tau-squared  |   {metrics.get('tau_squared', 0):.4f}")
        lines.append(f"  ───────────────┼─────────────────────────────────")
        lines.append(f"  Test of ES=0   |")
        lines.append(f"    z            |   {metrics.get('z_score', 0):.2f}")
        lines.append(f"    p-value      |   {metrics.get('p_value', 0):.4f}")
        lines.append(f"  ───────────────┴─────────────────────────────────")
        model = "Random-effects (DerSimonian-Laird)" if metrics.get('model', '') == 'DL' else "Fixed-effects"
        lines.append(f"  Model: {model}")
    elif cmd == "METAPROP":
        lines.append(f"-> {cmd}: Proportion Meta-Analysis")
        lines.append(f"  Pooled Proportion | {metrics.get('pooled_effect', 0):.4f}")
        lines.append(f"  95% CI            | [{metrics.get('ci_lower', 0):.4f}, {metrics.get('ci_upper', 0):.4f}]")
        lines.append(f"  I-squared         | {metrics.get('i_squared', 0):.1f}%")
        lines.append(f"  Q                 | {metrics.get('q_statistic', 0):.2f}")
        lines.append(f"  p (heterogeneity) | {metrics.get('q_p_value', 0):.4f}")
    elif cmd == "METAREG":
        lines.append(f"-> {cmd}: Meta-Regression")
        lines.append(f"  Covariates        | {metrics.get('covariates', 'N/A')}")
        lines.append(f"  tau-squared       | {metrics.get('tau_squared', 0):.4f}")
        lines.append(f"  I-squared (resid) | {metrics.get('i_squared', 0):.1f}%")
    elif cmd in ("FUNNEL", "METAFUNNEL"):
        lines.append(f"-> {cmd}: Funnel Plot")
        lines.append(f"  Egger's test: t = {metrics.get('egger_t', 0):.2f}")
        lines.append(f"  p = {metrics.get('egger_p', 0):.4f}")
    elif cmd == "FOREST":
        lines.append(f"-> {cmd}: Forest Plot")
        lines.append(f"  Pooled ES: {metrics.get('pooled_effect', 0):.4f}")
        lines.append(f"  95% CI: [{metrics.get('ci_lower', 0):.4f}, {metrics.get('ci_upper', 0):.4f}]")
    else:
        lines.append(f"-> {cmd}: Results")
        lines.append(f"  Pooled ES: {metrics.get('pooled_effect', 0):.4f}")
        lines.append(f"  95% CI: [{metrics.get('ci_lower', 0):.4f}, {metrics.get('ci_upper', 0):.4f}]")
        lines.append(f"  p-value:  {metrics.get('p_value', 0):.4f}")
        lines.append(f"  I²:       {metrics.get('i_squared', 0):.1f}%")

    lines.append("." + "─" * 78)
    return "\n".join(lines)