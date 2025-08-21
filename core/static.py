from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .protected_static import ProtectedStaticFiles
from .settings import settings
import os

def setup_static_files(app: FastAPI):
    """
    配置静态文件服务
    
    Args:
        app (FastAPI): FastAPI应用实例
    """
    # 获取静态文件目录的绝对路径
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    
    # 确保静态文件目录存在
    os.makedirs(static_dir, exist_ok=True)
    
    # 根据配置决定是否使用受保护的静态文件处理器
    if settings.PROTECTED_FILE_ENABLE:
        app.mount("/static", ProtectedStaticFiles(
            directory=static_dir,
            protected_extensions=settings.PROTECTED_FILE_EXTENSIONS,
            protected_paths=settings.PROTECTED_FILE_PATHS
        ), name="static")
    else:
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    return app