import os
import importlib
from typing import List

def get_app_models() -> List[str]:
    apps_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "apps")
    app_models = []

    for app_name in os.listdir(apps_dir):
        if os.path.isdir(os.path.join(apps_dir, app_name)) and not app_name.startswith('__'):
            try:
                module = importlib.import_module(f"apps.{app_name}.models")
                app_models.append(f"apps.{app_name}.models")
            except ImportError:
                # 如果应用没有 models.py 文件，就跳过
                pass

    return app_models

# 获取所有应用的模型
ALL_MODELS = get_app_models()