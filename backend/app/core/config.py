"""应用配置加载模块。

从 YAML 文件读取配置并解析为强类型的 Pydantic 模型。
优先加载 backend/config/config.yaml；若不存在（例如未填密钥的测试/CI 环境），
回退到 config.example.yaml，保证程序可启动、测试可运行。

配置文件路径可通过环境变量 RAGDEMO_CONFIG 覆盖。
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# backend/ 目录（本文件位于 backend/app/core/config.py）
BACKEND_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BACKEND_DIR / "config"


class AppConfig(BaseModel):
    secret_key: str = "change-me"
    jwt_expire_minutes: int = 1440
    jwt_algorithm: str = "HS256"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


class MySQLConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 3307
    user: str = "legal_user"
    password: str = "legal_pass"
    db: str = "legal_rag"

    @property
    def async_url(self) -> str:
        """SQLAlchemy 异步连接串（aiomysql 驱动）。"""
        return (
            f"mysql+aiomysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}?charset=utf8mb4"
        )


class MilvusConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 19530


class MinioConfig(BaseModel):
    endpoint: str = "127.0.0.1:9200"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "legal-rag"
    secure: bool = False


class DashScopeConfig(BaseModel):
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen-max"
    embedding_model: str = "text-embedding-v3"
    rerank_model: str = "gte-rerank-v2"


class ChatConfig(BaseModel):
    history_rounds: int = 5
    temperature: float = 0.7
    top_p: float = 0.8
    max_tokens: int = 2048


class RagConfig(BaseModel):
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5


class OcrConfig(BaseModel):
    lang: str = "ch"
    use_gpu: bool = False


class Settings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    mysql: MySQLConfig = Field(default_factory=MySQLConfig)
    milvus: MilvusConfig = Field(default_factory=MilvusConfig)
    minio: MinioConfig = Field(default_factory=MinioConfig)
    dashscope: DashScopeConfig = Field(default_factory=DashScopeConfig)
    chat: ChatConfig = Field(default_factory=ChatConfig)
    rag: RagConfig = Field(default_factory=RagConfig)
    ocr: OcrConfig = Field(default_factory=OcrConfig)


def _resolve_config_path() -> Path:
    """确定使用的配置文件路径：环境变量 > config.yaml > config.example.yaml。"""
    env_path = os.getenv("RAGDEMO_CONFIG")
    if env_path:
        return Path(env_path)
    real = CONFIG_DIR / "config.yaml"
    if real.exists():
        return real
    return CONFIG_DIR / "config.example.yaml"


@lru_cache
def get_settings() -> Settings:
    """加载并缓存全局配置对象。"""
    path = _resolve_config_path()
    if not path.exists():
        # 无任何配置文件时使用默认值，保证不崩溃
        return Settings()
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return Settings(**data)
