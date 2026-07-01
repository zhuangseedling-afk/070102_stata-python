# Stata Meta → Python 翻译器 业务流程图

本文档使用业务流程图描述项目从用户输入到结果输出的完整流程，重点说明 **Stata 代码如何被转换为 Python 代码**。

---

## 一、总体业务流程图

```mermaid
flowchart TD
    A[用户打开 Streamlit 页面] --> B[左侧输入 Stata 代码]
    B --> C[侧边栏配置转译选项]
    C --> D[点击 🔄 转译按钮]
    D --> E[调用 translate_stata 进入规则引擎]
    E --> F{规则是否命中}
    F -->|命中| G[生成对应 Python 代码]
    F -->|未命中| H[LLM 兜底解析]
    H --> G
    G --> I[沙箱执行生成的 Python 代码]
    I --> J[右侧显示 Python 代码与执行结果]
    J --> K[用户选择参考数据集]
    K --> L[运行验证对照]
    L --> M[输出逐项指标对比表]
```

---

## 二、Stata → Python 转译核心流程图

这是本项目最核心的业务流程，由 `backend/engine/rule_engine.py` 完成。

```mermaid
flowchart TD
    A["输入 Stata 代码"] --> B["parse_stata_code 解析"]
    B --> B1["去除注释与空行"]
    B --> B2["识别 input/end 数据块"]
    B --> B3["识别主命令 metan/metaprop/metareg/funnel/forest/meta"]
    B --> B4["拆分变量部分与选项部分"]
    B --> C["提取变量列"]

    C --> C1["metan: es se / es se lci uci / ne meane sde nc meanc sdc"]
    C --> C2["metaprop: events total"]
    C --> C3["metareg: 效应量 + 协变量"]
    C --> C4["funnel: es se"]
    C --> C5["forest: es lci uci"]

    C --> D["_parse_options 解析原始选项"]
    D --> D1["模型: random / fixed / reml / ml / common"]
    D --> D2["绘图: forest / funnel"]
    D --> D3["亚组: by"]
    D --> D4["标签: lcols"]
    D --> D5["效应量: effect"]
    D --> D6["其他: sortby / wsse / label"]

    D --> N["normalize_parsed_command 规范化层"]
    N --> N1["random/randomi → DL"]
    N --> N2["fixed/fixedi → FE"]
    N --> N3["common → CE"]
    N --> N4["reml/ml → REML/ML"]
    N --> N5["effect(or) → odds_ratio"]
    N --> N6["lcols → label_cols"]

    N --> E["generate_python_code 生成代码"]
    E --> E1["UI 选项覆盖解析结果"]
    E1 --> E2["从数据行提取列数值"]
    E2 --> E3["选择对应代码模板"]
    E3 --> E4["模板字符串替换变量"]
    E4 --> F["输出 TranslationResult"]

    F --> G["沙箱 execute_python_code 执行"]
    G --> H["提取 MetaMetrics"]
    H --> I["与 Stata 参考值对比"]
```

---

## 三、选项与模型映射子流程

```mermaid
flowchart LR
    A["UI 侧边栏选项"] --> B["模型选择"]
    B --> B1["RE 随机效应"]
    B --> B2["FE 固定效应"]
    B --> B3["CE 公共效应"]

    B1 --> C["τ² 估计量选择"]
    C --> C1["DL / REML / ML / Hedges / SJ / HS / EB"]
    C1 --> D["生成模型字符串"]

    B2 --> D2["model = FE"]
    B3 --> D3["model = CE"]

    D --> E["合并 confidence_level / eform / mode"]
    E --> F["传入 translate_stata"]

    G["Stata 代码原始选项"] --> H["normalize_parsed_command"]
    H --> H1["random/randomi → DL"]
    H --> H2["fixed/fixedi → FE"]
    H --> H3["common → CE"]
    H --> H4["reml → REML"]
    H --> H5["ml → ML"]
    H --> H6["effect(or) → odds_ratio"]
    H --> H7["lcols → label_cols"]
    H --> F
```

### 规范化映射表

| 类型 | 原始写法 | 规范值 |
|------|----------|--------|
| 模型 | `random`, `randomi` | `DL` |
| 模型 | `fixed`, `fixedi` | `FE` |
| 模型 | `common` | `CE` |
| 模型 | `reml` | `REML` |
| 模型 | `ml` | `ML` |
| τ² 估计量 | `dl`, `dersimonian-laird` | `DL` |
| τ² 估计量 | `reml` | `REML` |
| τ² 估计量 | `ml` | `ML` |
| τ² 估计量 | `sj`, `sidik-jonkman` | `SJ` |
| τ² 估计量 | `hs`, `hunter-schmidt` | `HS` |
| τ² 估计量 | `eb`, `empirical-bayes` | `EB` |
| 效应量 | `or` | `odds_ratio` |
| 效应量 | `rr` | `risk_ratio` |
| 效应量 | `rd` | `risk_difference` |
| 效应量 | `md`, `wmd` | `mean_diff` |
| 效应量 | `smd` | `std_mean_diff` |
| 效应量 | `hr` | `hazard_ratio` |
| 选项键 | `lcols` | `label_cols` |
| 选项键 | `rcols` | `right_cols` |
| 选项键 | `xlabel` | `xlim` |
| 选项键 | `texts` | `text_size` |
| 选项键 | `by` | `subgroup` |
| 选项键 | `sortby` | `sort_col` |

---

## 四、Python 代码生成与执行子流程

```mermaid
flowchart TD
    A["解析完成 ParsedStataCommand"] --> B{"命令类型"}
    B -->|"metan 2变量"| C["METAN_RULES 模板"]
    B -->|"metan 4变量 CI"| D["METAN_CI_RULES 模板"]
    B -->|"metan 6变量"| E["METAN_RAW_MD_TEMPLATE 模板"]
    B -->|"metan by()"| F["METAN_BY_TEMPLATE 模板"]
    B -->|"metaprop"| G["METAPROP_RULES 模板"]
    B -->|"metareg"| H["METAREG_RULES 模板"]
    B -->|"funnel"| I["FUNNEL_RULES 模板"]
    B -->|"forest"| J["FOREST_RULES 模板"]

    C --> K["字符串替换占位符"]
    D --> K
    E --> K
    F --> K
    G --> K
    H --> K
    I --> K
    J --> K

    K --> L["生成 py 临时文件"]
    L --> M["subprocess 执行 30秒超时"]
    M --> N{"执行是否成功"}
    N -->|"成功"| O["解析 stdout 提取指标"]
    N -->|"失败"| P["显示错误信息"]
    O --> Q["展示结果与森林图"]
```

---

## 五、验证对照业务流程图

```mermaid
flowchart TD
    A[用户选择参考数据集] --> B[读取 stata_reference.json]
    B --> C[获取该数据集的 Stata 代码与 options]
    C --> D[重新调用 translate_stata]
    D --> E[沙箱执行生成的 Python]
    E --> F[extract_metrics_from_output 提取指标]
    F --> G[compare_metrics 对比参考值]
    G --> H{相对差 ≤ 1%}
    H -->|是| I[✅ 验证通过]
    H -->|否| J[❌ 验证失败]
    I --> K[展示 pandas 对比表]
    J --> K
```

---

## 六、核心计算流程（以 metan 为例）

```mermaid
flowchart TD
    A[读取 es[], se[]] --> B[weights = 1 / se²]
    B --> C[计算异质性 Q / I² / p_hetero]
    C --> D[根据 tau2_estimator 计算 tau²]
    D --> D1[DL / Hedges]
    D --> D2[REML / ML 迭代]
    D --> D3[Sidik-Jonkman]
    D --> D4[Hunter-Schmidt]
    D --> D5[Empirical Bayes 迭代]

    D --> E{模型类型}
    E -->|FE/CE| F[w* = weights, tau²=0]
    E -->|RE| G[w* = 1 / (se² + tau²)]

    F --> H[pooled_es = Σw*·es / Σw*]
    G --> H
    H --> I[se_pooled = √(1 / Σw*)]
    I --> J[ci = pooled_es ± zα·se_pooled]
    J --> K{z_score / p_value}
    K --> L{eform?}
    L -->|是| M[对效应量与 CI 取 exp]
    L -->|否| N[保持原值]
    M --> O[print 结果并保存森林图]
    N --> O
```

---

## 七、关键业务角色与文件对应

| 业务环节 | 负责文件 | 说明 |
|----------|----------|------|
| 页面渲染 | `app.py` | Streamlit 三栏布局、侧边栏、状态管理 |
| 代码解析 | `backend/engine/rule_engine.py` | 解析 Stata 命令、变量、选项 |
| 规则映射 | `backend/engine/rules/*.py` | metan / metaprop / metareg / funnel / forest 模板与算法 |
| LLM 兜底 | `backend/engine/llm_parser.py` | 规则未命中时调用 |
| 安全执行 | `backend/sandbox/executor.py` | 临时文件 + subprocess + 30 秒超时 |
| 指标提取 | `backend/comparator/metrics.py` | 从 stdout 解析 pooled_effect / CI / I² / Q / τ² 等 |
| 差异对比 | `backend/comparator/differ.py` | 计算相对差并判定通过/失败 |
| 参考数据 | `stata_reference.json` | 存储 Stata 官方参考数据集与参考值 |

---

## 八、业务规则摘要

1. **规则优先**：所有已识别的 Stata meta 命令优先通过结构化规则字典映射为 Python 代码。
2. **UI 覆盖代码**：侧边栏中的模型、τ² 估计量、置信水平、eform 等选项可覆盖 Stata 代码中的默认选项。
3. **RE 模型语义映射**：当 UI 选择 RE 时，若 τ² 估计量为 REML/ML 则使用之，否则默认使用 DL。
4. **精度优先**：6 变量原始数据格式直接从原始数据计算 MD 与 SE，避免由 CI 反推带来的精度损失。
5. **沙箱隔离**：所有生成代码在独立子进程中执行，超时 30 秒，防止恶意或异常代码影响主程序。
6. **验证容差**：与 Stata 参考值对比的容差为 1%，逐项展示绝对差与相对差。
