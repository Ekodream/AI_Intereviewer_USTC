"""
配置文件 - 集中管理 API 密钥和系统路径
"""

import os
from pathlib import Path


def _load_dotenv_file(dotenv_path: Path) -> None:
    """Load simple KEY=VALUE pairs from .env into process environment."""
    if not dotenv_path.exists():
        return

    for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# Load .env from project root so runtime can use values copied from .env.example.
_load_dotenv_file(Path(__file__).parent / ".env")


def _required_env(name: str) -> str:
    """Read a required environment variable and fail fast if missing."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

# ==================== API 密钥配置 ====================
# StepFun API (用于 TTS 和 ASR) - 8 个 Key 轮询
STEPFUN_API_KEYS = [
    os.getenv("STEPFUN_API_KEY_1", "").strip(),
    os.getenv("STEPFUN_API_KEY_2", "").strip(),
    os.getenv("STEPFUN_API_KEY_3", "").strip(),
    os.getenv("STEPFUN_API_KEY_4", "").strip(),
    os.getenv("STEPFUN_API_KEY_5", "").strip(),
    os.getenv("STEPFUN_API_KEY_6", "").strip(),
    os.getenv("STEPFUN_API_KEY_7", "").strip(),
    os.getenv("STEPFUN_API_KEY_8", "").strip(),
]
STEPFUN_API_KEYS = [k for k in STEPFUN_API_KEYS if k]
if not STEPFUN_API_KEYS:
    raise RuntimeError("Missing StepFun API key. Set STEPFUN_API_KEY_1 at minimum.")

# 兼容旧代码（使用第一个 Key）
STEPFUN_API_KEY = STEPFUN_API_KEYS[0]

# 阿里云 DashScope API (用于 LLM)
DASHSCOPE_API_KEY = _required_env("DASHSCOPE_API_KEY")
DASHSCOPE_API_KEYS = [DASHSCOPE_API_KEY]

# ==================== 模型配置 ====================
# LLM 模型
LLM_MODEL = "qwen-plus"
LLM_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# TTS 模型
TTS_MODEL = "step-tts-mini"
TTS_VOICE = "cixingnansheng"  # 磁性男声

# ASR 模型
ASR_MODEL = "step-asr"
# ==================== 路径配置 ====================
# 项目根目录
BASE_DIR = Path(__file__).parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
RAW_KNOWLEDGE_DIR = DATA_DIR / "raw_knowledge"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"

# 输出目录
OUTPUT_DIR = BASE_DIR / "output"
REPORTS_DIR = OUTPUT_DIR / "reports"
VIDEOS_DIR = OUTPUT_DIR / "videos"
ADVISOR_DOCS_DIR = OUTPUT_DIR / "advisor_docs"
ROOMS_DIR = OUTPUT_DIR / "rooms"
ROOMS_INDEX_FILE = ROOMS_DIR / "rooms.json"

# 临时文件目录
TEMP_DIR = BASE_DIR / "temp_audio"

# ==================== 应用配置 ====================
# 音频采样率
AUDIO_SAMPLE_RATE = 16000

# 最大对话轮数
MAX_CONVERSATION_TURNS = 50

# 流式输出延迟（秒）
STREAM_DELAY = 0.01

# ==================== 初始化目录 ====================
def init_directories():
    """创建必要的目录结构"""
    directories = [
        DATA_DIR,
        OUTPUT_DIR,
        REPORTS_DIR,
        VIDEOS_DIR,
        ADVISOR_DOCS_DIR,
        ROOMS_DIR,
        TEMP_DIR
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    print("✅ 目录初始化完成")

# 自动初始化
if __name__ == "__main__":
    init_directories()
