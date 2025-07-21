#!/bin/bash

# FastDog Brotli 压缩模块安装脚本
# 用于在生产服务器上安装和配置 Nginx Brotli 模块

echo "🚀 开始安装 Nginx Brotli 模块..."

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用 root 权限运行此脚本"
    exit 1
fi

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo "❌ 无法检测操作系统版本"
    exit 1
fi

echo "📋 检测到操作系统: $OS $VER"

# Ubuntu/Debian 系统
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    echo "🔧 为 Ubuntu/Debian 安装 Brotli 模块..."
    
    # 更新包列表
    apt update
    
    # 安装依赖
    apt install -y nginx-module-brotli
    
    # 如果上面的包不可用，尝试编译安装
    if [ $? -ne 0 ]; then
        echo "📦 从源码编译 Brotli 模块..."
        apt install -y build-essential git libpcre3-dev zlib1g-dev libssl-dev
        
        # 下载 Brotli 源码
        cd /tmp
        git clone https://github.com/google/ngx_brotli.git
        cd ngx_brotli
        git submodule update --init
        
        # 获取 Nginx 版本
        NGINX_VERSION=$(nginx -v 2>&1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
        
        # 下载对应的 Nginx 源码
        cd /tmp
        wget http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz
        tar -xzf nginx-${NGINX_VERSION}.tar.gz
        cd nginx-${NGINX_VERSION}
        
        # 编译模块
        ./configure --with-compat --add-dynamic-module=/tmp/ngx_brotli
        make modules
        
        # 复制模块文件
        cp objs/ngx_http_brotli_filter_module.so /usr/lib/nginx/modules/
        cp objs/ngx_http_brotli_static_module.so /usr/lib/nginx/modules/
    fi
    
# CentOS/RHEL 系统
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    echo "🔧 为 CentOS/RHEL 安装 Brotli 模块..."
    
    # 安装 EPEL 仓库
    yum install -y epel-release
    
    # 尝试安装预编译模块
    yum install -y nginx-mod-http-brotli
    
    if [ $? -ne 0 ]; then
        echo "📦 从源码编译 Brotli 模块..."
        yum groupinstall -y "Development Tools"
        yum install -y pcre-devel zlib-devel openssl-devel git
        
        # 编译过程同 Ubuntu
        cd /tmp
        git clone https://github.com/google/ngx_brotli.git
        cd ngx_brotli
        git submodule update --init
        
        NGINX_VERSION=$(nginx -v 2>&1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
        
        cd /tmp
        wget http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz
        tar -xzf nginx-${NGINX_VERSION}.tar.gz
        cd nginx-${NGINX_VERSION}
        
        ./configure --with-compat --add-dynamic-module=/tmp/ngx_brotli
        make modules
        
        cp objs/ngx_http_brotli_filter_module.so /usr/lib64/nginx/modules/
        cp objs/ngx_http_brotli_static_module.so /usr/lib64/nginx/modules/
    fi
else
    echo "❌ 不支持的操作系统: $OS"
    exit 1
fi

# 创建模块加载配置
echo "📝 配置 Nginx 模块加载..."

# 检查模块配置文件
if [ ! -f /etc/nginx/modules-enabled/50-mod-http-brotli.conf ]; then
    mkdir -p /etc/nginx/modules-enabled
    cat > /etc/nginx/modules-enabled/50-mod-http-brotli.conf << EOF
# Brotli 压缩模块
load_module modules/ngx_http_brotli_filter_module.so;
load_module modules/ngx_http_brotli_static_module.so;
EOF
fi

# 检查 Nginx 配置语法
echo "🔍 检查 Nginx 配置..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx 配置检查通过"
    
    # 重新加载 Nginx
    echo "🔄 重新加载 Nginx..."
    systemctl reload nginx
    
    if [ $? -eq 0 ]; then
        echo "🎉 Brotli 模块安装和配置完成！"
        echo ""
        echo "📊 验证 Brotli 是否工作:"
        echo "curl -H 'Accept-Encoding: br' -I http://your-domain.com/static/js/wasm-decoder.js"
        echo ""
        echo "🔍 查看响应头中是否包含 'Content-Encoding: br'"
    else
        echo "❌ Nginx 重新加载失败"
        exit 1
    fi
else
    echo "❌ Nginx 配置检查失败，请检查配置文件"
    exit 1
fi

# 清理临时文件
echo "🧹 清理临时文件..."
rm -rf /tmp/ngx_brotli /tmp/nginx-*

echo "✨ 安装完成！"