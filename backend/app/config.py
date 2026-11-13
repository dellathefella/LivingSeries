"""LivingSeries configuration.

Everything is environment-driven so the same service runs against Strata, vLLM XPU, or MLX without
code changes.  The defaults point at the Arc box's vLLM endpoint; set LLM_BASE_URL to Strata's
127.0.0.1:8080/v1 when the TP=4 engine is serving.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # LLM (OpenAI-compatible)
    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", "http://10.0.1.121:8081/v1"))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", "none"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "qwen3.8-27b"))
    llm_timeout_s: float = field(default_factory=lambda: float(_env("LLM_TIMEOUT_S", "120")))
    llm_max_tokens: int = field(default_factory=lambda: int(_env("LLM_MAX_TOKENS", "512")))
    llm_temperature: float = field(default_factory=lambda: float(_env("LLM_TEMPERATURE", "0.8")))

    # Storage
    db_path: Path = field(default_factory=lambda: Path(_env("LS_DB", "data/livingseries.db")))

    # Memory retrieval
    memory_top_k: int = field(default_factory=lambda: int(_env("LS_MEMORY_TOP_K", "8")))
    embedding_dim: int = field(default_factory=lambda: int(_env("LS_EMBED_DIM", "64")))

    # Clip scoring
    clip_min_score: float = field(default_factory=lambda: float(_env("LS_CLIP_MIN_SCORE", "0.35")))

    # Discord (optional)
    discord_token: str = field(default_factory=lambda: _env("DISCORD_TOKEN", ""))
    api_base: str = field(default_factory=lambda: _env("LS_API_BASE", "http://127.0.0.1:8090"))


settings = Settings()
