#!/bin/bash

# FastDog WASM Decoder Build Script
# 构建 WebAssembly 模块

echo "🚀 开始构建 FastDog WASM 解码器..."

# 检查 wasm-pack 是否安装
if ! command -v wasm-pack &> /dev/null; then
    echo "❌ wasm-pack 未安装，请先安装:"
    echo "   curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh"
    exit 1
fi

# 检查 Rust 是否安装
if ! command -v rustc &> /dev/null; then
    echo "❌ Rust 未安装，请先安装:"
    echo "   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

# 清理之前的构建
echo "🧹 清理之前的构建..."
rm -rf pkg/
rm -rf target/

# 构建 WASM 包
echo "🔨 构建 WASM 包..."
wasm-pack build --target web --out-dir pkg --release

if [ $? -eq 0 ]; then
    echo "✅ 构建成功！"
    echo "📦 输出目录: pkg/"
    echo "📄 生成的文件:"
    ls -la pkg/
    
    # 复制到静态文件目录
    echo "📋 复制到静态文件目录..."
    mkdir -p ../static/wasm/
    cp pkg/fastdog_decoder.js ../static/wasm/
    cp pkg/fastdog_decoder_bg.wasm ../static/wasm/
    cp pkg/fastdog_decoder.d.ts ../static/wasm/
    
    echo "✅ 文件已复制到 ../static/wasm/"
    echo "🎉 构建完成！现在可以在 HTML 中使用 WASM 解码器了。"
else
    echo "❌ 构建失败！"
    exit 1
fi