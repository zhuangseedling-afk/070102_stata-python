# MetaFlow 项目汇报材料

> Stata Meta-Analysis → Python 翻译器（规则匹配优先 + LLM 兜底）

---

## 一、网页功能介绍

MetaFlow 是一个面向医学/循证医学研究者的在线工具，核心目标是把 Stata 的 meta 分析命令一键转译为可执行的 Python 代码，并验证其计算结果与 Stata 官方输出的一致性。

### 1.1 当前界面布局

页面采用**学术期刊风格**的垂直三栏布局：

| 区域 | 名称 | 功能 |
|------|------|------|
| 顶部 | 配置面板 | 分析模型、τ² 估计量、置信水平、eform、转译模式、文件上传、内置示例 |
| I | Stata · 脚本输入 | 输入 Stata meta 命令，支持 `input/end` 内联数据 |
| II | Python · 输出 | 生成代码、执行输出、转译日志三 Tab 展示 |
| III | 验证对照 | 选择 Stata 参考数据集，逐项对比效应量、CI、I²、Q、τ² 等指标 |

### 1.2 核心交互流程

1. 用户在 **I 区**输入或加载 Stata 代码；
2. 顶部配置面板选择模型与统计选项；
3. 点击 **「🔄 转译 → Python」**；
4. 后台规则引擎生成 Python 代码；
5. 沙箱执行并返回结果到 **II 区**；
6. 用户可在 **III 区**与 Stata 参考值做精度验证。

---

## 二、项目迭代与优化历程

### 2.1 第一阶段：项目整理与 Streamlit Cloud 部署

- 清理杂乱文件，建立可上传的 Streamlit 包结构；
- 确定以 `app.py` 为唯一入口，删除 FastAPI/React 分离架构；
- 配置 `requirements.txt`、`.streamlit/config.toml`、`.gitignore`。

### 2.2 第二阶段：核心翻译引擎建设

- 构建 `backend/engine/rule_engine.py` 规则引擎；
- 支持 `metan`、`metaprop`、`metareg`、`funnel`、`forest`、`meta` 等主命令；
- 实现 7 种 τ² 估计量（DL / REML / ML / Hedges / SJ / HS / EB）和 3 种模型（RE / FE / CE）；
- 支持 2 变量（ES+SE）、4 变量（ES+LCI+UCI）、6 变量（原始均值/标准差）等多种数据格式；
- 引入 `backend/sandbox/executor.py` 子进程沙箱执行，30 秒超时隔离。

### 2.3 第三阶段：规范化层与精度优化

- 增加 `normalize_parsed_command` 规范化层，统一 Stata 命令的各种等价写法：
  - `random` / `randomi` → `DL`
  - `fixed` / `fixedi` → `FE`
  - `common` → `CE`
  - `effect(or)` → `odds_ratio`
  - `lcols(...)` → `label_cols`
- 修正 Mantel-Haenszel OR 方差公式括号问题；
- 6 变量原始数据格式直接计算 MD 与 SE，避免由 CI 反推带来的精度损失；
- 建立 `stata_reference.json` 参考数据集与验证流程。

### 2.4 第四阶段：UI 迭代优化

| 阶段 | 设计风格 | 关键变化 |
|------|----------|----------|
| v1 | 基础 Streamlit | 左侧边栏配置，左右两栏输入输出 |
| v2 | SaaS 科技感 | 深蓝渐变背景、霓虹青紫、玻璃态卡片、顶部横向配置栏 |
| v3 | 极简宽松布局 | 顶部配置栏改为两排四列宽松排版，主内容改为垂直三栏 |
| v4 | 学术期刊风 | 米白纸纹背景、藏蓝+金色、Crimson Text 衬线字体、章节编号 I/II/III |

### 2.5 当前状态

- 入口：`app.py`（Streamlit）
- 部署目标：Streamlit Cloud
- 翻译引擎：规则优先 + LLM 兜底
- 验证机制：与 Stata 参考值对比，容差 1%

---

## 三、系统架构图

```mermaid
flowchart TB
    subgraph UI["Streamlit 前端层"]
        A[app.py]
        A1[顶部配置面板]
        A2[I · Stata 脚本输入]
        A3[II · Python 输出]
        A4[III · 验证对照]
    end

    subgraph Engine["翻译引擎层"]
        B[backend/engine/rule_engine.py]
        B1[parse_stata_code 解析器]
        B2[normalize_parsed_command 规范化层]
        B3[generate_python_code 代码生成器]
        C[backend/engine/rules/]
        C1[metan.py]
        C2[metaprop.py]
        C3[metareg.py]
        C4[funnel.py]
        C5[forest.py]
        D[backend/engine/llm_parser.py]
    end

    subgraph Exec["执行与验证层"]
        E[backend/sandbox/executor.py]
        F[backend/comparator/metrics.py]
        G[backend/comparator/differ.py]
    end

    subgraph Data["数据层"]
        H[backend/data/examples.py]
        I[stata_reference.json]
    end

    A --> B
    A1 --> A
    A2 --> A
    A3 --> A
    A4 --> A

    B --> B1
    B1 --> B2
    B2 --> B3
    B3 --> C
    C --> C1
    C --> C2
    C --> C3
    C --> C4
    C --> C5
    B3 -. 规则未命中 .-> D
    D -.-> B3

    B3 --> E
    E --> F
    F --> G
    G --> A3
    G --> A4

    H --> A2
    I --> A4
```

---

## 四、核心时序图

### 4.1 Stata → Python 转译与执行主流程

```mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant UI as Streamlit app.py
    participant RE as rule_engine.py
    participant RL as rules/*.py
    participant LLM as llm_parser.py
    participant SB as sandbox/executor.py
    participant CP as comparator
    participant Ref as stata_reference.json

    U->>UI: 输入 Stata 代码 + 配置选项
    U->>UI: 点击「转译 → Python」
    UI->>RE: translate_stata(stata_code, options)
    RE->>RE: parse_stata_code()
    RE->>RE: normalize_parsed_command()
    RE->>RL: 选择对应规则模板
    alt 规则命中
        RL-->>RE: 返回 Python 代码模板
    else 规则未命中
        RE->>LLM: llm_parse_and_translate()
        LLM-->>RE: 返回兜底代码
    end
    RE-->>UI: TranslationResult
    UI->>SB: execute_python_code(python_code)
    SB->>SB: 写入临时文件
    SB->>SB: subprocess 执行（30s 超时）
    SB-->>UI: 执行结果 stdout/stderr
    UI->>CP: extract_metrics_from_output()
    UI->>UI: 展示生成代码与执行结果

    U->>UI: 选择参考数据集并运行验证
    UI->>Ref: 读取参考 Stata 代码与参考值
    UI->>RE: 重新转译参考数据集
    UI->>SB: 沙箱执行
    UI->>CP: compare_metrics(参考值, Python 输出值)
    CP-->>UI: 通过/失败 + 逐项对比表
```

### 4.2 规则引擎内部处理流程

```mermaid
sequenceDiagram
    autonumber
    participant In as 输入 Stata 代码
    participant P as parse_stata_code
    participant V as 变量提取
    participant O as _parse_options
    participant N as normalize_parsed_command
    participant M as 模型语义映射
    participant G as generate_python_code
    participant T as 模板选择
    participant Out as 输出 Python 代码

    In->>P: 去除注释与空行
    P->>P: 识别 input/end 数据块
    P->>V: 提取 effect_size / se / lci / uci 等列
    P->>O: 拆分变量部分与选项部分
    O->>O: 提取 random/fixed/common/reml/ml 等原始关键字
    O->>O: 提取 forest/funnel/by/lcols/effect 等选项
    O->>N: 规范化等价写法
    N->>N: random/randomi → DL
    N->>N: fixed/fixedi → FE
    N->>N: common → CE
    N->>N: effect(or) → odds_ratio
    N->>N: lcols → label_cols
    N->>M: RE + τ² 估计量 → DL/REML/ML
    M->>G: UI 选项覆盖解析结果
    G->>T: 根据命令类型选择模板
    T->>T: metan 2变量 / 4变量 CI / 6变量 / by 分组
    T->>T: metaprop / metareg / funnel / forest
    T->>Out: 字符串替换占位符并输出
```

---

## 五、技术栈

| 层级 | 技术 |
|------|------|
| 前端 UI | Streamlit + 自定义 CSS（学术期刊风格） |
| 后端引擎 | Python 3.9+ |
| 科学计算 | numpy、scipy、statsmodels、pandas、matplotlib |
| 规则引擎 | 结构化字典 + 模板字符串替换 |
| LLM 兜底 | backend/engine/llm_parser.py（可选） |
| 沙箱执行 | subprocess + tempfile + 30s 超时 |
| 验证对比 | 自定义 metrics/differ 模块 |
| 部署 | Streamlit Cloud |

---

## 六、关键设计亮点

1. **规则优先，LLM 兜底**：80% 常见 Stata meta 命令通过结构化规则直接映射，保证可解释性与稳定性；未命中时启用 LLM。
2. **规范化层**：统一 Stata 命令的多种等价写法，避免规则膨胀。
3. **精度优先**：6 变量原始数据直接计算，避免 CI 反推 SE 的精度损失。
4. **沙箱隔离**：生成代码在独立子进程执行，30 秒超时，限制输出大小。
5. **可验证性**：内置 Stata 参考数据集，逐项对比 effect size、CI、I²、Q、τ²，容差 1%。
6. **学术风格 UI**：米白纸纹、藏蓝主色、金色点缀、衬线字体，符合学术场景审美。

---

## 七、文件职责总览

| 文件 | 职责 |
|------|------|
| `app.py` | Streamlit 页面渲染、状态管理、CSS 主题注入 |
| `backend/engine/rule_engine.py` | Stata 解析、规范化、代码生成主入口 |
| `backend/engine/rules/*.py` | 各命令的算法模板与实现 |
| `backend/engine/llm_parser.py` | 规则未命中时的 LLM 兜底解析 |
| `backend/sandbox/executor.py` | 临时文件 + subprocess 沙箱执行 |
| `backend/sandbox/security.py` | 代码安全检测 |
| `backend/comparator/metrics.py` | 从 stdout 提取 pooled_effect / CI / I² / Q / τ² 等 |
| `backend/comparator/differ.py` | 相对差计算与通过/失败判定 |
| `backend/data/examples.py` | 内置 Stata 示例 |
| `stata_reference.json` | Stata 官方参考数据集与参考值 |
| `.streamlit/config.toml` | Streamlit 主题配置 |
| `requirements.txt` | 依赖清单 |
