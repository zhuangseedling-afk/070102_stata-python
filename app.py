"""
MetaFlow — Stata Meta-Analysis -> Python Translator
Streamlit 主程序（学术期刊风格 UI + 三栏布局 + 验证对照）
"""
from __future__ import annotations

import sys
import os
import json
import hashlib
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.engine.rule_engine import translate_stata, translate_stata_batch
from backend.sandbox.executor import execute_python_code
from backend.comparator.metrics import extract_metrics_from_output, MetaMetrics
from backend.comparator.differ import compare_metrics
from backend.data.examples import EXAMPLES
from backend.stata_runner import find_stata_executable, run_stata_do, extract_stata_metrics

# ─────────────────────────────────────────────────────────────
# 页面配置
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MetaFlow | Stata → Python",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# 常量与选项
# ─────────────────────────────────────────────────────────────
MODEL_OPTIONS = {"随机效应 (RE)": "RE", "固定效应 (FE)": "FE", "公共效应 (CE)": "CE"}
TAU2_OPTIONS = {
    "DerSimonian-Laird (DL)": "DL",
    "Restricted ML (REML)": "REML",
    "Maximum Likelihood (ML)": "ML",
    "Hedges": "Hedges",
    "Sidik-Jonkman (SJ)": "SJ",
    "Hunter-Schmidt (HS)": "HS",
    "Empirical Bayes (EB)": "EB",
}
MODE_OPTIONS = {"单条 (Single)": "single", "批量 (Batch)": "batch"}

# ─────────────────────────────────────────────────────────────
# 学术期刊风 CSS 注入
# ─────────────────────────────────────────────────────────────
def inject_academic_css() -> None:
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400&family=Source+Serif+4:ital,opsz,wght@0,8..60,300..900;1,8..60,300..900&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --paper: #FDFCF8;
        --paper-elevated: #FFFFFF;
        --ink: #2C3E50;
        --ink-muted: #6B7280;
        --border: #E5E1D8;
        --navy: #1E3A5F;
        --navy-deep: #152A47;
        --gold: #A67C52;
        --gold-soft: #D4B996;
        --warm: #F5F3EE;
        --radius: 4px;
        --shadow-soft: 0 1px 2px rgba(30, 58, 95, 0.06), 0 4px 12px rgba(30, 58, 95, 0.04);
    }

    /* ── 页面基调：带轻微纸纹的学术白 ── */
    .stApp {
        background-color: var(--paper);
        color: var(--ink);
        font-family: 'Source Serif 4', Georgia, 'Times New Roman', serif;
    }
    .stApp::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image:
            radial-gradient(circle at 20% 20%, rgba(166, 124, 82, 0.04) 0%, transparent 45%),
            radial-gradient(circle at 80% 80%, rgba(30, 58, 95, 0.04) 0%, transparent 45%),
            url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.025'/%3E%3C/svg%3E");
        pointer-events: none;
        z-index: 0;
    }

    /* ── 隐藏默认页眉/页脚/侧边栏 ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {display: none !important;}
    .stAppDeployButton {display: none !important;}
    [data-testid="stSidebar"] {display: none !important;}
    [data-testid="stSidebarCollapsedControl"] {display: none !important;}

    /* ── 入场动画 ── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(16px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .main > div {
        animation: fadeInUp 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
    }
    .main > div:nth-child(2) { animation-delay: 0.08s; }
    .main > div:nth-child(3) { animation-delay: 0.16s; }
    .main > div:nth-child(4) { animation-delay: 0.24s; }

    /* ── 标题样式 ── */
    .hero-title {
        font-family: 'Crimson Text', Georgia, serif;
        font-size: 2.9rem;
        font-weight: 700;
        color: var(--navy);
        letter-spacing: -0.5px;
        margin-bottom: 0.2rem;
        line-height: 1.05;
    }
    .hero-subtitle {
        color: var(--ink-muted);
        font-size: 1rem;
        font-weight: 400;
        letter-spacing: 0.2px;
        margin-bottom: 0.5rem;
    }
    .hero-divider {
        height: 1px;
        background: linear-gradient(90deg, var(--gold) 0%, var(--border) 60%, transparent 100%);
        margin: 1rem 0 1.5rem 0;
    }

    /* ── 期刊风章节标题 ── */
    .section-title {
        font-family: 'Crimson Text', Georgia, serif;
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--navy);
        margin-bottom: 1.1rem;
        display: flex;
        align-items: baseline;
        gap: 12px;
    }
    .section-title .num {
        font-family: 'Crimson Text', Georgia, serif;
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--gold);
        border: 1px solid var(--gold-soft);
        border-radius: 999px;
        width: 28px;
        height: 28px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }
    .section-title .label {
        border-bottom: 1px solid var(--border);
        padding-bottom: 2px;
    }

    /* ── 状态徽章 ── */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.4px;
        border: 1px solid var(--border);
        background: var(--paper-elevated);
        color: var(--navy);
        box-shadow: var(--shadow-soft);
    }
    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--gold);
    }

    /* ── 顶部配置栏：手稿元数据块 ── */
    .top-config-start + div {
        background: var(--paper-elevated) !important;
        border: 1px solid var(--border);
        border-top: 3px solid var(--navy);
        border-radius: var(--radius) !important;
        padding: 26px 30px !important;
        margin-bottom: 28px;
        box-shadow: var(--shadow-soft);
    }
    .top-config-title {
        font-family: 'Crimson Text', Georgia, serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--navy);
        margin-bottom: 0;
        line-height: 1.2;
    }
    .top-config-subtitle {
        font-size: 0.7rem;
        color: var(--ink-muted);
        letter-spacing: 0.6px;
        text-transform: uppercase;
        font-weight: 600;
    }
    .top-config-label {
        font-size: 0.68rem;
        color: var(--ink-muted);
        text-transform: uppercase;
        letter-spacing: 0.7px;
        margin-bottom: 7px;
        font-weight: 600;
    }

    /* ── 按钮 ── */
    div[data-testid="stButton"] > button[kind="primary"] {
        width: 100%;
        background: var(--navy) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        letter-spacing: 0.4px;
        border: none !important;
        border-radius: var(--radius) !important;
        padding: 12px 20px !important;
        box-shadow: var(--shadow-soft) !important;
        transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1) !important;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background: var(--navy-deep) !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(30, 58, 95, 0.14) !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"] {
        background: var(--paper-elevated) !important;
        color: var(--navy) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background: var(--warm) !important;
        border-color: var(--gold) !important;
        color: var(--navy-deep) !important;
    }
    div[data-testid="stButton"] > button {
        white-space: nowrap !important;
    }

    /* ── 文本域 ── */
    div[data-testid="stTextArea"] textarea {
        background: var(--paper-elevated) !important;
        color: var(--ink) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        font-family: 'JetBrains Mono', 'SF Mono', Monaco, monospace !important;
        font-size: 0.88rem !important;
        line-height: 1.6 !important;
        padding: 18px !important;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.03) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-testid="stTextArea"] textarea:focus {
        border-color: var(--navy) !important;
        box-shadow: 0 0 0 3px rgba(30, 58, 95, 0.08) !important;
    }

    /* ── 选择器 / 滑块 / 开关 ── */
    div[data-baseweb="select"] > div,
    div[data-testid="stSelectbox"] > div > div {
        background: var(--paper-elevated) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        color: var(--ink) !important;
    }
    div[data-testid="stSlider"] > div > div > div {
        background: var(--navy) !important;
    }
    div[data-testid="stToggle"] button {
        background: var(--border) !important;
    }
    div[data-testid="stToggle"] button[aria-checked="true"] {
        background: var(--navy) !important;
    }

    /* ── 代码块 ── */
    .stCodeBlock {
        border-radius: var(--radius) !important;
        border: 1px solid var(--border) !important;
        box-shadow: var(--shadow-soft) !important;
    }
    .stCodeBlock pre {
        background: #F8F7F4 !important;
    }
    .stCodeBlock code {
        font-family: 'JetBrains Mono', 'SF Mono', Monaco, monospace !important;
        font-size: 0.84rem !important;
        line-height: 1.65 !important;
        color: var(--ink) !important;
    }

    /* ── 数据表格 ── */
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-soft) !important;
    }
    div[data-testid="stDataFrame"] th {
        background: var(--warm) !important;
        color: var(--navy) !important;
        font-weight: 700 !important;
        border-bottom: 1px solid var(--border) !important;
    }
    div[data-testid="stDataFrame"] td {
        background: var(--paper-elevated) !important;
        color: var(--ink) !important;
    }

    /* ── Expander ── */
    div[data-testid="stExpander"] {
        background: var(--paper-elevated) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
    }
    div[data-testid="stExpander"] > details > summary {
        color: var(--ink) !important;
        font-weight: 600 !important;
    }

    /* ── Tabs ── */
    button[data-baseweb="tab"] {
        color: var(--ink-muted) !important;
        font-weight: 600 !important;
        letter-spacing: 0.2px;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--navy) !important;
    }
    [data-testid="stTabs"] [role="tablist"] {
        border-bottom: 1px solid var(--border) !important;
    }

    /* ── 提示框 ── */
    div[data-testid="stSuccessAlert"] {
        background: #F6F9F6 !important;
        border: 1px solid #A3C9A8 !important;
        border-radius: var(--radius) !important;
        color: #2A5A3A !important;
    }
    div[data-testid="stErrorAlert"] {
        background: #FDF6F6 !important;
        border: 1px solid #E4A6A6 !important;
        border-radius: var(--radius) !important;
        color: #7A2626 !important;
    }
    div[data-testid="stWarningAlert"] {
        background: #FDFCF5 !important;
        border: 1px solid #E6D69C !important;
        border-radius: var(--radius) !important;
        color: #7A5C1A !important;
    }
    div[data-testid="stInfoAlert"] {
        background: #F5F8FC !important;
        border: 1px solid #A6C4E4 !important;
        border-radius: var(--radius) !important;
        color: #264A7A !important;
    }

    /* ── Metric 卡片 ── */
    div[data-testid="stMetric"] {
        background: var(--paper-elevated) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        padding: 16px !important;
        box-shadow: var(--shadow-soft) !important;
    }
    div[data-testid="stMetric"] > div:first-child {
        color: var(--ink-muted) !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    div[data-testid="stMetric"] > div:nth-child(2) {
        color: var(--navy) !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }

    /* ── 文件上传 ── */
    [data-testid="stFileUploaderDropzone"] {
        background: var(--paper-elevated) !important;
        border: 1px dashed var(--border) !important;
        border-radius: var(--radius) !important;
        color: var(--ink-muted) !important;
        min-height: 34px !important;
        padding: 4px 10px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 10px !important;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: var(--navy) !important;
        background: var(--warm) !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzone"] button {
        padding: 4px 12px !important;
        font-size: 0.75rem !important;
        white-space: nowrap !important;
    }

    /* ── 分隔线 ── */
    hr {
        border: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border), transparent);
        margin: 2rem 0;
    }

    /* ── 滚动条 ── */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--warm);
    }
    ::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--ink-muted);
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────
@st.cache_data
def load_reference_datasets() -> dict[str, dict]:
    """加载 stata_reference.json 中的参考数据集"""
    ref_path = Path(__file__).parent / "stata_reference.json"
    if not ref_path.exists():
        return {}
    data = json.loads(ref_path.read_text(encoding="utf-8"))
    return {ds["id"]: ds for ds in data.get("datasets", [])}


def reference_select_options() -> dict[str, str | None]:
    """构造参考数据集下拉选项"""
    refs = load_reference_datasets()
    return {"（选择参考数据集）": None, **{ds["name"]: ds_id for ds_id, ds in refs.items()}}


def example_select_options() -> dict[str, dict | None]:
    """构造内置示例下拉选项"""
    return {"（选择内置示例）": None, **{ex["title"]: ex for ex in EXAMPLES}}


def build_backend_options(
    model_label: str,
    tau2_label: str,
    confidence_level: int,
    eform: bool,
    mode_label: str,
) -> dict[str, Any]:
    """将侧边栏选项映射为后端可识别的参数字典"""
    model_val = MODEL_OPTIONS[model_label]
    tau2_val = TAU2_OPTIONS[tau2_label]
    mode_val = MODE_OPTIONS[mode_label]

    if model_val == "RE":
        backend_model = tau2_val if tau2_val in ("REML", "ML") else "DL"
    elif model_val == "FE":
        backend_model = "FE"
    elif model_val == "CE":
        backend_model = "CE"
    else:
        backend_model = "DL"

    return {
        "model": backend_model,
        "tau2_estimator": tau2_val,
        "confidence_level": float(confidence_level),
        "eform": bool(eform),
        "translation_mode": mode_val,
    }


def run_translation(stata_code: str, options: dict[str, Any]) -> tuple[Any, Any]:
    """转译 Stata 代码并执行生成的 Python 代码。

    根据 options['translation_mode'] 决定单条或批量处理：
      - single: 返回 (TranslationResult, exec_result)
      - batch:  返回 (list[TranslationResult], list[exec_result])
    """
    mode = options.get("translation_mode", "single")
    if mode == "batch":
        # 批量模式下，每条 Stata 命令自身的模型/选项优先；
        # 仅把 confidence_level 等全局设置透传下去。
        batch_options = {
            "confidence_level": float(options.get("confidence_level", 95.0)),
        }
        results = translate_stata_batch(stata_code, options=batch_options)
        exec_results = []
        for res in results:
            if not res.python_code or res.python_code.startswith("# Unable"):
                exec_results.append(None)
            else:
                exec_results.append(execute_python_code(res.python_code))
        return results, exec_results

    result = translate_stata(stata_code, options=options)
    if not result.python_code or result.python_code.startswith("# Unable"):
        return result, None
    exec_result = execute_python_code(result.python_code)
    return result, exec_result


def display_generated_plot() -> None:
    """显示生成的森林图/漏斗图"""
    for plot_name in ["forest_plot.png", "funnel_plot.png"]:
        plot_path = Path(plot_name)
        if plot_path.exists():
            st.image(str(plot_path), use_container_width=True)


def build_validation_table(
    ref_dict: dict[str, Any], py_metrics: MetaMetrics
) -> tuple[pd.DataFrame, bool]:
    """根据参考值与 Python 输出构建分组对比表

    维度覆盖 Stata 官方 meta 输出中的核心指标：
    模型/样本、合并效应、异质性、预测区间、发表偏倚、Meta 回归、亚组分析、Trim-and-fill 等。
    """
    metric_groups = [
        ("模型与数据", [
            ("number_of_studies", "Number of studies"),
            ("model", "Model"),
            ("model_method", "Method"),
            ("effect_measure", "Effect measure"),
        ]),
        ("合并效应", [
            ("pooled_effect", "Pooled Effect"),
            ("ci_lower", "CI Lower"),
            ("ci_upper", "CI Upper"),
            ("z_score", "z-score"),
            ("p_value", "p-value (overall)"),
        ]),
        ("异质性", [
            ("q_statistic", "Q Statistic"),
            ("q_df", "Q df"),
            ("q_p_value", "p-value for Q"),
            ("i_squared", "I² (%)"),
            ("h_squared", "H²"),
            ("tau_squared", "τ²"),
        ]),
        ("预测区间", [
            ("prediction_interval_lower", "Prediction Interval Lower"),
            ("prediction_interval_upper", "Prediction Interval Upper"),
        ]),
        ("发表偏倚", [
            ("egger_intercept", "Egger's intercept"),
            ("egger_t", "Egger's t"),
            ("egger_p", "Egger's p"),
            ("begg_z", "Begg's z"),
            ("begg_p", "Begg's p"),
            ("harbord_beta1", "Harbord beta1"),
            ("harbord_z", "Harbord z"),
            ("harbord_p", "Harbord p"),
        ]),
        ("Meta 回归", [
            ("metareg_r_squared", "R² (%)"),
            ("metareg_wald_chi2", "Wald χ²"),
            ("metareg_wald_p", "Wald p"),
            ("residual_q", "Residual Q"),
            ("residual_q_p_value", "Residual Q p-value"),
        ]),
        ("亚组分析", [
            ("subgroup_between_q", "Subgroup between-Q"),
            ("subgroup_between_p", "Subgroup between-p"),
        ]),
        ("Trim-and-fill", [
            ("trimfill_missing_studies", "Missing studies"),
            ("trimfill_adjusted_effect", "Adjusted effect"),
            ("trimfill_adjusted_ci_lower", "Adjusted CI lower"),
            ("trimfill_adjusted_ci_upper", "Adjusted CI upper"),
        ]),
    ]
    rows = []
    all_pass = True
    tolerance = 0.01

    for group_name, metrics in metric_groups:
        for key, label in metrics:
            if key not in ref_dict:
                continue
            ref_raw = ref_dict[key]
            py_raw = getattr(py_metrics, key, 0.0)

            # 字符串字段（model / effect_measure）直接精确匹配
            if isinstance(ref_raw, str) or key in ("model", "effect_measure"):
                ref_val_str = str(ref_raw).strip().lower()
                py_val_str = str(py_raw).strip().lower()
                passed = ref_val_str == py_val_str or not ref_val_str or not py_val_str
                if not passed:
                    all_pass = False
                rows.append(
                    {
                        "维度": group_name,
                        "指标": label,
                        "Stata 参考值": ref_raw,
                        "Python 输出值": py_raw,
                        "绝对差": "—" if passed else "不匹配",
                        "相对差": "—" if passed else "不匹配",
                        "状态": "通过" if passed else "失败",
                    }
                )
                continue

            ref_val = float(ref_raw)
            py_val = float(py_raw)
            abs_diff = abs(ref_val - py_val)
            rel_diff = abs_diff / max(abs(ref_val), 1e-12)
            passed = rel_diff <= tolerance
            if not passed:
                all_pass = False
            rows.append(
                {
                    "维度": group_name,
                    "指标": label,
                    "Stata 参考值": ref_val,
                    "Python 输出值": py_val,
                    "绝对差": round(abs_diff, 6),
                    "相对差": f"{rel_diff:.2%}",
                    "状态": "通过" if passed else "失败",
                }
            )

    return pd.DataFrame(rows), all_pass


# ─────────────────────────────────────────────────────────────
# UI 组件
# ─────────────────────────────────────────────────────────────
def render_header() -> None:
    """顶部品牌栏"""
    cols = st.columns([0.75, 0.25])
    with cols[0]:
        st.markdown(
            """
            <div class="hero-title">MetaFlow</div>
            <div class="hero-subtitle">Stata Meta-Analysis → Python 翻译器 | 规则匹配优先 + LLM 兜底</div>
            """,
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            """
            <div style="display:flex;justify-content:flex-end;align-items:center;height:100%;padding-top:8px;">
                <span class="status-badge"><span class="status-dot"></span>引擎在线</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown('<div class="hero-divider"></div>', unsafe_allow_html=True)


def render_top_config_bar() -> tuple[str, str, int, bool, str, Any, dict | None, str, bool]:
    """渲染顶部横向配置导航栏（宽松两排布局）"""
    st.markdown('<div class="top-config-start"></div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div style="display:flex;align-items:baseline;gap:14px;margin-bottom:22px;">
            <div class="top-config-title">⚙️ 配置面板</div>
            <div class="top-config-subtitle">Configuration</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 第一排：核心分析选项
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1], gap="large")
    with c1:
        st.markdown('<div class="top-config-label">分析模型</div>', unsafe_allow_html=True)
        model_label = st.selectbox("分析模型", list(MODEL_OPTIONS.keys()), index=0, label_visibility="collapsed")
    with c2:
        st.markdown('<div class="top-config-label">τ² 估计量</div>', unsafe_allow_html=True)
        tau2_label = st.selectbox("τ² 估计量", list(TAU2_OPTIONS.keys()), index=0, label_visibility="collapsed")
    with c3:
        st.markdown('<div class="top-config-label">置信水平</div>', unsafe_allow_html=True)
        confidence_level = st.slider("置信水平", min_value=50, max_value=99, value=95, label_visibility="collapsed")
    with c4:
        st.markdown('<div class="top-config-label">取指数 (eform)</div>', unsafe_allow_html=True)
        eform = st.toggle("取指数 (eform)", value=False, label_visibility="collapsed")

    # 第二排：运行与输入选项
    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
    c5, c6, c7, c8 = st.columns([1, 1, 1, 1], gap="large")
    with c5:
        st.markdown('<div class="top-config-label">转译模式</div>', unsafe_allow_html=True)
        mode_label = st.selectbox("转译模式", list(MODE_OPTIONS.keys()), index=0, label_visibility="collapsed")
    with c6:
        st.markdown('<div class="top-config-label">文件上传</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "上传 Stata 脚本",
            type=["txt", "do", "stata", "ado"],
            accept_multiple_files=False,
            label_visibility="collapsed",
        )
    with c7:
        st.markdown('<div class="top-config-label">内置示例</div>', unsafe_allow_html=True)
        example_options = example_select_options()
        example_title = st.selectbox("选择示例", list(example_options.keys()), index=0, label_visibility="collapsed")
    with c8:
        st.markdown('<div class="top-config-label">&nbsp;</div>', unsafe_allow_html=True)
        load_example = st.button("加载示例", use_container_width=True)

    return model_label, tau2_label, confidence_level, eform, mode_label, uploaded_file, example_options, example_title, load_example


def render_input_panel() -> tuple[str, bool]:
    """渲染 Stata 脚本输入面板"""
    st.markdown(
        '<div class="section-title"><span class="num">I</span><span class="label">Stata · 脚本输入</span></div>',
        unsafe_allow_html=True,
    )

    if "stata_code" not in st.session_state:
        st.session_state["stata_code"] = ""

    stata_code = st.text_area(
        "在此输入 Stata meta 分析代码...",
        key="stata_code",
        height=420,
        label_visibility="collapsed",
    )

    translate_clicked = st.button("🔄 转译 → Python", type="primary", use_container_width=True)
    return stata_code, translate_clicked


def _render_single_output(result: Any, exec_result: Any | None, idx: int = 0) -> None:
    """渲染单个命令单元的输出（代码 / 执行 / 日志）。"""
    prefix = f"命令 {idx + 1}: " if idx else ""
    tab_code, tab_exec, tab_log = st.tabs(
        [f"{prefix}💻 生成代码", f"{prefix}▶️ 执行输出", f"{prefix}📋 转译日志"]
    )

    with tab_code:
        st.code(result.python_code, language="python")
        st.download_button(
            label="📥 下载 .py 文件",
            data=result.python_code,
            file_name=f"translated_{idx + 1}.py",
            mime="text/x-python",
            use_container_width=True,
        )

    with tab_exec:
        if exec_result is not None:
            if exec_result["success"]:
                st.markdown("**标准输出**")
                st.code(exec_result["stdout"], language="text")
                display_generated_plot()
            else:
                st.error("Python 代码执行失败")
                st.code(exec_result.get("stderr", ""), language="text")
        else:
            st.info("生成代码未执行或执行被跳过")

    with tab_log:
        parsed = result.parsed
        log = {
            "source": result.source,
            "command": parsed.command,
            "model": parsed.model,
            "effect_measure": parsed.effect_measure,
            "confidence_level": parsed.confidence_level,
            "tau2_estimator": parsed.tau2_estimator,
            "eform": parsed.eform,
            "translation_mode": parsed.translation_mode,
            "columns": parsed.column_names,
            "subgroup_col": parsed.subgroup_col,
        }
        st.json(log)


def render_output_panel(result: Any | None, exec_result: Any | None) -> None:
    """渲染右侧 Python 输出面板（使用 Tabs 组织）"""
    st.markdown(
        '<div class="section-title"><span class="num">II</span><span class="label">Python · 输出</span></div>',
        unsafe_allow_html=True,
    )

    if result is None:
        st.info("点击上方「转译 → Python」按钮生成代码")
        return

    # 批量模式：展示多个命令单元
    if isinstance(result, list):
        st.success(f"批量转译完成，共识别 {len(result)} 个命令单元")
        for idx, (res, ex) in enumerate(zip(result, exec_result or [])):
            with st.expander(f"命令单元 {idx + 1}: {res.parsed.command or 'unknown'}", expanded=(idx == 0)):
                _render_single_output(res, ex, idx)
        return

    _render_single_output(result, exec_result)


def render_validation_panel() -> None:
    """渲染验证对照面板"""
    st.markdown(
        '<div class="section-title"><span class="num">III</span><span class="label">验证对照</span></div>',
        unsafe_allow_html=True,
    )

    # 概念说明折叠区
    with st.expander("📖 验证对照与 Stata 概念说明（点击展开）", expanded=False):
        st.markdown(
            """
            **1. τ² 估计量是什么？**
            τ²（tau-squared）是随机效应模型中“研究间异质性方差”的估计值。不同的估计方法对 τ² 的计算方式不同，会直接影响合并效应的权重与置信区间：
            - **DL（DerSimonian-Laird）**：最常用，基于 Q 统计量的非迭代矩估计。
            - **REML / ML**：基于似然函数的迭代估计，REML 对小样本偏差更稳健。
            - **Hedges / SJ / HS / EB**：其他矩估计或经验贝叶斯方法，适用于不同数据场景。

            **2. 转译模式（Translation mode）是什么意思？**
            - **单条 (Single)**：每次把输入框中的**一条** Stata 命令翻译成 Python 并执行。
            - **批量 (Batch)**：把输入框中的**多行** Stata 代码一次性解析、批量生成 Python 代码。
            当前参考数据集主要面向单条 metan 命令验证，批量模式用于处理复杂脚本。

            **3. “Python · 输出”里的执行输出结果来自 Stata 还是 Python？**
            执行输出模块显示的是 **Python 代码在沙箱中运行后的结果**。流程是：Stata 脚本 → 规则引擎/Llm 转译 → 生成 Python → 在隔离进程中执行 → 展示输出。因此它实际上是“用 Python 复现 Stata 分析”的结果，验证对照就是把这些结果与已知的 Stata 参考值做比对。

            **4. 为什么验证对照需要选择参考数据集？**
            参考数据集是预先记录好“真实 Stata 输出”的标杆。选择后，系统会重新转译并执行该数据集的 Stata 代码，把 Python 复现结果与标杆逐项比较，从而量化转译引擎的准确度。

            **5. 为什么目前只有这几种参考数据集？**
            当前内置了 4 个覆盖最常见 metan 输入格式（2 变量 ES+SE、3 变量 ES+CI、6 变量原始数据 MD）的标杆。后续可以按同样格式在 `stata_reference.json` 中追加 metaprop、metareg、funnel、亚组分析、发表偏倚等更多标杆。

            **6. 当前可验证的维度有哪些？**
            本页面已扩展为 8 大类维度：模型与数据、合并效应、异质性、预测区间、发表偏倚、Meta 回归、亚组分析、Trim-and-fill。其中后 4 类会在参考数据集中提供对应值时自动显示。
            """
        )

    ref_options = reference_select_options()
    cols = st.columns([0.7, 0.3])
    with cols[0]:
        ref_name = st.selectbox("从 stata_reference.json 加载", list(ref_options.keys()), index=0, label_visibility="collapsed")
    with cols[1]:
        run_verify = st.button("▶️ 运行验证", use_container_width=True)

    if run_verify:
        selected_ref_id = ref_options.get(ref_name)
        if selected_ref_id is None:
            st.warning("请先选择一个参考数据集")
            return

        ref_dataset = load_reference_datasets().get(selected_ref_id)
        if ref_dataset is None:
            st.error("参考数据集不存在")
            return

        with st.spinner("正在运行验证..."):
            ref_options_backend = ref_dataset.get("options", {})
            v_result, v_exec = run_translation(ref_dataset["stata_code"], ref_options_backend)
            # 参考数据集默认单条；若返回批量结果则取第一个有效单元
            if isinstance(v_result, list):
                v_result = v_result[0] if v_result else None
                v_exec = v_exec[0] if v_exec else None
            if v_result is None or v_result.python_code.startswith("# Unable"):
                st.error("参考数据集转译失败")
            elif v_exec is None or not v_exec["success"]:
                st.error("参考数据集执行失败")
                if v_exec:
                    st.code(v_exec.get("stderr", ""), language="text")
            else:
                py_metrics = extract_metrics_from_output(v_exec["stdout"])
                ref_metrics_dict = ref_dataset.get("reference", {})
                df, all_pass = build_validation_table(ref_metrics_dict, py_metrics)

                # 指标卡片
                metric_cols = st.columns(3)
                with metric_cols[0]:
                    st.metric("测试指标数", len(df))
                with metric_cols[1]:
                    st.metric("通过数", (df["状态"] == "通过").sum())
                with metric_cols[2]:
                    st.metric("失败数", (df["状态"] == "失败").sum())

                if all_pass:
                    st.success("✅ 验证通过：所有指标相对差 ≤ 1%")
                else:
                    st.error("❌ 验证失败：部分指标超出容差")
                st.dataframe(df, use_container_width=True)
                if df.empty:
                    st.info("该参考数据集未提供可比对指标，可在 stata_reference.json 中补充 reference 字段。")

    # ─────────────────────────────────────────────────────────────
    # 真实 Stata 输出比对（不依赖预设参考数据集）
    # ─────────────────────────────────────────────────────────────
    with st.expander("🖥️ 真实 Stata 输出比对（点击展开）", expanded=False):
        st.markdown(
            """
            这里可以直接调用你本地安装的 Stata，或上传 Stata 运行后的 `.log`/`.txt` 输出文件，
            与「Python · 输出」中的复现结果逐项比对。
            """
        )

        current_code = st.session_state.get("stata_code", "")
        detected_path = find_stata_executable()

        stata_path = st.text_input(
            "Stata 可执行文件路径（留空则自动检测）",
            value=detected_path or "",
            placeholder="例如 /Applications/Stata/StataSE.app/Contents/MacOS/StataSE",
        )

        run_real_stata = st.button("▶️ 调用 Stata 运行当前脚本", use_container_width=True)

        if run_real_stata:
            if not current_code.strip():
                st.warning("请先在「Stata · 脚本输入」区域输入 Stata 代码")
            else:
                with st.spinner("正在调用 Stata 执行..."):
                    sr = run_stata_do(current_code, stata_path=stata_path)
                    if sr["success"]:
                        st.success(f"Stata 执行成功：{sr['stata_path']}")
                        st.session_state["last_stata_log"] = sr["log"]
                    else:
                        st.error(f"Stata 调用失败：{sr.get('error') or '未知错误'}")
                        if sr.get("log"):
                            st.code(sr["log"], language="text")
                        _render_stata_fallback_help()

        st.markdown("<div style='text-align:center;margin:12px 0;color:#6B7280;'>— 或 —</div>", unsafe_allow_html=True)

        uploaded_log = st.file_uploader(
            "上传 Stata 输出文件（.log / .txt）",
            type=["log", "txt"],
            accept_multiple_files=False,
            label_visibility="collapsed",
        )
        if uploaded_log is not None:
            st.session_state["last_stata_log"] = uploaded_log.read().decode("utf-8", errors="ignore")
            st.success("已上传 Stata 输出文件")

        # 比对逻辑
        if "last_stata_log" in st.session_state and st.session_state["last_stata_log"]:
            stata_metrics = extract_stata_metrics(st.session_state["last_stata_log"])
            if not stata_metrics:
                st.warning("未能从 Stata 输出中解析到指标。请确认输出中包含 Pooled ES、95% CI、I-squared 等字段。")
            else:
                py_metrics = _get_current_python_metrics()
                if py_metrics is None:
                    st.info("请先点击「转译 → Python」生成并执行 Python 代码，再进行比对。")
                else:
                    df, all_pass = build_validation_table(stata_metrics, py_metrics)
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("测试指标数", len(df))
                    with c2:
                        st.metric("通过数", (df["状态"] == "通过").sum())
                    with c3:
                        st.metric("失败数", (df["状态"] == "失败").sum())

                    if all_pass:
                        st.success("✅ 与真实 Stata 输出一致：所有指标相对差 ≤ 1%")
                    else:
                        st.error("❌ 与真实 Stata 输出存在差异")
                    st.dataframe(df, use_container_width=True)

            with st.expander("查看原始 Stata 输出"):
                st.code(st.session_state["last_stata_log"], language="text")


def _render_stata_fallback_help() -> None:
    """当未检测到 Stata 时，给出可落地的调用方案。"""
    st.markdown(
        """
        **当前环境未检测到 Stata。以下是几种可行的调用方案，你可以任选其一协助配置：**

        1. **本地安装 Stata（推荐）**
           - 在 macOS/Windows/Linux 上安装 Stata/SE、Stata/MP 或 Stata/BE。
           - macOS 典型路径：
             `/Applications/Stata/StataSE.app/Contents/MacOS/StataSE`
           - 安装后刷新页面，系统会自动识别。

        2. **手动指定 Stata 路径**
           - 在上方输入框中填写 Stata 可执行文件的绝对路径，再点击「调用 Stata 运行当前脚本」。

        3. **远程/服务器 Stata**
           - 如果你有一台已安装 Stata 的服务器，可通过 SSH 执行 `.do` 文件后，把 `.log` 文件下载到本地。
           - 然后使用本面板的「上传 Stata 输出文件」功能进行比对。

        4. **先在本机运行 Stata 再上传结果**
           - 在本地 Stata 中执行输入框里的代码，复制输出结果保存为 `.txt` 或 `.log`。
           - 直接上传该文件，平台会解析其中的指标并与 Python 复现结果比对。
        """
    )


def _get_current_python_metrics() -> MetaMetrics | None:
    """从最近一次 Python 执行输出中提取指标（支持单条与批量模式）。"""
    exec_result = st.session_state.get("last_exec")
    if exec_result is None:
        return None
    if isinstance(exec_result, list):
        for ex in exec_result:
            if ex and ex.get("success"):
                return extract_metrics_from_output(ex["stdout"])
        return None
    if exec_result.get("success"):
        return extract_metrics_from_output(exec_result["stdout"])
    return None


def main() -> None:
    inject_academic_css()

    # 顶部横向配置栏（替代左侧侧边栏）
    (
        model_label,
        tau2_label,
        confidence_level,
        eform,
        mode_label,
        uploaded_file,
        example_options,
        example_title,
        load_example,
    ) = render_top_config_bar()

    render_header()

    # 文件上传处理
    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_hash = hashlib.md5(file_bytes).hexdigest()
        if st.session_state.get("last_upload_hash") != file_hash:
            try:
                st.session_state["stata_code"] = file_bytes.decode("utf-8")
                st.session_state["last_upload_hash"] = file_hash
            except Exception as e:
                st.error(f"文件读取失败: {e}")

    # 示例加载
    if load_example:
        selected_example = example_options.get(example_title)
        if selected_example:
            st.session_state["stata_code"] = selected_example["stata_code"]
        else:
            st.warning("请先选择一个示例")

    options = build_backend_options(model_label, tau2_label, confidence_level, eform, mode_label)

    # 第一栏：Stata · 脚本输入
    stata_code, translate_clicked = render_input_panel()

    st.markdown("<hr>", unsafe_allow_html=True)

    # 第二栏：Python · 输出
    if translate_clicked:
        if not stata_code.strip():
            st.warning("请输入 Stata 代码")
        else:
            with st.spinner("正在转译并执行..."):
                result, exec_result = run_translation(stata_code, options)
                st.session_state["last_result"] = result
                st.session_state["last_exec"] = exec_result

    result = st.session_state.get("last_result")
    exec_result = st.session_state.get("last_exec")
    render_output_panel(result, exec_result)

    st.markdown("<hr>", unsafe_allow_html=True)

    # 第三栏：验证对照
    render_validation_panel()


if __name__ == "__main__":
    main()
