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

def debug_filter(record):
    """过滤掉不需要的DEBUG信息"""
    message = record["message"]
    # 过滤文件变化监控的DEBUG信息
    if "changes detected" in message.lower():
        return False
    # 过滤git相关的DEBUG信息
    if ".git/" in message:
        return False
    # 过滤日志文件轮转的DEBUG信息
    if "app.log" in message and ("deleted" in message or "added" in message):
        return False
    return True

def setup_logging():
    # 创建日志目录
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # 配置日志格式
    log_format = settings.LOG_FORMAT
    log_level = settings.LOG_LEVEL

    # 配置日志输出
    logger.configure(
        handlers=[
            {"sink": sys.stdout, "format": log_format, "level": log_level, "filter": debug_filter},
            {"sink": str(logs_dir / "app.log"), "rotation": settings.LOG_ROTATION, "retention": "10 days", "compression": "zip", "format": log_format, "level": log_level, "enqueue": True, "buffering": 4096, "filter": debug_filter},
        ],
        levels=[{"name": "DEBUG", "color": "<blue>"}],
    )

    # 拦截标准库的日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 设置第三方库的日志级别
    for _log in ['uvicorn', 'uvicorn.error', 'fastapi']:
        _logger = logging.getLogger(_log)
        _logger.handlers = [InterceptHandler()]
        # 设置第三方库的日志级别为INFO，避免过多的DEBUG信息
        _logger.setLevel(logging.INFO)

    return logger