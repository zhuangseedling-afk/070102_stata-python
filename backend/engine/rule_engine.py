"""第一层：规则匹配引擎 — 覆盖 80% 常见 Stata Meta 命令"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from scipy import stats

from .rules.metan import METAN_RULES, METAN_CI_RULES, METAN_RAW_MD_TEMPLATE, METAN_BY_TEMPLATE
from .rules.metaprop import METAPROP_RULES
from .rules.metareg import METAREG_RULES
from .rules.funnel import FUNNEL_RULES
from .rules.forest import FOREST_RULES
from .rules.meta import META_SERIES_RULES


class MetaModel(Enum):
    """规范化的 Meta 分析模型"""
    FIXED = "FE"
    COMMON = "CE"
    RANDOM_DL = "DL"
    RANDOM_REML = "REML"
    RANDOM_ML = "ML"


@dataclass
class ParsedStataCommand:
    """解析后的 Stata 命令结构"""
    command: str = ""
    effect_size_col: str = ""
    se_col: str = ""
    ci_lower_col: str = ""
    ci_upper_col: str = ""
    model: str = "DL"
    label_cols: list[str] = field(default_factory=list)
    subgroup_col: str = ""
    sort_col: str = ""
    forest_plot: bool = False
    funnel_plot: bool = False
    extra_options: dict[str, str] = field(default_factory=dict)
    raw_code: str = ""
    # metaprop 专用
    events_col: str = ""
    total_col: str = ""
    # metareg 专用
    covariates: list[str] = field(default_factory=list)
    # 6-variable 格式 (ne meane sde nc meanc sdc)
    ne_col: str = ""
    meane_col: str = ""
    sde_col: str = ""
    nc_col: str = ""
    meanc_col: str = ""
    sdc_col: str = ""
    # effect measure (e.g. "md", "smd", "or")
    effect_measure: str = ""
    # UI 可覆盖的高级选项
    confidence_level: float = 95.0
    tau2_estimator: str = "DL"  # DL, REML, ML, Hedges, SJ, HS, EB
    eform: bool = False
    translation_mode: str = "single"  # single | batch
    # 数据
    data_lines: list[str] = field(default_factory=list)
    column_names: list[str] = field(default_factory=list)


@dataclass
class TranslationResult:
    """翻译引擎输出"""
    stata_code: str
    python_code: str
    parsed: ParsedStataCommand
    source: str  # "rule_engine" | "llm_parser" | "hybrid"


# 所有规则注册表
COMMAND_REGISTRY = {
    "metan": METAN_RULES,
    "metaprop": METAPROP_RULES,
    "metareg": METAREG_RULES,
    "funnel": FUNNEL_RULES,
    "metafunnel": FUNNEL_RULES,
    "forest": FOREST_RULES,
    "meta": META_SERIES_RULES,
}


def parse_stata_code(stata_code: str) -> ParsedStataCommand:
    """
    解析 Stata 代码，提取命令、变量、选项
    支持内联数据 (input/end) 格式
    """
    lines = [l.strip() for l in stata_code.strip().split("\n") if l.strip() and not l.strip().startswith("*")]
    command = ""
    data_lines = []
    column_names = []
    in_data = False

    for line in lines:
        # 检测数据块
        m = re.match(r'^\s*input\s+(.+)', line)
        if m:
            in_data = True
            column_names = m.group(1).split()
            continue
        if re.match(r'^\s*end\b', line):
            in_data = False
            continue
        if in_data:
            data_lines.append(line)
            continue
        # 找到主命令
        if not command and re.match(r'^\s*(metan|metaprop|metareg|funnel|metafunnel|forest|meta)\b', line):
            command = line

    if not command:
        return ParsedStataCommand(command="unknown", raw_code=stata_code)

    parsed = ParsedStataCommand(raw_code=stata_code, data_lines=data_lines, column_names=column_names)

    # 提取命令名
    cmd_match = re.match(r'^\s*(metan|metaprop|metareg|funnel|metafunnel|forest|meta)\b', command)
    if not cmd_match:
        parsed.command = "unknown"
        return parsed

    parsed.command = cmd_match.group(1)
    cmd_body = command[cmd_match.end():].strip()

    # 分离变量列表和选项（逗号分隔）
    # metan es se, random lcols(...)
    # metaprop events total, random
    parts = cmd_body.split(",")
    var_part = parts[0].strip() if parts else ""
    option_part = ",".join(parts[1:]) if len(parts) > 1 else ""

    # 解析变量
    var_names = var_part.split()
    if parsed.command in ("metan", "metareg"):
        # 6-variable 格式: ne meane sde nc meanc sdc
        if len(var_names) >= 6:
            parsed.ne_col = var_names[0]
            parsed.meane_col = var_names[1]
            parsed.sde_col = var_names[2]
            parsed.nc_col = var_names[3]
            parsed.meanc_col = var_names[4]
            parsed.sdc_col = var_names[5]
        elif len(var_names) >= 2:
            parsed.effect_size_col = var_names[0]
            parsed.se_col = var_names[1]
        # 三变量格式 es lci uci（使用置信区间列）
        if len(var_names) == 3 and not parsed.ne_col:
            parsed.ci_lower_col = var_names[1]
            parsed.ci_upper_col = var_names[2]
            parsed.se_col = ""  # CI 列优先于 SE 列
        elif len(var_names) >= 4 and not parsed.ne_col:
            parsed.ci_lower_col = var_names[2]
            parsed.ci_upper_col = var_names[3]
            parsed.se_col = ""
    elif parsed.command == "metaprop":
        if len(var_names) >= 2:
            parsed.events_col = var_names[0]
            parsed.total_col = var_names[1]
    elif parsed.command == "funnel":
        if len(var_names) >= 2:
            parsed.effect_size_col = var_names[0]
            parsed.se_col = var_names[1]
    elif parsed.command in ("forest", "metafunnel"):
        if len(var_names) >= 3:
            parsed.effect_size_col = var_names[0]
            parsed.ci_lower_col = var_names[1]
            parsed.ci_upper_col = var_names[2]

    # 解析选项
    if option_part:
        parsed = _parse_options(option_part.strip(), parsed)

    return parsed


def _parse_options(opt_str: str, parsed: ParsedStataCommand) -> ParsedStataCommand:
    """解析选项字符串：只提取原始关键字，规范化交给 normalize_parsed_command"""
    opt_str = opt_str.lower().strip()

    # 模型检测 —— 保留原始关键字，便于规范化层统一处理
    if re.search(r'\breml\b', opt_str):
        parsed.model = "reml"
    elif re.search(r'\bml\b', opt_str):
        parsed.model = "ml"
    elif re.search(r'\brandomi?\b', opt_str):
        parsed.model = "random"
    elif re.search(r'\bfixedi?\b', opt_str):
        parsed.model = "fixed"
    elif re.search(r'\bcommon\b', opt_str):
        parsed.model = "common"

    # 绘图
    if re.search(r'\bforest\b', opt_str):
        parsed.forest_plot = True
    if re.search(r'\bfunnel\b', opt_str):
        parsed.funnel_plot = True

    # lcols(label_cols) 提取
    lcols_m = re.search(r'lcols\(([^)]+)\)', opt_str)
    if lcols_m:
        parsed.label_cols = [c.strip() for c in lcols_m.group(1).split()]

    # by(subgroup)
    by_m = re.search(r'\bby\((\w+)\)', opt_str)
    if by_m:
        parsed.subgroup_col = by_m.group(1)

    # sortby()
    sort_m = re.search(r'sortby\((\w+)\)', opt_str)
    if sort_m:
        parsed.sort_col = sort_m.group(1)

    # wsse() — metareg
    wsse_m = re.search(r'\bwsse\((\w+)\)', opt_str)
    if wsse_m:
        parsed.extra_options["wsse"] = wsse_m.group(1)

    # effect(md) — 效应量指标
    effect_m = re.search(r'effect\((\w+)\)', opt_str)
    if effect_m:
        parsed.effect_measure = effect_m.group(1)
        parsed.extra_options["effect"] = effect_m.group(1)

    # label(namevar=author) — 研究标签变量
    label_m = re.search(r'label\(namevar=(\w+)\)', opt_str)
    if label_m:
        parsed.extra_options["label_namevar"] = label_m.group(1)

    # 提取其他形如 key(value) 的选项
    for m in re.finditer(r'(\w+)\(([^)]+)\)', opt_str):
        key = m.group(1)
        if key not in ("lcols", "rcols", "by", "sortby", "wsse", "effect", "label"):
            parsed.extra_options[key] = m.group(2)

    return parsed


# ======================================================================
# 规范化层：统一 Stata 选项的各种等价写法
# ======================================================================

MODEL_KEYWORD_MAP = {
    "random": MetaModel.RANDOM_DL,
    "randomi": MetaModel.RANDOM_DL,
    "fixed": MetaModel.FIXED,
    "fixedi": MetaModel.FIXED,
    "common": MetaModel.COMMON,
    "reml": MetaModel.RANDOM_REML,
    "ml": MetaModel.RANDOM_ML,
}

TAU2_KEYWORD_MAP = {
    "dl": "DL",
    "dersimonian-laird": "DL",
    "reml": "REML",
    "ml": "ML",
    "hedges": "Hedges",
    "sj": "SJ",
    "sidik-jonkman": "SJ",
    "hs": "HS",
    "hunter-schmidt": "HS",
    "eb": "EB",
    "empirical-bayes": "EB",
}

EFFECT_MEASURE_MAP = {
    "": "generic",
    "or": "odds_ratio",
    "rr": "risk_ratio",
    "rd": "risk_difference",
    "smd": "std_mean_diff",
    "md": "mean_diff",
    "wmd": "mean_diff",
    "hr": "hazard_ratio",
}

EXTRA_OPTION_KEY_MAP = {
    "lcols": "label_cols",
    "rcols": "right_cols",
    "xlabel": "xlim",
    "texts": "text_size",
    "by": "subgroup",
    "sortby": "sort_col",
    "nostandard": "no_standard",
    "nowt": "no_weights",
    "nograph": "no_graph",
    "effect": "effect_label",
    "label": "label_name",
    "astext": "annotate_size",
    "boxsca": "box_scale",
    "diamond": "diamond_color",
    # dp 保持原样，模板直接使用 {dp}
    "dp": "dp",
}


def normalize_parsed_command(parsed: ParsedStataCommand) -> ParsedStataCommand:
    """
    规范化层：把 Stata 代码中的各种等价写法统一为规范值。

    例如：
      random / randomi  → DL
      fixed / fixedi    → FE
      common            → CE
      reml              → REML
      ml                → ML
      effect(or)        → odds_ratio
      lcols(...)        → label_cols
    """
    # 1. 模型规范化
    model_raw = str(parsed.model).lower().strip()
    if model_raw in MODEL_KEYWORD_MAP:
        parsed.model = MODEL_KEYWORD_MAP[model_raw].value

    # 2. tau² 估计量规范化
    tau2_raw = str(parsed.tau2_estimator).lower().strip()
    if tau2_raw in TAU2_KEYWORD_MAP:
        parsed.tau2_estimator = TAU2_KEYWORD_MAP[tau2_raw]

    # 3. 若 Stata 代码明确指定 reml/ml，同步 tau² 估计量
    if parsed.model in ("REML", "ML"):
        parsed.tau2_estimator = parsed.model

    # 4. 效应量规范化
    effect_raw = str(parsed.effect_measure).lower().strip()
    if effect_raw in EFFECT_MEASURE_MAP:
        parsed.effect_measure = EFFECT_MEASURE_MAP[effect_raw]

    # 5. extra_options 键名规范化
    normalized_extra: dict[str, str] = {}
    for key, val in parsed.extra_options.items():
        key_lower = str(key).lower().strip()
        normalized_key = EXTRA_OPTION_KEY_MAP.get(key_lower, key_lower)
        normalized_extra[normalized_key] = val
    parsed.extra_options = normalized_extra

    return parsed


def generate_python_code(parsed: ParsedStataCommand, options: dict | None = None) -> tuple[str, str]:
    """
    根据解析结果生成 Python 代码
    返回 (python_code, source)
    """
    options = options or {}
    cmd = parsed.command
    if cmd not in COMMAND_REGISTRY:
        return "", "unknown"

    rule = COMMAND_REGISTRY[cmd]
    # UI 选项优先于 Stata 代码解析结果
    model = options.get("model", parsed.model)
    confidence_level = float(options.get("confidence_level", parsed.confidence_level))
    tau2_estimator = options.get("tau2_estimator", parsed.tau2_estimator)
    eform = bool(options.get("eform", parsed.eform))

    # UI 模型语义映射：RE 随机效应默认使用 DL，除非 tau² 估计量指定为 REML/ML
    if model == "RE":
        model = tau2_estimator if tau2_estimator in ("REML", "ML") else "DL"
    elif model == "FE":
        model = "FE"
    elif model == "CE":
        model = "CE"

    # 构建数据块
    data_block = _build_data_block(parsed, cmd)
    dp = parsed.extra_options.get("dp", "4")

    # 提取变量值
    es_values_str = ""
    se_values_str = ""
    lci_values_str = ""
    uci_values_str = ""
    events_values_str = ""
    totals_values_str = ""
    labels_array_str = "[]"
    # 6-variable 格式
    ne_values_str = ""
    meane_values_str = ""
    sde_values_str = ""
    nc_values_str = ""
    meanc_values_str = ""
    sdc_values_str = ""
    # by() 分组变量值
    subgroup_values_str = ""
    subgroup_name = parsed.subgroup_col

    if parsed.data_lines:
        columns = parsed.column_names if parsed.column_names else [c.strip() for c in parsed.data_lines[0].split()]
        es_col = parsed.effect_size_col
        se_col = parsed.se_col
        lci_col = parsed.ci_lower_col
        uci_col = parsed.ci_upper_col
        events_col = parsed.events_col
        total_col = parsed.total_col
        label_cols = parsed.label_cols
        # 6-variable 列
        ne_col = parsed.ne_col
        meane_col = parsed.meane_col
        sde_col = parsed.sde_col
        nc_col = parsed.nc_col
        meanc_col = parsed.meanc_col
        sdc_col = parsed.sdc_col

        # 数据行（如果没有 column_names，则跳过第一行作为表头）
        data_rows = parsed.data_lines if parsed.column_names else (parsed.data_lines[1:] if len(parsed.data_lines) > 1 else [])
        values = {}
        for col_name in columns:
            values[col_name] = []

        for row in data_rows:
            if not row.strip():
                continue
            vals = row.split()
            for i, col_name in enumerate(columns):
                if i < len(vals):
                    values[col_name].append(vals[i])

        if es_col and es_col in values:
            es_values_str = ", ".join(values[es_col])
        if se_col and se_col in values:
            se_values_str = ", ".join(values[se_col])
        if lci_col and lci_col in values:
            lci_values_str = ", ".join(values[lci_col])
        if uci_col and uci_col in values:
            uci_values_str = ", ".join(values[uci_col])
        if events_col and events_col in values:
            events_values_str = ", ".join(values[events_col])
        if total_col and total_col in values:
            totals_values_str = ", ".join(values[total_col])

        # 6-variable 格式值提取
        if ne_col and ne_col in values:
            ne_values_str = ", ".join(values[ne_col])
        if meane_col and meane_col in values:
            meane_values_str = ", ".join(values[meane_col])
        if sde_col and sde_col in values:
            sde_values_str = ", ".join(values[sde_col])
        if nc_col and nc_col in values:
            nc_values_str = ", ".join(values[nc_col])
        if meanc_col and meanc_col in values:
            meanc_values_str = ", ".join(values[meanc_col])
        if sdc_col and sdc_col in values:
            sdc_values_str = ", ".join(values[sdc_col])

        # by() 分组变量值
        if subgroup_name and subgroup_name in values:
            subgroup_values_str = ", ".join(f'"{v}"' for v in values[subgroup_name])

        # 多列标签拼接
        if label_cols:
            valid_cols = [c for c in label_cols if c in values]
            if valid_cols:
                combined_labels = []
                n_labels = len(values[valid_cols[0]])
                for i in range(n_labels):
                    parts = []
                    for col in valid_cols:
                        if i < len(values[col]):
                            parts.append(values[col][i])
                    combined_labels.append(" ".join(parts))
                labels_array_str = str(combined_labels)
        elif label_cols and label_cols[0] in values:
            labels_array_str = str(values[label_cols[0]])

    # 模板选择
    if cmd == "metan":
        if parsed.ne_col and parsed.subgroup_col:
            template = METAN_BY_TEMPLATE
        elif parsed.ne_col:
            template = METAN_RAW_MD_TEMPLATE
        elif parsed.ci_lower_col and parsed.ci_upper_col:
            template = METAN_CI_RULES["code_template"]
        else:
            template = METAN_RULES["code_template"]
    elif cmd == "metaprop":
        template = METAPROP_RULES["code_template"]
    elif cmd == "metareg":
        template = METAREG_RULES["code_template"]
    elif cmd in ("funnel", "metafunnel"):
        template = FUNNEL_RULES["code_template"]
    elif cmd == "forest":
        template = FOREST_RULES["code_template"]
    elif cmd == "meta":
        template = "# meta command — simplified summary\nprint('Meta summary not yet implemented')\n"
    else:
        return "", "unknown"

    # 填充模板
    model_desc = "Random-effects (DL)" if model == "DL" else "Fixed-effects (Mantel-Haenszel)"
    if model == "REML":
        model_desc = "Random-effects (REML)"
    elif model == "ML":
        model_desc = "Random-effects (ML)"
    elif model == "FE":
        model_desc = "Fixed-effects (Inverse-variance)"
    elif model == "CE":
        model_desc = "Common-effect (Inverse-variance)"

    fig_height = max(3, len(es_values_str.split(",")) * 0.5 if es_values_str else 3)
    z_alpha = stats.norm.ppf(1 - (1 - confidence_level / 100) / 2)

    # 填充模板（使用 replace 避免与 f-string 冲突）
    replacements = {
        "{data_block}": data_block,
        "{es_values}": es_values_str,
        "{se_values}": se_values_str,
        "{lci_values}": lci_values_str,
        "{uci_values}": uci_values_str,
        "{events_values}": events_values_str,
        "{totals_values}": totals_values_str,
        "{model}": model,
        "{model_desc}": model_desc,
        "{dp}": dp,
        "{labels_array}": labels_array_str,
        "{fig_height}": str(fig_height),
        "{covariate_arrays}": "",
        # 6-variable 格式
        "{ne_values}": ne_values_str,
        "{meane_values}": meane_values_str,
        "{sde_values}": sde_values_str,
        "{nc_values}": nc_values_str,
        "{meanc_values}": meanc_values_str,
        "{sdc_values}": sdc_values_str,
        # by() 分组
        "{subgroup_name}": subgroup_name,
        "{subgroup_values}": subgroup_values_str,
        # 高级选项
        "{confidence_level}": str(confidence_level),
        "{z_alpha}": f"{z_alpha:.10f}",
        "{tau2_estimator}": tau2_estimator,
        "{eform}": str(eform),
        "{effect_measure}": parsed.effect_measure or "generic",
    }
    code = template
    for key, val in replacements.items():
        code = code.replace(key, val)

    return code, "rule_engine"


def _build_data_block(parsed: ParsedStataCommand, cmd: str) -> str:
    """构建数据块注释"""
    if not parsed.data_lines:
        return "# (No inline data — using simulated example data)"
    if parsed.column_names:
        return f"# Inline data: {' '.join(parsed.column_names)}"
    return f"# Inline data: {parsed.data_lines[0]}"


def translate_stata(stata_code: str, options: dict | None = None, use_llm: bool = False) -> TranslationResult:
    """
    主入口：翻译 Stata → Python
    第一层：规则引擎（含规范化层）
    第二层：LLM（按需）
    """
    parsed = parse_stata_code(stata_code)
    parsed = normalize_parsed_command(parsed)
    python_code, source = generate_python_code(parsed, options=options)

    if not python_code and use_llm:
        # 第二层：LLM 兜底
        from .llm_parser import llm_parse_and_translate
        result = llm_parse_and_translate(stata_code)
        if result:
            python_code, source = result, "llm_parser"

    return TranslationResult(
        stata_code=stata_code,
        python_code=python_code or "# Unable to translate this Stata code",
        parsed=parsed,
        source=source,
    )


# ----------------------------------------------------------------------
# 批量模式：把 .do 文件中的多行命令切分为独立单元并逐个翻译
# ----------------------------------------------------------------------

_META_COMMAND_RE = re.compile(
    r'^\s*(metan|metaprop|metareg|funnel|metafunnel|forest|meta)\b',
    re.IGNORECASE,
)


def _has_meta_command(buffer: list[str]) -> bool:
    """判断缓冲区中是否已包含可翻译的 meta 主命令"""
    for line in buffer:
        if _META_COMMAND_RE.match(line):
            return True
    return False


def split_stata_batch(stata_code: str) -> list[str]:
    """
    将多行 Stata 代码切分为多个可独立翻译的命令单元。

    每个单元包含：
      - 一个 input ... end 数据块（可选）
      - 一条 metan / metaprop / metareg / funnel / forest / meta 主命令

    不在数据块中的杂项命令（clear / set / gen 等）会被跳过，
    专注于可被规则引擎翻译的 meta 分析命令。
    """
    lines = stata_code.splitlines()
    chunks: list[str] = []
    buffer: list[str] = []
    in_data = False

    for raw_line in lines:
        stripped = raw_line.strip()
        # 跳过空行与注释
        if not stripped or stripped.startswith("*"):
            continue

        # input 开始：开启新的数据块
        if re.match(r'^\s*input\s+', stripped, re.IGNORECASE):
            if buffer and not _has_meta_command(buffer):
                # 之前没有主命令的零散内容丢弃，开始新的命令单元
                buffer = []
            in_data = True
            buffer.append(raw_line)
            continue

        # end 结束数据块
        if re.match(r'^\s*end\s*$', stripped, re.IGNORECASE):
            in_data = False
            buffer.append(raw_line)
            continue

        # 数据行
        if in_data:
            buffer.append(raw_line)
            continue

        # 主命令：把当前缓冲区（数据块 + 命令）作为一个单元输出
        if _META_COMMAND_RE.match(stripped):
            buffer.append(raw_line)
            chunks.append("\n".join(buffer).strip())
            buffer = []
        # 其他非主命令忽略

    return chunks


def translate_stata_batch(
    stata_code: str,
    options: dict | None = None,
    use_llm: bool = False,
) -> list[TranslationResult]:
    """
    批量翻译 Stata 代码。

    若未识别出多个独立命令单元，则退化到单条翻译，保证兼容性。
    """
    chunks = split_stata_batch(stata_code)
    if not chunks:
        return [translate_stata(stata_code, options=options, use_llm=use_llm)]

    results: list[TranslationResult] = []
    for chunk in chunks:
        results.append(translate_stata(chunk, options=options, use_llm=use_llm))
    return results