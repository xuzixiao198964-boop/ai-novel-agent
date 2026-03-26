# -*- coding: utf-8 -*-
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """应用配置"""
    # 服务器
    host: str = "0.0.0.0"
    port: int = 9000
    # 数据目录（部署时可挂载）
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    memory_dir: Path = Path(__file__).resolve().parents[2] / "memory"
    # 大模型（可选，后续接真实 API）
    # 统一采用“OpenAI兼容接口”最通用：
    # - 本地模型：vLLM / Ollama(OpenAI兼容) / LM Studio / Text Generation WebUI(OpenAI扩展) 等
    # - 云端：阿里百炼(Qwen) / 火山方舟 / 智谱 / OpenAI / DeepSeek 等（若提供兼容接口）
    llm_provider: str = "openai_compatible"  # openai_compatible / openclaw
    llm_api_base: str = ""   # 例: http://127.0.0.1:8001/v1
    llm_api_key: str = ""    # 例: sk-xxxx
    llm_model: str = ""      # 例: qwen2.5-72b-instruct / gpt-4o-mini 等
    mock_llm: bool = False   # True 时用桩数据不调真实 API，用于部署/流程验证

    # 趋势/爬虫（可选）：若使用第三方搜索或代理，可配置
    serpapi_key: str = ""          # SerpAPI（可选）
    proxy_url: str = ""            # HTTP/HTTPS 代理（可选）

    # 小说规模：章节数由大纲决定，100–500 章，每章不少于 10000 字
    chapter_range_min: int = 100       # 大纲建议最少章数
    chapter_range_max: int = 500        # 大纲建议最多章数
    words_per_chapter: int = 10000      # 每章不少于字数（字）
    total_chapters: int = 0            # 0=由大纲/目录决定；测试时可设如 5 跑短篇
    max_chapters_to_write: int = 0     # 0=写满目录；>0 时只写前 N 章（如 50）
    # 单章打分不通过时最大重写轮数（每章写完后打分，不通过则重写该章）
    chapter_score_rewrite_max: int = 3
    # 审计不通过时最大重写轮数（重写问题章及后续）
    audit_rewrite_max: int = 2
    # 限速：避免 CPU 负载过高（秒）
    agent_interval_seconds: float = 1.0  # Agent 与 Agent 之间的间隔
    step_interval_seconds: float = 0.2   # Agent 内部步骤间隔（循环/分段写作等）
    # 资源限制（可选）
    cpu_limit: float = 1.0
    memory_limit_mb: int = 2048
    # 网页刷新间隔（秒）
    web_refresh_interval: int = 30
    # 可选登录密码（空则不需要登录）
    web_password: str = ""
    # 小说站账号：管理员与普通用户（为空则回退到 web_password 兼容旧配置）
    web_admin_password: str = ""
    web_user_password: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
