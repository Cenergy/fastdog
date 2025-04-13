import multiprocessing
import os

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8188"
accesslog = "-"
errorlog = "-"
loglevel = "info"
reload = False
preload_app = True

# 设置环境变量
os.environ["ENVIRONMENT"] = "production"
