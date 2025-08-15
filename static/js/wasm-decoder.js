/**
 * FastDog WASM 解码器
 * 支持 WASM 和 JavaScript 备选解码器
 * 优化版本：增强错误处理、性能监控、缓存机制
 */
class FastDogDecoder {
    constructor(options = {}) {
        this.wasmModule = null;
        this.jsDecoder = null;
        this.usingJSFallback = false;
        this.isInitialized = false;
        this.initPromise = null;
        
        // 配置选项
        this.config = {
            enableLogging: options.enableLogging !== false,
            enableCache: options.enableCache !== false,
            maxCacheSize: options.maxCacheSize || 50,
            retryAttempts: options.retryAttempts || 2,
            wasmPath: options.wasmPath || '/static/wasm/fastdog_decoder.js',
            wasmBgPath: options.wasmBgPath || '/static/wasm/fastdog_decoder_bg.wasm',
            fallbackPath: options.fallbackPath || '/static/js/fallback-decoder.js',
            ...options
        };
        
        // 缓存系统
        this.cache = new Map();
        this.cacheStats = {
            hits: 0,
            misses: 0,
            evictions: 0
        };
        
        // 性能监控
        this.performanceStats = {
            totalDecodes: 0,
            totalTime: 0,
            wasmDecodes: 0,
            jsDecodes: 0,
            averageTime: 0
        };
        
        // 错误统计
        this.errorStats = {
            wasmErrors: 0,
            jsErrors: 0,
            totalErrors: 0
        };
    }

    /**
     * 加载 WASM 模块（支持重试机制）
     * @private
     */
    async _loadWASM() {
        let lastError = null;
        
        for (let attempt = 1; attempt <= this.config.retryAttempts; attempt++) {
            try {
                if (this.config.enableLogging) {
                    console.log(`🚀 正在加载 FastDog WASM 解码器... (尝试 ${attempt}/${this.config.retryAttempts})`);
                }
                
                // 预检查 WASM 支持
                if (!this._isWasmSupported()) {
                    throw new Error('当前环境不支持 WebAssembly');
                }
                
                // 动态导入 WASM 模块
                const wasmModule = await this._importWasmModule();
                
                // 初始化WASM模块，需要指定WASM文件路径
                await wasmModule.default(this.config.wasmBgPath);
                
                this.wasmModule = wasmModule;
                this.usingJSFallback = false;
                
                if (this.config.enableLogging) {
                    console.log('✅ FastDog WASM 解码器加载成功');
                }
                
                // 调用初始化函数
                if (this.wasmModule.init) {
                    this.wasmModule.init();
                }
                
                // 预热 WASM 模块
                await this._warmupWasm();
                
                return; // 成功加载，退出重试循环
                
            } catch (error) {
                lastError = error;
                this.errorStats.wasmErrors++;
                
                if (this.config.enableLogging) {
                    console.warn(`❌ WASM 模块加载失败 (尝试 ${attempt}/${this.config.retryAttempts}):`, error.message);
                }
                
                // 如果不是最后一次尝试，等待一段时间后重试
                if (attempt < this.config.retryAttempts) {
                    await this._delay(1000 * attempt); // 递增延迟
                }
            }
        }
        
        // 所有 WASM 加载尝试都失败，尝试 JavaScript 备选方案
        if (this.config.enableLogging) {
            console.error('❌ WASM 模块加载失败，尝试使用 JavaScript 备选方案:', lastError);
        }
        
        await this._loadJSFallback(lastError);
    }

    /**
     * 加载 JavaScript 备选解码器（增强版）
     * @private
     */
    async _loadJSDecoder() {
        return new Promise((resolve, reject) => {
            // 检查是否已经加载
            if (window.FastDogJSDecoder) {
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.src = this.config.fallbackPath;
            script.async = true;
            script.defer = true;
            
            const timeout = setTimeout(() => {
                reject(new Error('JavaScript 解码器加载超时'));
            }, 10000); // 10秒超时
            
            script.onload = () => {
                clearTimeout(timeout);
                resolve();
            };
            
            script.onerror = () => {
                clearTimeout(timeout);
                reject(new Error('无法加载 JavaScript 解码器'));
            };
            
            document.head.appendChild(script);
        });
    }
    
    /**
     * 加载 JavaScript 备选方案
     * @private
     */
    async _loadJSFallback(wasmError) {
        try {
            // 动态加载 JavaScript 解码器
            await this._loadJSDecoder();
            
            this.jsDecoder = new window.FastDogJSDecoder();
            await this.jsDecoder.init();
            
            if (this.config.enableLogging) {
                console.log('✅ 已切换到 JavaScript 解码器');
            }
            
            this.usingJSFallback = true;
            this.wasmModule = null; // 确保清除失败的WASM模块引用
            
        } catch (jsError) {
            this.errorStats.jsErrors++;
            this.errorStats.totalErrors++;
            
            if (this.config.enableLogging) {
                console.error('❌ JavaScript 解码器也加载失败:', jsError);
            }
            
            this.usingJSFallback = false;
            this.wasmModule = null;
            this.jsDecoder = null;
            
            throw new Error(`所有解码器都加载失败: WASM(${wasmError?.message || '未知错误'}), JS(${jsError.message})`);
        }
    }

    /**
     * 初始化解码器（支持单例模式）
     */
    async init() {
        if (this.isInitialized) {
            return;
        }
        
        if (this.initPromise) {
            return this.initPromise;
        }
        
        this.initPromise = this._performInit();
        
        try {
            await this.initPromise;
            this.isInitialized = true;
        } catch (error) {
            this.initPromise = null;
            throw error;
        }
    }
    
    /**
     * 执行实际的初始化
     * @private
     */
    async _performInit() {
        const startTime = performance.now();
        
        try {
            await this._loadWASM();
            
            const initTime = performance.now() - startTime;
            if (this.config.enableLogging) {
                console.log(`🎯 解码器初始化完成，耗时: ${initTime.toFixed(2)}ms`);
            }
            
        } catch (error) {
            this.errorStats.totalErrors++;
            if (this.config.enableLogging) {
                console.error('❌ 解码器初始化失败:', error);
            }
            throw error;
        }
    }

    /**
     * 解码数据（增强版）
     * @param {ArrayBuffer|Uint8Array} data - 要解码的数据
     * @param {boolean} zeroCopy - 是否使用零拷贝模式
     * @param {Object} options - 解码选项
     * @returns {Promise<ArrayBuffer>} 解码后的数据
     */
    async decode(data, zeroCopy = false, options = {}) {
        if (!this.isInitialized) {
            await this.init();
        }
        
        if (!this.wasmModule && !this.jsDecoder) {
            throw new Error('解码器未初始化');
        }
        
        // 输入验证
        if (!data || (data.byteLength === 0 && data.length === 0)) {
            throw new Error('输入数据为空');
        }
        
        // 生成缓存键
        const cacheKey = this._generateCacheKey(data, zeroCopy, options);
        
        // 检查缓存
        if (this.config.enableCache && this.cache.has(cacheKey)) {
            this.cacheStats.hits++;
            if (this.config.enableLogging) {
                console.log('🎯 缓存命中，直接返回结果');
            }
            return this.cache.get(cacheKey);
        }
        
        this.cacheStats.misses++;
        const startTime = performance.now();
        
        try {
            let result;
            
            if (this.wasmModule && !this.usingJSFallback) {
                // 使用 WASM 解码
                result = await this._decodeWithWasm(data, zeroCopy, options);
                this.performanceStats.wasmDecodes++;
            } else if (this.jsDecoder) {
                // 使用 JavaScript 备选解码器
                result = await this._decodeWithJS(data, zeroCopy, options);
                this.performanceStats.jsDecodes++;
            } else {
                throw new Error('没有可用的解码器');
            }
            
            const endTime = performance.now();
            const decodeTime = endTime - startTime;
            
            // 更新性能统计
            this.performanceStats.totalDecodes++;
            this.performanceStats.totalTime += decodeTime;
            this.performanceStats.averageTime = this.performanceStats.totalTime / this.performanceStats.totalDecodes;
            
            if (this.config.enableLogging) {
                console.log(`解码完成，耗时: ${decodeTime.toFixed(2)}ms, 使用: ${this.usingJSFallback ? 'JavaScript' : 'WASM'}`);
            }
            
            // 缓存结果
            if (this.config.enableCache && result) {
                this._setCached(cacheKey, result);
            }
            
            return result;
            
        } catch (error) {
            this.errorStats.totalErrors++;
            if (this.usingJSFallback) {
                this.errorStats.jsErrors++;
            } else {
                this.errorStats.wasmErrors++;
            }
            
            if (this.config.enableLogging) {
                console.error('解码失败:', error);
            }
            
            // 如果 WASM 解码失败，尝试降级到 JS
            if (!this.usingJSFallback && this.jsDecoder) {
                if (this.config.enableLogging) {
                    console.warn('🔄 WASM 解码失败，尝试使用 JavaScript 备选方案');
                }
                
                try {
                    const result = await this._decodeWithJS(data, zeroCopy, options);
                    this.performanceStats.jsDecodes++;
                    return result;
                } catch (jsError) {
                    this.errorStats.jsErrors++;
                    throw new Error(`所有解码方案都失败: WASM(${error.message}), JS(${jsError.message})`);
                }
            }
            
            throw error;
        }
    }

    /**
     * 零拷贝解码数据（直接返回二进制数据）
     * @param {ArrayBuffer} data - 要解码的数据
     * @returns {Promise<{data: Uint8Array, stats: Object}>} 解码后的二进制数据和统计信息
     */
    async decodeBinary(data) {
        if (this.usingJSFallback) {
            // JavaScript备选方案
            const result = await this.decode(data);
            if (result.data && result.data.type === 'glb') {
                // 将base64数据转换回二进制
                const binaryData = this._base64ToUint8Array(result.data.data);
                return {
                    data: binaryData,
                    stats: result.stats
                };
            }
            throw new Error('JavaScript解码器不支持二进制输出');
        } else {
            if (!this.wasmModule || !this.wasmModule.decode_fastdog_to_binary) {
                throw new Error('WASM解码器未初始化或decode_fastdog_to_binary方法不可用');
            }
            
            // 确保数据是Uint8Array格式
            const uint8Data = data instanceof ArrayBuffer ? new Uint8Array(data) : data;
            
            // 调用WASM二进制解码函数
            const startTime = performance.now();
            const binaryResult = this.wasmModule.decode_fastdog_to_binary(uint8Data);
            const endTime = performance.now();
            
            // 获取统计信息
            const statsResult = this.wasmModule.get_decode_stats(uint8Data);
            
            console.log('🚀 WASM二进制解码完成，数据长度:', binaryResult.length);
            
            return {
                data: binaryResult,
                stats: {
                    originalSize: statsResult.original_size,
                    compressedSize: statsResult.compressed_size,
                    compressionRatio: statsResult.compression_ratio,
                    decodeTimeMs: statsResult.decode_time_ms,
                    formatVersion: statsResult.format_version,
                    wasmDecodeTime: statsResult.decode_time_ms,
                    jsWrapperTime: endTime - startTime
                }
            };
        }
    }

    /**
     * 零拷贝解码（返回内存指针）
     * @param {ArrayBuffer} data - 要解码的数据
     * @returns {Promise<{dataView: Uint8Array, stats: Object}>} 内存视图和统计信息
     */
    async decodeZeroCopy(data) {
        if (this.usingJSFallback) {
            // JavaScript备选方案，实际上还是会拷贝
            return await this.decodeBinary(data);
        } else {
            if (!this.wasmModule || !this.wasmModule.decode_fastdog_binary_zero_copy) {
                throw new Error('WASM解码器未初始化或decode_fastdog_binary_zero_copy方法不可用');
            }
            
            // 确保数据是Uint8Array格式
            const uint8Data = data instanceof ArrayBuffer ? new Uint8Array(data) : data;
            
            // 调用WASM零拷贝解码函数
            const startTime = performance.now();
            const result = this.wasmModule.decode_fastdog_binary_zero_copy(uint8Data);
            const endTime = performance.now();
            
            if (!result.success) {
                throw new Error(`WASM零拷贝解码失败: ${result.error || '未知错误'}`);
            }
            
            // 创建内存视图，直接访问WASM内存
            const dataView = new Uint8Array(
                this.wasmModule.memory.buffer,
                result.data_ptr,
                result.data_len
            );
            
            console.log('⚡ WASM零拷贝解码完成，数据长度:', result.data_len);
            
            return {
                dataView: dataView,
                stats: {
                    originalSize: result.stats.original_size,
                    compressedSize: result.stats.compressed_size,
                    compressionRatio: result.stats.compression_ratio,
                    decodeTimeMs: result.stats.decode_time_ms,
                    formatVersion: result.stats.format_version,
                    wasmDecodeTime: result.stats.decode_time_ms,
                    jsWrapperTime: endTime - startTime
                }
            };
        }
    }

    /**
     * Base64转Uint8Array的辅助函数
     * @private
     */
    _base64ToUint8Array(base64) {
        const binaryString = atob(base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes;
    }

    /**
     * 获取当前使用的解码器类型
     * @returns {string} 'wasm' 或 'javascript'
     */
    getDecoderType() {
        return this.usingJSFallback ? 'javascript' : 'wasm';
    }
    
    /**
     * 获取解码器状态（增强版）
     * @returns {Object} 状态信息
     */
    getStatus() {
        return {
            wasmLoaded: !!this.wasmModule,
            jsLoaded: !!this.jsDecoder,
            usingJSFallback: this.usingJSFallback,
            ready: !!(this.wasmModule || this.jsDecoder),
            initialized: this.isInitialized,
            config: { ...this.config },
            performance: { ...this.performanceStats },
            cache: {
                size: this.cache.size,
                maxSize: this.config.maxCacheSize,
                stats: { ...this.cacheStats }
            },
            errors: { ...this.errorStats }
        };
    }
    
    /**
     * 批量解码多个数据
     * @param {Array} dataArray - 数据数组
     * @param {Object} options - 解码选项
     * @returns {Promise<Array>} 解码结果数组
     */
    async batchDecode(dataArray, options = {}) {
        if (!Array.isArray(dataArray)) {
            throw new Error('输入必须是数组');
        }
        
        const {
            concurrency = 3,
            continueOnError = true,
            zeroCopy = false
        } = options;
        
        const results = [];
        const errors = [];
        
        // 分批处理
        for (let i = 0; i < dataArray.length; i += concurrency) {
            const batch = dataArray.slice(i, i + concurrency);
            const batchPromises = batch.map(async (data, index) => {
                try {
                    const result = await this.decode(data, zeroCopy, options);
                    return { index: i + index, result, error: null };
                } catch (error) {
                    if (!continueOnError) {
                        throw error;
                    }
                    return { index: i + index, result: null, error };
                }
            });
            
            const batchResults = await Promise.all(batchPromises);
            
            for (const item of batchResults) {
                if (item.error) {
                    errors.push({ index: item.index, error: item.error });
                }
                results[item.index] = item.result;
            }
        }
        
        return {
            results,
            errors,
            successCount: results.filter(r => r !== null).length,
            errorCount: errors.length
        };
    }
    
    /**
     * 预加载解码器（后台初始化）
     * @param {Object} options - 预加载选项
     * @returns {Promise<void>}
     */
    static async preload(options = {}) {
        const {
            priority = 'low',
            timeout = 30000
        } = options;
        
        const delay = priority === 'high' ? 0 : priority === 'normal' ? 100 : 500;
        
        return new Promise((resolve, reject) => {
            const timeoutId = setTimeout(() => {
                reject(new Error('预加载超时'));
            }, timeout);
            
            setTimeout(async () => {
                try {
                    const decoder = new FastDogDecoder(options);
                    await decoder.init();
                    clearTimeout(timeoutId);
                    resolve(decoder);
                } catch (error) {
                    clearTimeout(timeoutId);
                    reject(error);
                }
            }, delay);
        });
    }
    
    /**
     * 销毁解码器，释放资源
     */
    destroy() {
        try {
            // 清理缓存
            this.clearCache();
            
            // 清理 WASM 模块
            if (this.wasmModule && typeof this.wasmModule.free === 'function') {
                this.wasmModule.free();
            }
            
            // 清理 JS 解码器
            if (this.jsDecoder && typeof this.jsDecoder.destroy === 'function') {
                this.jsDecoder.destroy();
            }
            
            // 重置状态
            this.wasmModule = null;
            this.jsDecoder = null;
            this.isInitialized = false;
            this.initPromise = null;
            
            if (this.config.enableLogging) {
                console.log('🗑️ 解码器已销毁，资源已释放');
            }
            
        } catch (error) {
            if (this.config.enableLogging) {
                console.error('❌ 销毁解码器时出错:', error);
            }
        }
    }
    
    /**
     * 获取详细的性能报告
     * @returns {Object} 性能报告
     */
    getPerformanceReport() {
        const status = this.getStatus();
        const cacheHitRate = this.cacheStats.hits + this.cacheStats.misses > 0 
            ? (this.cacheStats.hits / (this.cacheStats.hits + this.cacheStats.misses) * 100).toFixed(2)
            : 0;
        
        return {
            ...status,
            cacheHitRate: `${cacheHitRate}%`,
            averageDecodeTime: `${this.performanceStats.averageTime.toFixed(2)}ms`,
            totalDecodeTime: `${this.performanceStats.totalTime.toFixed(2)}ms`,
            wasmUsageRate: this.performanceStats.totalDecodes > 0 
                ? `${(this.performanceStats.wasmDecodes / this.performanceStats.totalDecodes * 100).toFixed(2)}%`
                : '0%',
            errorRate: this.performanceStats.totalDecodes > 0
                ? `${(this.errorStats.totalErrors / this.performanceStats.totalDecodes * 100).toFixed(2)}%`
                : '0%'
        };
    }
    
    /**
     * 配置更新
     * @param {Object} newConfig - 新配置
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        
        // 如果缓存大小改变，调整缓存
        if (newConfig.maxCacheSize && newConfig.maxCacheSize < this.cache.size) {
            const excess = this.cache.size - newConfig.maxCacheSize;
            const keys = Array.from(this.cache.keys()).slice(0, excess);
            keys.forEach(key => this.cache.delete(key));
            this.cacheStats.evictions += excess;
        }
        
        if (this.config.enableLogging) {
            console.log('⚙️ 解码器配置已更新:', newConfig);
        }
    }
    
    /**
     * 工具方法：检查 WASM 支持
     * @private
     */
    _isWasmSupported() {
        try {
            if (typeof WebAssembly === 'object' &&
                typeof WebAssembly.instantiate === 'function') {
                const module = new WebAssembly.Module(new Uint8Array([0x0, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00]));
                if (module instanceof WebAssembly.Module) {
                    return new WebAssembly.Instance(module) instanceof WebAssembly.Instance;
                }
            }
        } catch (e) {
            return false;
        }
        return false;
    }
    
    /**
     * 工具方法：动态导入 WASM 模块
     * @private
     */
    async _importWasmModule() {
        try {
            // 尝试 ES6 模块导入
            return await import(this.config.wasmPath);
        } catch (error) {
            // 备选方案：动态脚本加载
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = this.config.wasmPath;
                script.onload = () => {
                    if (window.wasm_bindgen) {
                        resolve(window.wasm_bindgen);
                    } else {
                        reject(new Error('WASM 模块加载后未找到 wasm_bindgen'));
                    }
                };
                script.onerror = () => reject(new Error('WASM 脚本加载失败'));
                document.head.appendChild(script);
            });
        }
    }
    
    /**
     * 工具方法：WASM 模块预热
     * @private
     */
    async _warmupWasm() {
        if (!this.wasmModule) return;
        
        try {
            // 使用小数据进行预热
            const testData = new Uint8Array([0x46, 0x44, 0x47, 0x01]); // FastDog 魔数
            if (this.wasmModule.decode_fastdog_binary) {
                this.wasmModule.decode_fastdog_binary(testData);
            }
        } catch (error) {
            // 预热失败不影响正常使用
            if (this.config.enableLogging) {
                console.warn('⚠️ WASM 预热失败:', error.message);
            }
        }
    }
    
    /**
     * 工具方法：延迟函数
     * @private
     */
    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * 工具方法：生成缓存键
     * @private
     */
    _generateCacheKey(data, zeroCopy, options) {
        const dataHash = this._simpleHash(data);
        const optionsStr = JSON.stringify(options);
        return `${dataHash}_${zeroCopy}_${optionsStr}`;
    }
    
    /**
     * 工具方法：简单哈希函数
     * @private
     */
    _simpleHash(data) {
        const bytes = data instanceof ArrayBuffer ? new Uint8Array(data) : data;
        let hash = 0;
        for (let i = 0; i < Math.min(bytes.length, 1024); i++) {
            hash = ((hash << 5) - hash + bytes[i]) & 0xffffffff;
        }
        return hash.toString(36);
    }
    
    /**
     * 工具方法：设置缓存
     * @private
     */
    _setCached(key, value) {
        if (this.cache.size >= this.config.maxCacheSize) {
            // LRU 淘汰策略：删除最旧的条目
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
            this.cacheStats.evictions++;
        }
        this.cache.set(key, value);
    }
    
    /**
     * 工具方法：使用 WASM 解码
     * @private
     */
    async _decodeWithWasm(data, zeroCopy, options) {
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
        
        if (this.config.enableLogging) {
            console.log('🔍 WASM解码原始结果:', wasmResult);
        }
        
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
                if (this.config.enableLogging) {
                    console.log('✅ WASM数据JSON解析成功');
                }
            } else {
                throw new Error('WASM返回的数据为空');
            }
        } catch (error) {
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
    
    /**
     * 工具方法：使用 JavaScript 解码
     * @private
     */
    async _decodeWithJS(data, zeroCopy, options) {
        if (!this.jsDecoder) {
            throw new Error('JavaScript解码器未初始化');
        }
        return await this.jsDecoder.decode(data, zeroCopy, options);
    }
    
    /**
     * 清理缓存
     */
    clearCache() {
        this.cache.clear();
        this.cacheStats.hits = 0;
        this.cacheStats.misses = 0;
        this.cacheStats.evictions = 0;
    }
    
    /**
     * 重置性能统计
     */
    resetStats() {
        this.performanceStats = {
            totalDecodes: 0,
            totalTime: 0,
            wasmDecodes: 0,
            jsDecodes: 0,
            averageTime: 0
        };
        
        this.errorStats = {
            wasmErrors: 0,
            jsErrors: 0,
            totalErrors: 0
        };
    }
    
    /**
     * 获取StreamDecoder类（仅WASM模式支持）
     * @returns {Function|null} StreamDecoder构造函数或null
     */
    getStreamDecoder() {
        if (this.usingJSFallback) {
            if (this.config.enableLogging) {
                console.warn('⚠️ JavaScript模式不支持StreamDecoder，返回null');
            }
            return null;
        }
        
        if (!this.wasmModule || !this.wasmModule.StreamDecoder) {
            if (this.config.enableLogging) {
                console.warn('⚠️ WASM模块未加载或不支持StreamDecoder');
            }
            return null;
        }
        
        return this.wasmModule.StreamDecoder;
    }
}

// 导出解码器类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FastDogDecoder;
} else if (typeof window !== 'undefined') {
    window.FastDogDecoder = FastDogDecoder;
    // 为了向后兼容，也导出为 FastDogWASMDecoder
    window.FastDogWASMDecoder = FastDogDecoder;
}