#!/bin/bash

# 部署脚本 - 用于将FastDog项目部署到CentOS服务器
# 作者: duaneng
# 最后更新: $(date +"%Y-%m-%d")

####################################
# 服务器配置信息
####################################
# 服务器SSH登录用户名
SERVER_USER="root"
# 服务器IP地址
SERVER_IP="gishai"
# 服务器Git仓库目录
REMOTE_DIR="/home/git/fastdog.git"
# 服务器应用部署目录
REMOTE_APP_DIR="/home/web/fastdog"


####################################
# 终端颜色定义
# 用于脚本输出信息着色
####################################
GREEN="\033[0;32m"  # 绿色 - 成功信息
YELLOW="\033[0;33m" # 黄色 - 警告信息
RED="\033[0;31m"    # 红色 - 错误信息
NC="\033[0m"        # 重置颜色 - No Color

####################################
# 日志输出函数
# 提供不同级别的日志输出功能
####################################
# 信息级别日志 - 绿色
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# 警告级别日志 - 黄色
warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 错误级别日志 - 红色
# 输出错误信息并退出脚本
error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

####################################
# Git远程仓库配置
# 检查并配置Git远程仓库
####################################
if ! git remote | grep -q fastdog; then
    info "配置Git远程仓库..."
    # 添加名为fastdog的远程仓库
    git remote add fastdog ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}
fi

####################################
# 1. 推送本地代码到服务器
info "推送代码到服务器..."
# 推送所有分支到fastdog远程仓库
# 如果失败则报错并退出
git push --all -f fastdog || error "推送代码失败"

info "推送代码成功..."
####################################
# 服务器端部署
# 通过SSH连接到服务器执行部署命令
####################################
info "连接到服务器并执行部署操作..."
# 使用SSH连接到服务器并执行以下命令块
# 添加SSH连接选项以提高稳定性
ssh -o ConnectTimeout=30 -o ServerAliveInterval=60 -o ServerAliveCountMax=3 ${SERVER_USER}@${SERVER_IP} << EOF
    # 传递主脚本中的变量到服务器
    REMOTE_DIR="${REMOTE_DIR}"
    REMOTE_APP_DIR="${REMOTE_APP_DIR}"
    ####################################
    # 服务器端变量定义
    ####################################
    # 应用部署目录
    APP_DIR="${REMOTE_APP_DIR}"
    # Git仓库目录
    GIT_DIR="${REMOTE_DIR}"
    # Python虚拟环境目录
    VENV_DIR="${APP_DIR}/.venv"
    # 日志文件目录
    LOG_DIR="${APP_DIR}/logs"
    
    # 打印变量值以便调试
    echo "应用部署目录: ${APP_DIR}"
    echo "日志目录: ${LOG_DIR}"
    
    ####################################
    # 目录创建
    # 确保应用和日志目录存在
    
    # 安装依赖
    echo "安装依赖..."
    # 检查是否安装了uv，如果没有则安装
    if ! command -v uv &> /dev/null; then
        echo "安装uv包管理器..."
        pip install uv
    fi
    
    # 创建并激活虚拟环境
    echo "设置Python虚拟环境..."
    cd ${APP_DIR}
    
    uv sync
    source ${VENV_DIR}/bin/activate
    echo "Python虚拟已激活..."
    
    # 配置环境变量
    echo "配置环境变量..."
    if [ ! -f "${APP_DIR}/.env" ]; then
        cp ${APP_DIR}/.env.example ${APP_DIR}/.env
        echo "请记得更新.env文件中的配置"
    fi
    
    # 执行数据库迁移
    echo "执行数据库迁移..."
    cd ${APP_DIR}
    aerich upgrade
    
    # 启动Gunicorn
    echo "启动Gunicorn..."
    cd ${APP_DIR}
    gunicorn -c ${APP_DIR}/deploy/gunicorn_conf.py main:app --daemon
    
    # # 配置Nginx
    # echo "配置Nginx..."
    # NGINX_CONF="/etc/nginx/conf.d/fastdog.conf"
    # cp ${APP_DIR}/deploy/nginx.conf ${NGINX_CONF}
    # # 替换配置文件中的路径
    # sed -i "s|/path/to/your/static/files/|${APP_DIR}/static/|g" ${NGINX_CONF}
    # sed -i "s|/path/to/your/media/files/|${APP_DIR}/static/uploads/|g" ${NGINX_CONF}
    # 使用更通用的方式获取IP地址 - 避免使用不兼容的命令
    # SERVER_IP=$(ifconfig | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | head -n 1)
    # 如果上面的命令不可用，可以尝试以下命令
    # SERVER_IP=$(hostname | tr -d '\n')
    # 或者直接使用固定IP地址
    # SERVER_IP="服务器IP地址"
    # sed -i "s|your_domain.com|${SERVER_IP}|g" ${NGINX_CONF}
    
    # 重启Nginx
    echo "重启Nginx..."
    nginx -t && systemctl restart nginx
    
    echo "部署完成！"
EOF

if [ $? -eq 0 ]; then
    info "部署成功完成！"
else
    error "部署过程中出现错误，请检查日志。"
fi