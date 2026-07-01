"""Stata 真实执行器 —— 在本地/远程 Stata 中运行 .do 文件并捕获输出"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


# macOS 常见 Stata 安装路径（可扩展）
STATA_CANDIDATE_PATHS = [
    "/Applications/Stata/StataSE.app/Contents/MacOS/StataSE",
    "/Applications/Stata/StataMP.app/Contents/MacOS/StataMP",
    "/Applications/Stata/StataBE.app/Contents/MacOS/StataBE",
    "/Applications/StataSE.app/Contents/MacOS/StataSE",
    "/Applications/StataMP.app/Contents/MacOS/StataMP",
    "/Applications/StataBE.app/Contents/MacOS/StataBE",
    "/usr/local/stata17/stata-se",
    "/usr/local/stata17/stata-mp",
    "/usr/local/stata17/stata",
    "/usr/local/stata16/stata-se",
    "/usr/local/stata16/stata-mp",
    "/usr/local/stata16/stata",
    "/usr/local/bin/stata",
    "/usr/local/bin/stata-se",
    "/usr/local/bin/stata-mp",
]


def find_stata_executable(user_path: str = "") -> Optional[str]:
    """查找可用的 Stata 可执行文件。"""
    candidates = [user_path] + STATA_CANDIDATE_PATHS if user_path else STATA_CANDIDATE_PATHS
    for p in candidates:
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    # 尝试 PATH
    for name in ["stata", "stata-se", "stata-mp", "StataSE", "StataMP"]:
        found = shutil.which(name)
        if found:
            return found
    return None


def run_stata_do(stata_code: str, stata_path: str = "", timeout: int = 60) -> dict:
    """
    将 Stata 代码写入临时 .do 文件并调用真实 Stata 执行。

    返回:
        {
            "success": bool,
            "stata_path": str,          # 实际使用的 Stata 路径
            "do_file": str,             # 临时 .do 文件路径
            "log": str,                 # Stata 输出日志
            "exit_code": int,
            "error": str,               # 错误说明
        }
    """
    result = {
        "success": False,
        "stata_path": "",
        "do_file": "",
        "log": "",
        "exit_code": -1,
        "error": "",
    }

    exe = find_stata_executable(stata_path)
    if not exe:
        result["error"] = (
            "未找到可用的 Stata 可执行文件。"
            "请安装 Stata 或在下方输入正确的 Stata 路径。"
        )
        return result
    result["stata_path"] = exe

    # 写入临时 .do 文件
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".do", delete=False, encoding="utf-8") as f:
            f.write(stata_code)
            do_path = f.name
        result["do_file"] = do_path

        # Stata 命令行：-b do file.do 会生成 file.log
        # 使用 -q 安静模式可选；这里保留完整输出
        cmd = [exe, "-b", "do", do_path]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        result["exit_code"] = proc.returncode

        # 优先读取同名的 .log 文件（Stata -b 模式默认行为）
        log_path = do_path.replace(".do", ".log")
        log_text = ""
        if os.path.isfile(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    log_text = f.read()
            except Exception as e:
                log_text = f"[读取 log 文件失败: {e}]\n"

        # 合并 stdout/stderr
        combined = proc.stdout + "\n" + proc.stderr
        result["log"] = (log_text + "\n" + combined).strip()
        result["success"] = proc.returncode == 0 and bool(log_text)

        # 清理临时文件
        try:
            os.unlink(do_path)
            if os.path.isfile(log_path):
                os.unlink(log_path)
        except OSError:
            pass

    except subprocess.TimeoutExpired:
        result["error"] = f"Stata 执行超时（{timeout} 秒）"
    except Exception as e:
        result["error"] = f"执行异常: {e}"

    return result


def extract_stata_metrics(stata_log: str) -> dict:
    """
    从 Stata 日志文本中提取常见 Meta 分析指标。

    注意：这是基于 metan / metaprop 常见输出格式的启发式解析，
    实际 Stata 输出会随版本、命令选项变化。解析失败时返回空值。
    """
    text = stata_log.replace(",", " ")
    metrics: dict = {}

    # 研究数量
    m = re.search(r'Number of studies\s*[:=]?\s*(\d+)', text, re.IGNORECASE)
    if m:
        metrics["number_of_studies"] = int(m.group(1))

    # Pooled effect / ES
    m = re.search(r'Pooled ES\s*[:=]?\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if not m:
        m = re.search(r'Pooled effect\s*[:=]?\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics["pooled_effect"] = float(m.group(1))

    # 95% CI
    m = re.search(r'95% CI\s*[:=]?\s*\[?\s*([\-\d.eE]+)\s*,?\s+([\-\d.eE]+)\s*\]?', text, re.IGNORECASE)
    if m:
        metrics["ci_lower"] = float(m.group(1))
        metrics["ci_upper"] = float(m.group(2))

    # z / p
    m = re.search(r'z\s*[:=]?\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics["z_score"] = float(m.group(1))
    m = re.search(r'p[- ]?value\s*[:=]?\s*([\-\d.eE]+|<0\.0001)', text, re.IGNORECASE)
    if m:
        val = m.group(1)
        metrics["p_value"] = 0.0 if val == "<0.0001" else float(val)

    # 异质性
    m = re.search(r'I\-squared\s*[:=]?\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics["i_squared"] = float(m.group(1))
    m = re.search(r'Q statistic\s*[:=]?\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics["q_statistic"] = float(m.group(1))
    m = re.search(r'tau\-squared\s*[:=]?\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics["tau_squared"] = float(m.group(1))
    m = re.search(r'H\-squared\s*[:=]?\s*([\-\d.eE]+)', text, re.IGNORECASE)
    if m:
        metrics["h_squared"] = float(m.group(1))

    # 模型
    if re.search(r'Random[- ]effects', text, re.IGNORECASE):
        metrics["model"] = "DL"
    elif re.search(r'Fixed[- ]effects', text, re.IGNORECASE):
        metrics["model"] = "FE"

    return metrics
