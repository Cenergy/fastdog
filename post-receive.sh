
#!/bin/bash

# 应用部署目录
APP_DIR="/Users/duaneng/Desktop/gishai/code/fastdog"
# Python虚拟环境目录
VENV_DIR="${APP_DIR}/.venv"
# 日志文件目录
LOG_DIR="${APP_DIR}/logs"
#nginx配置文件目录
NGINX_DIR="/usr/local/nginx/sbin"
# supervisor配置文件目录
SUPERVISOR_DIR="/etc/supervisor/conf.d"

# 确保日志目录存在
mkdir -p ${LOG_DIR}

# 创建固定日志文件
LOG_FILE="${LOG_DIR}/deploy.log"
touch ${LOG_FILE}
# 清空日志文件
truncate -s 0 ${LOG_FILE}

# 定义日志函数，同时输出到终端和日志文件
log() {
    echo "$1" | tee -a ${LOG_FILE}
}

log "==============================================="
log "开始部署: $(date)"
log "==============================================="

# 安装依赖
log "安装依赖..."
# 检查是否安装了uv，如果没有则安装
if ! command -v uv &> /dev/null; then
    log "安装uv包管理器..."
    pip install uv 2>&1 | tee -a ${LOG_FILE}
fi

# 创建并激活虚拟环境
log "设置Python虚拟环境..."
cd ${APP_DIR}

uv sync 2>&1 | tee -a ${LOG_FILE}
source ${VENV_DIR}/bin/activate
log "Python虚拟环境已激活..."

# 配置环境变量
log "配置环境变量..."
if [ ! -f "${APP_DIR}/.env" ]; then
    cp ${APP_DIR}/.env.example ${APP_DIR}/.env
    log "请记得更新.env文件中的配置"
fi


# 重启Gunicorn
log "重启Gunicorn..."
cd ${APP_DIR}
# 先尝试优雅地停止现有的Gunicorn进程
if [ -f "${LOG_DIR}/gunicorn.pid" ]; then
    kill -TERM $(cat ${LOG_DIR}/gunicorn.pid) 2>/dev/null || true
    sleep 2
fi
# 启动新的Gunicorn进程
gunicorn -c ${APP_DIR}/deploy/gunicorn_conf.py main:app --daemon 2>&1 | tee -a ${LOG_FILE}

# 检查Gunicorn是否成功启动
if [ $? -eq 0 ]; then
    log "Gunicorn已成功启动"
else
    log "警告: Gunicorn启动失败，请检查日志文件: ${LOG_FILE}"
fi

# 启动supervisor
log "启动supervisor..."
#supervisor存在则重启否则pass
if command -v supervisorctl &> /dev/null; then
    cp ${APP_DIR}/deploy/fastdog.conf ${SUPERVISOR_DIR}/fastdog.conf
    log "supervisor配置文件已拷贝..."
    # 重启supervisor
    log "重启supervisor..."
    supervisorctl reload 2>&1 | tee -a ${LOG_FILE}
    log "supervisor已成功重启"
else
    log "警告: supervisor未安装，跳过supervisor配置"
fi


# 先拷贝nginx配置文件然后再重启nginx
# log "拷贝nginx配置文件..."
# cp ${APP_DIR}/deploy/nginx.conf /usr/local/etc/nginx/nginx.conf
# log "nginx配置文件已拷贝..."

# 重启Nginx 
log "重启Nginx..."
# 检查Nginx是否安装并可用
if [ -x "${NGINX_DIR}/nginx" ]; then
    ${NGINX_DIR}/nginx -s reload 2>&1 | tee -a ${LOG_FILE}
elif command -v nginx &> /dev/null; then
    nginx -s reload 2>&1 | tee -a ${LOG_FILE}
else
    log "警告: Nginx命令未找到，请确保Nginx已安装并设置正确的NGINX_DIR路径"
fi

log "==============================================="
log "部署完成: $(date)"
log "==============================================="

# 将终端输出保存到日志文件
log "终端输出已保存到: ${LOG_FILE}"

# 终止tail进程
if [ -n "$TAIL_PID" ]; then
    kill $TAIL_PID
fi