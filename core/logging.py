import logging
import sys
from pathlib import Path
from loguru import logger
from core.settings import settings

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

def setup_logging():
    # 创建日志目录
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # 配置日志格式
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # 配置日志输出
    logger.configure(
        handlers=[
            {"sink": sys.stdout, "format": log_format},
            {"sink": str(logs_dir / "app.log"), "rotation": "1 day", "retention": "10 days", "compression": "zip", "format": log_format, "enqueue": True, "buffering": 4096},
        ],
        levels=[{"name": "DEBUG", "color": "<blue>"}],
    )

    # 拦截标准库的日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 设置第三方库的日志级别
    for _log in ['uvicorn', 'uvicorn.error', 'fastapi']:
        _logger = logging.getLogger(_log)
        _logger.handlers = [InterceptHandler()]

    return logger