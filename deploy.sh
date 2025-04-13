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
REMOTE_DIR="/home/git/fastdog"
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
git push --all fastdog || error "推送代码失败"

####################################
# 服务器端部署
# 通过SSH连接到服务器执行部署命令
####################################
info "连接到服务器并执行部署操作..."
# 使用SSH连接到服务器并执行以下命令块
ssh ${SERVER_USER}@${SERVER_IP} << EOF
    # 传递主脚本中的变量到服务器
    REMOTE_DIR="${REMOTE_DIR}"
    REMOTE_APP_DIR="${REMOTE_APP_DIR}"
    ####################################
    # Git钩子配置说明
    ####################################
    echo "注意：请确保服务器上已手动配置Git钩子..."
    echo "确保服务器上的post-receive钩子已正确设置在 ${REMOTE_DIR}/hooks/post-receive"
    echo "并且具有可执行权限 (chmod +x ${REMOTE_DIR}/hooks/post-receive)"
    # 设置脚本遇到错误立即退出
    set -e
    
    ####################################
    # 服务器端变量定义
    ####################################
    # 应用部署目录
    APP_DIR="${REMOTE_APP_DIR}"
    # Git仓库目录
    GIT_DIR="${REMOTE_DIR}"
    # Python虚拟环境目录
    VENV_DIR="${APP_DIR}/venv"
    # 日志文件目录
    LOG_DIR="${APP_DIR}/logs"
    
    ####################################
    # 目录创建
    # 确保应用和日志目录存在
    ####################################
    mkdir -p ${APP_DIR} ${LOG_DIR}
    
    ####################################
    # 代码更新
    # 从Git仓库拉取最新代码或复制初始代码
    ####################################
    echo "更新代码..."
    # 检查应用目录是否已经是Git仓库
    if [ -d "${APP_DIR}/.git" ]; then
        # 如果是Git仓库，直接拉取最新代码
        cd ${APP_DIR} && git pull origin main
    else
        # 如果不是Git仓库，清空目录并从Git目录复制代码
        rm -rf ${APP_DIR}/*
        cp -r ${GIT_DIR}/* ${APP_DIR}/
    fi
    
    # 创建并激活虚拟环境
    echo "设置Python虚拟环境..."
    if [ ! -d "${VENV_DIR}" ]; then
        python3 -m venv ${VENV_DIR}
    fi
    source ${VENV_DIR}/bin/activate
    
    # 安装依赖
    echo "安装依赖..."
    # 检查是否安装了uv，如果没有则安装
    if ! command -v uv &> /dev/null; then
        echo "安装uv包管理器..."
        pip install uv
    fi
    # 使用uv安装依赖
    uv pip install --upgrade pip
    uv pip install -r ${APP_DIR}/requirements.txt
    
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
    
    # 配置Nginx
    echo "配置Nginx..."
    NGINX_CONF="/etc/nginx/conf.d/fastdog.conf"
    cp ${APP_DIR}/deploy/nginx.conf ${NGINX_CONF}
    # 替换配置文件中的路径
    sed -i "s|/path/to/your/static/files/|${APP_DIR}/static/|g" ${NGINX_CONF}
    sed -i "s|/path/to/your/media/files/|${APP_DIR}/static/uploads/|g" ${NGINX_CONF}
    sed -i "s|your_domain.com|$(hostname -I | awk '{print $1}')|g" ${NGINX_CONF}
    
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