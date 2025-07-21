/**
 * FastDog WASM 解码器
 * 支持 WASM 和 JavaScript 备选解码器
 */
class FastDogDecoder {
    constructor() {
        this.wasmModule = null;
        this.jsDecoder = null;
        this.usingJSFallback = false;
    }

    /**
     * 加载 WASM 模块
     * @private
     */
    async _loadWASM() {
        try {
            console.log('🚀 正在加载 FastDog WASM 解码器...');
            
            // 动态导入 WASM 模块
            const wasmModule = await import('/static/wasm/fastdog_decoder.js');
            
            // 初始化WASM模块，需要指定WASM文件路径
            await wasmModule.default('/static/wasm/fastdog_decoder_bg.wasm');
            
            this.wasmModule = wasmModule;
            this.usingJSFallback = false;
            console.log('✅ FastDog WASM 解码器加载成功');
            
            // 调用初始化函数
            if (this.wasmModule.init) {
                this.wasmModule.init();
            }
            
        } catch (error) {
            console.error('❌ WASM 模块加载失败，尝试使用 JavaScript 备选方案:', error);
            
            // 尝试加载 JavaScript 备选解码器
            try {
                // 动态加载 JavaScript 解码器
                if (!window.FastDogJSDecoder) {
                    await this._loadJSDecoder();
                }
                
                this.jsDecoder = new window.FastDogJSDecoder();
                await this.jsDecoder.init();
                
                console.log('✅ 已切换到 JavaScript 解码器');
                this.usingJSFallback = true;
                this.wasmModule = null; // 确保清除失败的WASM模块引用
                
            } catch (jsError) {
                console.error('❌ JavaScript 解码器也加载失败:', jsError);
                this.usingJSFallback = false;
                this.wasmModule = null;
                this.jsDecoder = null;
                throw new Error(`所有解码器都加载失败: WASM(${error.message}), JS(${jsError.message})`);
            }
        }
    }

    /**
     * 加载 JavaScript 备选解码器
     * @private
     */
    async _loadJSDecoder() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = '/static/js/fallback-decoder.js';
            script.onload = resolve;
            script.onerror = () => reject(new Error('无法加载 JavaScript 解码器'));
            document.head.appendChild(script);
        });
    }

    /**
     * 初始化解码器
     */
    async init() {
        await this._loadWASM();
    }

    /**
     * 解码数据
     * @param {ArrayBuffer} data - 要解码的数据
     * @returns {Promise<ArrayBuffer>} 解码后的数据
     */
    async decode(data) {
        if (this.usingJSFallback) {
            if (!this.jsDecoder) {
                throw new Error('JavaScript解码器未初始化');
            }
            return await this.jsDecoder.decode(data);
        } else {
            if (!this.wasmModule || !this.wasmModule.decode_fastdog_binary) {
                throw new Error('WASM解码器未初始化或decode_fastdog_binary方法不可用');
            }
            
            // 确保数据是Uint8Array格式
            const uint8Data = data instanceof ArrayBuffer ? new Uint8Array(data) : data;
            
            // 调用WASM解码函数
            const startTime = performance.now();
            const wasmResult = this.wasmModule.decode_fastdog_binary(uint8Data);
            const endTime = performance.now();
            const decodeTime = endTime - startTime;
            
            console.log('🔍 WASM解码原始结果:', wasmResult);
            console.log('🔍 WASM结果类型:', typeof wasmResult);
            
            // WASM返回的是DecodeResult结构
            if (!wasmResult.success) {
                throw new Error(`WASM解码失败: ${wasmResult.error || '未知错误'}`);
            }
            
            // 解析WASM返回的数据
            let parsedData;
            try {
                if (wasmResult.data) {
                    // WASM返回的data字段是JSON字符串，需要解析
                    parsedData = JSON.parse(wasmResult.data);
                    console.log('✅ WASM数据JSON解析成功');
                } else {
                    throw new Error('WASM返回的数据为空');
                }
            } catch (error) {
                console.error('❌ WASM数据解析失败:', error);
                throw new Error(`WASM数据解析失败: ${error.message}`);
            }
            
            // 使用WASM返回的统计信息，并添加JavaScript层的时间
            const stats = {
                originalSize: wasmResult.stats.original_size,
                compressedSize: wasmResult.stats.compressed_size,
                compressionRatio: wasmResult.stats.compression_ratio,
                decodeTimeMs: wasmResult.stats.decode_time_ms,
                formatVersion: wasmResult.stats.format_version,
                wasmDecodeTime: wasmResult.stats.decode_time_ms,
                jsWrapperTime: decodeTime
            };
            
            // 返回与JavaScript解码器相同格式的结果
            return {
                success: true,
                data: parsedData,
                stats: stats
            };
        }
    }

    /**
     * 获取当前使用的解码器类型
     * @returns {string} 'wasm' 或 'javascript'
     */
    getDecoderType() {
        return this.usingJSFallback ? 'javascript' : 'wasm';
    }
}

// 导出解码器类
window.FastDogDecoder = FastDogDecoder;
// 为了向后兼容，也导出为 FastDogWASMDecoder
window.FastDogWASMDecoder = FastDogDecoder;