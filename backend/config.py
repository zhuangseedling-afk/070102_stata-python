"""全局配置"""
import os

# 沙箱配置
SANDBOX_TIMEOUT = 30          # 秒
SANDBOX_MAX_MEMORY_MB = 512

# 迭代修正
MAX_FIX_ITERATIONS = 3
DIFF_THRESHOLD = 0.01         # 1% 差异即视为不一致

# LLM 配置（可选）
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_BASE = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

# 服务
HOST = "0.0.0.0"
PORT = 8000