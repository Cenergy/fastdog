from fastapi import FastAPI
from fastadmin import fastapi_app as admin_app
from fastadmin import TortoiseModelAdmin, register, ModelAdmin, action, display, WidgetType
from apps.users.models import User
from core.settings import settings
from apps.users.crud import get_user_by_username_or_email
from core.security import verify_password

from typing import Type, Dict, List, Tuple, Any, Optional
from uuid import UUID
import importlib
import pkgutil
import inspect
import os
import logging

from apps.tasks import  admin as TaskModelAdmin
from apps.ideas import  admin as IdeaModelAdmin

# 配置日志
logger = logging.getLogger(__name__)



class AdminRegistry:
    """FastAdmin模型注册表类，用于管理所有注册的ModelAdmin类"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AdminRegistry, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.registry = {}
            self._initialized = True
    
    def register(self, model, admin_class):
        """注册ModelAdmin类
        
        Args:
            model: 模型类
            admin_class: ModelAdmin类
        """
        model_name = model.__name__
        if model_name in self.registry:
            logger.warning(f"模型 {model_name} 已经注册，将被覆盖")
        self.registry[model_name] = (model, admin_class)
        return admin_class
    
    def get_registry(self):
        """获取所有注册的ModelAdmin类
        
        Returns:
            Dict: 注册的ModelAdmin类字典
        """
        return self.registry


# 全局注册表实例
admin_registry = AdminRegistry()


def discover_admin_modules(package_name: str = "apps") -> List[str]:
    """自动发现所有app中的admin模块
    
    Args:
        package_name: 应用包名，默认为"apps"
        
    Returns:
        List[str]: 发现的admin模块路径列表
    """
    admin_modules = []
    
    try:
        package = importlib.import_module(package_name)
    except ImportError:
        logger.warning(f"无法导入包 {package_name}")
        return admin_modules
    
    # 获取包的路径
    package_path = getattr(package, "__path__", [])
    
    # 遍历包中的所有模块
    for _, name, is_pkg in pkgutil.iter_modules(package_path):
        full_name = f"{package_name}.{name}"
        
        if is_pkg:
            # 如果是包，查找admin.py模块
            try:
                admin_module = f"{full_name}.admin"
                importlib.import_module(admin_module)
                admin_modules.append(admin_module)
            except ImportError:
                continue
    return admin_modules


def discover_admin_classes() -> Dict[str, Tuple[Any, Type[TortoiseModelAdmin]]]:
    """发现并导入所有app中已注册的ModelAdmin类
    
    Returns:
        Dict[str, Tuple[Any, Type[TortoiseModelAdmin]]]: 已注册的模型和ModelAdmin类的字典
    """
    # 发现所有admin模块
    admin_modules = discover_admin_modules()
    
    # 打印发现的admin模块
    logger.info(f"发现以下admin模块: {', '.join(admin_modules)}")
    
    # 获取使用register装饰器的类
    registry = admin_registry.get_registry()
    
    # 如果没有找到任何注册的类，尝试直接查找未使用装饰器的类
    if not registry:
        logger.warning("没有找到使用register装饰器注册的ModelAdmin类，尝试直接查找...")
        
        for module_path in admin_modules:
            try:
                module = importlib.import_module(module_path)
                
                # 查找模块中的所有ModelAdmin子类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, TortoiseModelAdmin) and 
                        obj != TortoiseModelAdmin and
                        hasattr(obj, 'model')):
                        
                        model = obj.model
                        model_name = model.__name__
                        registry[model_name] = (model, obj)
                        logger.info(f"发现并注册 {model_name} 与 {obj.__name__}")
                        
            except ImportError as e:
                logger.error(f"导入 {module_path} 时出错: {e}")
    
    return registry


def register_admin_class(model=None):
    """自定义注册装饰器，用于替代原生的register
    
    Args:
        model: 要注册的模型类，可选
        
    Returns:
        Function: 装饰器函数
    """
    def decorator(admin_class):
        nonlocal model
        # 如果没有指定model，尝试从admin类获取
        if model is None and hasattr(admin_class, 'model'):
            model = admin_class.model
            
        if model is None:
            # 无法找到模型
            logger.warning(f"无法为 {admin_class.__name__} 找到模型")
            return admin_class
            
        # 注册到全局注册表
        admin_registry.register(model, admin_class)
        return admin_class
        
    # 如果model是一个类而不是None，说明装饰器被用作 @register_admin_class(Model)
    if model is not None and isinstance(model, type):
        admin_class = model
        model = None
        return decorator(admin_class)
        
    return decorator


def setup_admin(app: FastAPI):
    """
    设置FastAdmin
    
    Args:
        app (FastAPI): FastAPI应用实例
        
    Returns:
        FastAPI: 配置后的FastAPI应用实例
    """
    # 配置FastAdmin
    admin_app.title = settings.PROJECT_NAME + " 管理后台"
    admin_app.logo = "/static/logo.png"
    admin_app.theme = "blue"
    
    # 设置用户模型和用户名字段
    os.environ["ADMIN_USER_MODEL"] = "User"
    os.environ["ADMIN_USER_MODEL_USERNAME_FIELD"] = "username"
    os.environ["ADMIN_SECRET_KEY"] = settings.SECRET_KEY
    
    # 自动发现并加载所有ModelAdmin类
    discover_admin_classes()
    # 挂载FastAdmin
    app.mount("/admin", admin_app)
    return app