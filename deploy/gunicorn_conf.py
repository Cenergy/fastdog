import os
import multiprocessing


daemon=True # 设置守护进程
bind='0.0.0.0:8188' # 监听内网端口8000
chdir='./' # 工作目录
worker_class='uvicorn.workers.UvicornWorker' # 工作模式
workers=multiprocessing.cpu_count()+1 # 并行工作进程数 核心数*2+1个
threads=2 # 指定每个工作者的线程数
worker_connections = 2000 # 设置最大并发量
loglevel='debug' # 错误日志的日志级别
# 设置访问日志和错误信息日志路径
log_dir = "./logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
pidfile='./logs/gunicorn.pid'
accesslog = "./logs/gunicorn_access.log"
errorlog = "./logs/gunicorn_error.log"

# 超时设置
timeout = 180  # 工作进程超时时间(秒)，增加以处理长时间运行的请求
keepalive = 10  # 在keep-alive连接上等待请求的秒数，增加以减少连接创建开销
graceful_timeout = 60  # 优雅重启超时时间(秒)，增加以确保请求能够完成

# 进程管理
max_requests = 3000  # 一个工作进程处理的最大请求数，增加以减少重启频率
max_requests_jitter = 200  # 增加随机抖动防止同时重启，增加抖动范围
proc_name = 'fastdog_gunicorn'  # 进程名称