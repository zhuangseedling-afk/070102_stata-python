# MetaFlow — Stata Meta-Analysis → Python 翻译器

> 规则匹配优先 + LLM 兜底，在线将 Stata meta 分析命令转译为可执行 Python 代码，并验证与 Stata 官方输出的一致性。

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

---

## 在线体验

本项目可直接部署到 [Streamlit Cloud](https://streamlit.io/cloud)：

1. Fork 或上传本仓库到 GitHub；
2. 登录 [Streamlit Cloud](https://streamlit.io/cloud)，点击 **New app**；
3. 选择仓库、分支与主文件 `app.py`；
4. 点击 **Deploy**。

Streamlit Cloud 会自动读取仓库根目录的 `requirements.txt` 与 `runtime.txt` 完成环境构建。部署前请确保这两个文件已提交并推送到对应仓库。

## 部署常见问题

### `ModuleNotFoundError: No module named 'scipy'`

如果部署后看到类似 `from scipy import stats` 的导入错误，说明 Streamlit Cloud 没有成功安装依赖。请按以下顺序排查：

1. **确认文件已推送**  
   在 GitHub 仓库根目录检查是否存在 `requirements.txt`，并包含 `scipy`：
   ```text
   scipy>=1.10.0
   ```
   若缺少，请将本地 `requirements.txt` 与 `runtime.txt` 一并提交并推送。

2. **确认部署来源正确**  
   Streamlit Cloud 报错日志中的路径（如 `/mount/src/xxx/`）应与你推送的仓库名一致。若不一致，请在 Cloud 控制台重新选择正确的仓库/分支。

3. **强制重新构建环境**  
   进入 Cloud 控制台 → 点击应用右下角 **Manage app** → 选择 **Reboot**。这会触发 pip 重新安装 `requirements.txt` 中的依赖。

4. **查看构建日志**  
   在 **Manage app → Logs** 中确认是否有 `Collecting scipy` 与 `Successfully installed` 字样。若 pip 安装失败，日志会给出具体原因（如网络、版本冲突等）。

### 页面样式与本地不一致

Streamlit Cloud 会读取 `.streamlit/config.toml`。若主题未生效，请确认该文件已推送，且内容包含 `[theme]` 与 `[server]` 段落。

### 真实 Stata 调用在云端不可用

Streamlit Cloud 的运行环境未预装 Stata，因此「调用 Stata 运行当前脚本」按钮在云端会提示未找到 Stata。云端用户请使用「上传 Stata 输出文件」功能进行结果比对。

---

## 功能亮点

- **规则引擎**：覆盖 `metan`、`metaprop`、`metareg`、`funnel`、`forest`、`meta` 等常用 Stata meta 命令。
- **多种数据格式**：支持 2 变量（ES+SE）、3 变量（ES+LCI+UCI）、4 变量、6 变量原始均值/标准差等输入。
- **模型与估计量**：支持 FE / RE / CE 模型，7 种 τ² 估计量（DL / REML / ML / Hedges / SJ / HS / EB）。
- **批量处理**：可一次性解析 `.do` 文件中的多条命令。
- **沙箱执行**：生成代码在独立子进程中运行，30 秒超时，保证安全。
- **验证对照**：内置 Stata 参考数据集，逐项对比合并效应、CI、I²、Q、τ² 等指标（容差 1%）。
- **真实 Stata 比对**：支持调用本地 Stata 或上传 `.log`/`.txt` 输出文件进行比对。
- **学术风格 UI**：米白纸纹、藏蓝主色、金色点缀，符合学术期刊审美。

---

## 本地运行

```bash
# 1. 克隆仓库
cd /path/to/0629_stata-python

# 2. 创建虚拟环境（推荐 Python 3.11）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动 Streamlit
streamlit run app.py
```

默认打开 http://localhost:8501。

---

## 目录结构

```text
.
├── app.py                      # Streamlit 主入口
├── requirements.txt            # Python 依赖
├── runtime.txt                 # Streamlit Cloud Python 版本
├── .streamlit/config.toml      # Streamlit 主题配置
├── stata_reference.json        # Stata 参考数据集
├── backend/
│   ├── engine/                 # 规则引擎与 LLM 兜底
│   │   ├── rule_engine.py
│   │   ├── llm_parser.py
│   │   └── rules/              # metan / metaprop / metareg / funnel / forest / meta
│   ├── sandbox/                # 子进程沙箱执行
│   │   ├── executor.py
│   │   └── security.py
│   ├── comparator/             # 指标提取与差异对比
│   │   ├── metrics.py
│   │   └── differ.py
│   ├── data/                   # 内置示例
│   │   └── examples.py
│   ├── corrector/              # 自动修正（预留）
│   └── stata_runner.py         # 本地 Stata 调用与日志解析
└── docs/                       # 项目汇报与业务说明文档
    ├── PROJECT_REPORT.md
    └── business_process.md
```

---

## 环境变量（可选）

| 变量名 | 说明 |
|--------|------|
| `LLM_API_KEY` | OpenAI 兼容接口的 API Key，用于规则未命中时的 LLM 兜底。不配置时 LLM 兜底自动跳过，不影响主流程。 |
| `LLM_API_BASE` | 自定义 LLM 接口地址，默认 `https://api.openai.com/v1`。 |
| `LLM_MODEL` | 模型名称，默认 `gpt-4o-mini`。 |

在 Streamlit Cloud 中，请通过 **Settings → Secrets** 配置这些变量。

---

## 使用说明

1. 在 **Stata · 脚本输入** 区域输入或粘贴 Stata meta 分析代码（支持 `input ... end` 内联数据）。
2. 在顶部 **配置面板** 选择模型、τ² 估计量、置信水平等选项。
3. 点击 **🔄 转译 → Python**，在 **Python · 输出** 区域查看生成代码与执行结果。
4. 在 **验证对照** 区域选择参考数据集或上传真实 Stata 输出，进行指标比对。

---

## 注意事项

- **真实 Stata 调用**：Streamlit Cloud 默认未安装 Stata，因此「调用 Stata 运行当前脚本」功能仅在本地或已安装 Stata 的服务器可用。云端用户可使用「上传 Stata 输出文件」进行比对。
- **LLM 兜底**：不配置 `LLM_API_KEY` 时，系统会返回规则未命中的提示，不会调用外部接口。

---

## 许可

本项目为教学与研究用途构建，内部使用请遵循相关 Stata 与第三方库的许可协议。
