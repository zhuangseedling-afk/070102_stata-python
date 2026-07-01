"""内置示例：Stata Meta 分析代码 → Python 转换"""
from __future__ import annotations
EXAMPLES = [
    {
        "id": "ex1",
        "title": "metan — 二分类结局（OR）随机效应",
        "description": "使用 metan 命令对 5 项研究的 OR 进行随机效应 Meta 分析",
        "stata_code": '''* Example 1: Meta-analysis of OR with random effects
input study es se
1 0.8 0.3
2 1.2 0.4
3 0.6 0.2
4 1.5 0.5
5 0.9 0.35
end
metan es se, random''',
        "tags": ["metan", "random", "OR"],
        "expected_metrics": {
            "pooled_effect": 0.95,
            "i_squared": 40.0,
            "model": "DL",
        }
    },
    {
        "id": "ex2",
        "title": "metan — 连续结局（SMD）固定效应",
        "description": "使用 metan 命令对连续结局 SMD 进行固定效应 Meta 分析",
        "stata_code": '''* Example 2: Meta-analysis of SMD with fixed effect
input study es se
1 0.45 0.15
2 0.52 0.18
3 0.38 0.12
4 0.61 0.20
5 0.49 0.16
6 0.55 0.14
end
metan es se, fixed texts(180)''',
        "tags": ["metan", "fixed", "SMD"],
        "expected_metrics": {
            "pooled_effect": 0.50,
            "i_squared": 0.0,
            "model": "FE",
        }
    },
    {
        "id": "ex3",
        "title": "metan — 使用CI列（es lci uci）",
        "description": "使用 metan 命令，通过效应量 + 置信区间进行 Meta 分析",
        "stata_code": '''* Example 3: Meta-analysis with CI columns
input study es lci uci
1 1.25 0.85 1.65
2 0.92 0.62 1.22
3 1.48 1.08 1.88
4 0.78 0.45 1.11
end
metan es lci uci, random lcols(study)''',
        "tags": ["metan", "CI", "random"],
        "expected_metrics": {
            "pooled_effect": 1.10,
            "model": "DL",
        }
    },
    {
        "id": "ex4",
        "title": "metaprop — 率的Meta分析",
        "description": "使用 metaprop 命令进行率的随机效应 Meta 分析",
        "stata_code": '''* Example 4: Meta-analysis of proportions
input study events total
1 15 100
2 22 120
3 10 80
4 18 95
5 25 150
end
metaprop events total, random''',
        "tags": ["metaprop", "random", "proportion"],
        "expected_metrics": {
            "pooled_effect": 0.15,
            "model": "DL",
        }
    },
    {
        "id": "ex5",
        "title": "funnel — 漏斗图 + Egger检验",
        "description": "使用 funnel 命令绘制漏斗图并输出 Egger 检验结果",
        "stata_code": '''* Example 5: Funnel plot with Egger test
input study es se
1 0.3 0.2
2 0.5 0.3
3 0.4 0.15
4 0.6 0.4
5 0.2 0.1
6 0.55 0.35
end
funnel es se''',
        "tags": ["funnel", "egger", "plot"],
        "expected_metrics": {
            "pooled_effect": 0.42,
        }
    },
    {
        "id": "ex6",
        "title": "metareg — Meta回归",
        "description": "使用 metareg 进行 Meta 回归分析",
        "stata_code": '''* Example 6: Meta-regression
input study es se year
1 0.8 0.3 2010
2 1.2 0.4 2012
3 0.6 0.2 2014
4 1.5 0.5 2016
5 0.9 0.35 2018
end
metareg es se, wsse(se)''',
        "tags": ["metareg", "regression"],
        "expected_metrics": {
            "model": "DL",
        }
    },
    {
        "id": "ex7",
        "title": "forest — 森林图",
        "description": "使用 forest 命令绘制森林图",
        "stata_code": '''* Example 7: Forest plot
input study es lci uci
1 1.2 0.8 1.6
2 0.9 0.6 1.3
3 1.5 1.0 2.0
4 0.7 0.4 1.1
5 1.1 0.7 1.5
end
forest es lci uci, lcols(study)''',
        "tags": ["forest", "plot"],
        "expected_metrics": {
            "pooled_effect": 1.08,
        }
    },
    {
        "id": "ex8",
        "title": "metan — 大规模研究（高异质性）",
        "description": "10 项研究的高异质性随机效应 Meta 分析",
        "stata_code": '''* Example 8: Large study with high heterogeneity
input study es se
1 0.5 0.15
2 1.8 0.40
3 0.3 0.10
4 2.1 0.50
5 0.7 0.20
6 1.3 0.30
7 0.4 0.12
8 1.9 0.45
9 0.6 0.18
10 2.5 0.55
end
metan es se, random''',
        "tags": ["metan", "random", "high_heterogeneity"],
        "expected_metrics": {
            "pooled_effect": 1.21,
            "i_squared": 85.0,
            "model": "DL",
        }
    },
    {
        "id": "ex9",
        "title": "metan — 6变量原始数据格式（MD）",
        "description": "使用6变量格式 (ne meane sde nc meanc sdc) 从原始数据直接计算均数差MD",
        "stata_code": '''* Example 9: 6-variable format for MD from raw data
input ne meane sde nc meanc sdc
30 5.2 1.8 28 3.8 1.5
25 4.8 1.6 30 4.0 1.4
40 6.1 2.0 35 4.5 1.7
22 4.5 1.3 24 3.2 1.1
35 5.8 1.9 32 4.2 1.6
end
metan ne meane sde nc meanc sdc, random effect(md)''',
        "tags": ["metan", "random", "MD", "6-variable", "raw_data"],
        "expected_metrics": {
            "model": "DL",
        }
    },
    {
        "id": "ex10",
        "title": "metan — 6变量格式 + by()分组 + label",
        "description": "使用6变量格式按drug分组进行亚组分析，含研究标签",
        "stata_code": '''* Example 10: 6-variable format with by(drug) and label(namevar=author)
input author ne meane sde nc meanc sdc drug year
Smith 30 5.2 1.8 28 3.8 1.5 A 2020
Jones 25 4.8 1.6 30 4.0 1.4 A 2019
Brown 40 6.1 2.0 35 4.5 1.7 B 2021
Davis 22 4.5 1.3 24 3.2 1.1 A 2020
Wilson 35 5.8 1.9 32 4.2 1.6 B 2022
Lee 28 5.0 1.5 26 3.6 1.3 B 2021
end
metan ne meane sde nc meanc sdc, random effect(md) by(drug) label(namevar=author) lcols(author year)''',
        "tags": ["metan", "random", "MD", "6-variable", "by", "subgroup", "label"],
        "expected_metrics": {
            "model": "DL",
        }
    },
]


def get_example_by_id(example_id: str) -> dict | None:
    for ex in EXAMPLES:
        if ex["id"] == example_id:
            return ex
    return None


def get_all_examples() -> list[dict]:
    return [{"id": e["id"], "title": e["title"], "description": e["description"],
             "tags": e["tags"]} for e in EXAMPLES]