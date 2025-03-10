from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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
    
    # 挂载静态文件目录
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    return app