import os
import importlib
import logging
from typing import List, Dict, Type, Any
from functools import lru_cache
from tortoise import Model

# 配置日志
logger = logging.getLogger(__name__)

# 存储已注册的模型
_registered_models: Dict[str, Type[Model]] = {}

def register_model(model_name: str = None):
    """模型注册装饰器

    Args:
        model_name (str, optional): 模型注册名称. 默认使用类名
    """
    def decorator(cls):
        nonlocal model_name
        if not model_name:
            model_name = cls.__name__
        if not issubclass(cls, Model):
            raise ValueError(f"{cls.__name__} 必须是 Tortoise Model 的子类")
        _registered_models[model_name] = cls
        return cls
    return decorator

def validate_model(module: Any) -> bool:
    """验证模块是否包含有效的Tortoise模型

    Args:
        module: 导入的模块

    Returns:
        bool: 是否包含有效模型
    """
    return any(
        isinstance(attr, type) and issubclass(attr, Model) 
        for attr in module.__dict__.values() 
        if isinstance(attr, type)
    )

@lru_cache(maxsize=32)
def get_app_models() -> List[str]:
    """获取所有应用的模型路径

    Returns:
        List[str]: 模型路径列表
    """
    apps_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "apps")
    app_models = []

    try:
        for app_name in os.listdir(apps_dir):
            app_path = os.path.join(apps_dir, app_name)
            if os.path.isdir(app_path) and not app_name.startswith('__'):
                model_path = f"apps.{app_name}.models"
                try:
                    module = importlib.import_module(model_path)
                    if validate_model(module):
                        app_models.append(model_path)
                        logger.info(f"成功加载模型: {model_path}")
                    else:
                        logger.warning(f"模块 {model_path} 中未找到有效的Tortoise模型")
                except ImportError as e:
                    logger.error(f"导入模块 {model_path} 失败: {str(e)}")
                except Exception as e:
                    logger.error(f"处理模块 {model_path} 时发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"扫描应用目录时发生错误: {str(e)}")

    return app_models

def get_registered_models() -> Dict[str, Type[Model]]:
    """获取所有已注册的模型

    Returns:
        Dict[str, Type[Model]]: 模型字典
    """
    return _registered_models.copy()

# 获取所有应用的模型
ALL_MODELS = get_app_models()