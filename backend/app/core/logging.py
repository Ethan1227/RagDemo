"""全局日志配置（loguru）。

同时输出到控制台与文件（logs/app.log，按天轮转、保留 14 天）。
程序启动时调用一次 setup_logging()。业务代码统一 `from loguru import logger` 使用。
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from loguru import logger

from backend.app.core.config import BACKEND_DIR

LOG_DIR = BACKEND_DIR.parent / "logs"
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

_configured = False


class _InterceptHandler(logging.Handler):
    """将标准 logging（uvicorn/sqlalchemy 等）转发到 loguru。"""

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(level: str = "INFO") -> None:
    """初始化日志：控制台 + 文件，并接管标准 logging。"""
    global _configured
    if _configured:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, format=LOG_FORMAT, level=level, enqueue=True)
    logger.add(
        LOG_DIR / "app.log",
        format=LOG_FORMAT,
        level=level,
        rotation="00:00",
        retention="14 days",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    # 接管标准库 logging，统一日志出口
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).handlers = [_InterceptHandler()]
        logging.getLogger(name).propagate = False

    _configured = True
    logger.info("日志系统初始化完成，日志目录：{}", LOG_DIR)
