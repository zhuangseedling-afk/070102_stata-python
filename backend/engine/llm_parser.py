"""
第二层：LLM 语义解析器 — 处理未知/复杂命令
策略：让 LLM 输出结构化 JSON，后端根据 JSON 生成代码
"""
import json
import re
from ..config import LLM_API_KEY, LLM_API_BASE, LLM_MODEL


def llm_parse_to_json(stata_code: str) -> dict | None:
    """
    调用 LLM 将 Stata 命令解析为结构化 JSON
    """
    if not LLM_API_KEY:
        return None

    prompt = f"""请将以下 Stata meta 分析命令解析为结构化 JSON，不要生成代码。

Stata 命令:
{stata_code}

输出格式（严格 JSON）：
{{
  "command": "metan" | "metaprop" | "metareg" | "funnel" | "forest" | "meta" | "unknown",
  "effect_size_col": "es",
  "se_col": "se",
  "ci_lower_col": "lci",
  "ci_upper_col": "uci",
  "model": "FE" | "DL" | "REML" | "ML",
  "label_cols": ["study"],
  "subgroup_col": null,
  "forest_plot": false,
  "funnel_plot": false,
  "extra_options": {{}}
}}

只输出 JSON，不要其他文字。"""

    try:
        import urllib.request
        import urllib.error

        data = json.dumps({
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": "You are a Stata-to-Python parser. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 500,
        }).encode()

        req = urllib.request.Request(
            f"{LLM_API_BASE}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LLM_API_KEY}",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            # 提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
    except Exception:
        pass

    return None


def llm_parse_and_translate(stata_code: str) -> str | None:
    """
    LLM 解析 + 生成 Python 代码
    """
    parsed_json = llm_parse_to_json(stata_code)
    if not parsed_json:
        return None

    # 根据 JSON 构造 ParsedStataCommand 并生成代码
    cmd = parsed_json.get("command", "unknown")
    if cmd == "unknown":
        return None

    # 简单拼接提示让 LLM 直接生成代码作为兜底
    if not LLM_API_KEY:
        return None

    prompt = f"""请将以下 Stata meta 分析翻译为等价的 Python 代码（使用 numpy + scipy/statsmodels）。

Stata 命令:
{stata_code}

要求:
1. 使用 numpy + scipy.stats 实现 Meta 分析
2. 输出合并效应量、95% CI、p值、I²、Q统计量、tau²
3. 打印结果到 stdout
4. 只输出 Python 代码，不要解释

Python 代码:"""

    try:
        import urllib.request
        import json as json_mod

        data = json_mod.dumps({
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": "You are a Stata-to-Python code translator. Output only Python code, no explanations."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1500,
        }).encode()

        req = urllib.request.Request(
            f"{LLM_API_BASE}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LLM_API_KEY}",
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json_mod.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            # 提取代码块
            code_match = re.search(r'```python\n([\s\S]*?)\n```', content)
            if code_match:
                return code_match.group(1)
            return content.strip()
    except Exception:
        return None