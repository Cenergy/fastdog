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