from fastapi import FastAPI
from fastadmin import fastapi_app as admin_app
from fastadmin import TortoiseModelAdmin, register, ModelAdmin
from apps.users.models import User
from core.config import settings
from apps.users.crud import get_user_by_username_or_email
from core.security import verify_password
from apps.users.admin import UserModelAdmin
import apps.test.admin  as TestAdmin
import apps.resources.admin as resourcesAdmin
import apps.tasks.admin as tasksAdmin
import apps.albums.admin as albumsAdmin
from typing import Type, Dict
import importlib
import pkgutil
import inspect
import os


def discover_admin_models() -> Dict[str, Type[TortoiseModelAdmin]]:
    """自动发现和注册所有带有register装饰器的ModelAdmin类
    
    Returns:
        Dict[str, Type[TortoiseModelAdmin]]: 注册的ModelAdmin类字典
    """
    registered_models = {}
    
    # 遍历apps目录下的所有包
    apps_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'apps')
    for module_info in pkgutil.iter_modules([apps_dir]):
        if not module_info.ispkg:
            continue
            
        # 导入app包
        app_name = module_info.name
        try:
            app_module = importlib.import_module(f'apps.{app_name}')
            admin_module = importlib.import_module(f'apps.{app_name}.admin')
        except ImportError:
            continue
            
        # 查找带有register装饰器的ModelAdmin类
        for name, obj in inspect.getmembers(admin_module):
            if inspect.isclass(obj) and issubclass(obj, TortoiseModelAdmin) and hasattr(obj, '_model'):
                model_name = obj._model.__name__.lower()
                registered_models[model_name] = obj
    
    return registered_models


def setup_admin(app: FastAPI):
    """
    设置FastAdmin
    
    Args:
        app (FastAPI): FastAPI应用实例
    """
    # 配置FastAdmin
    admin_app.title = settings.PROJECT_NAME + " 管理后台"
    admin_app.logo = "/static/logo.png"
    admin_app.theme = "blue"
    
    # 设置用户模型和用户名字段
    os.environ["ADMIN_USER_MODEL"] = "User"
    os.environ["ADMIN_USER_MODEL_USERNAME_FIELD"] = "username"
    os.environ["ADMIN_SECRET_KEY"] = settings.SECRET_KEY
    
    # 自动发现和注册所有ModelAdmin类
    models=discover_admin_models()
    
    # 挂载FastAdmin
    app.mount("/admin", admin_app)
    return app