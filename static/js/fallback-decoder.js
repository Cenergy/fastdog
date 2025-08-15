/**
 * FastDog 解码器 JavaScript 备选实现
 * 当 WASM 不可用时使用的纯 JavaScript 解码器
 * 优化版本：增强错误处理、性能监控、缓存机制
 */

class FastDogJSDecoder {
    constructor(options = {}) {
        this.isInitialized = false;
        this.initPromise = null;
        
        // 配置选项
        this.config = {
            enableLogging: options.enableLogging !== false,
            enableCache: options.enableCache !== false,
            maxCacheSize: options.maxCacheSize || 20,
            retryAttempts: options.retryAttempts || 2,
            compressionTimeout: options.compressionTimeout || 30000,
            ...options
        };
        
        // 缓存系统
        this.cache = new Map();
        this.cacheStats = {
            hits: 0,
            misses: 0,
            evictions: 0
        };
        
        // 性能统计
        this.performanceStats = {
            totalDecodes: 0,
            totalTime: 0,
            averageTime: 0,
            successCount: 0,
            errorCount: 0
        };
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
            // 检查环境支持
            if (!FastDogJSDecoder.isSupported()) {
                throw new Error('当前环境不支持 JavaScript 解码器');
            }
            
            const initTime = performance.now() - startTime;
            
            if (this.config.enableLogging) {
                console.log(`✅ JavaScript 解码器初始化成功，耗时: ${initTime.toFixed(2)}ms`);
            }
            
        } catch (error) {
            if (this.config.enableLogging) {
                console.error('❌ JavaScript 解码器初始化失败:', error);
            }
            throw error;
        }
    }

    /**
     * 解码 FastDog 二进制数据（增强版）
     * @param {ArrayBuffer|Uint8Array} data - 二进制数据
     * @param {Object} options - 解码选项
     * @returns {Promise<Object>} 解码结果
     */
    async decode(data, options = {}) {
        if (!this.isInitialized) {
            await this.init();
        }
        
        // 输入验证
        if (!data || (data.byteLength === 0 && data.length === 0)) {
            throw new Error('输入数据为空');
        }
        
        // 生成缓存键
        const cacheKey = this._generateCacheKey(data);
        
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
        
        let lastError = null;
        
        // 重试机制
        for (let attempt = 1; attempt <= this.config.retryAttempts; attempt++) {
            try {
                const result = await this._performDecode(data, options, attempt);
                
                // 更新性能统计
                const decodeTime = performance.now() - startTime;
                this._updateStats(decodeTime, true);
                
                // 缓存结果
                if (this.config.enableCache && result) {
                    this._setCached(cacheKey, result);
                }
                
                return result;
                
            } catch (error) {
                lastError = error;
                this.performanceStats.errorCount++;
                
                if (this.config.enableLogging && attempt < this.config.retryAttempts) {
                    console.warn(`❌ 解码失败 (尝试 ${attempt}/${this.config.retryAttempts}):`, error.message);
                }
                
                // 如果不是最后一次尝试，等待一段时间后重试
                if (attempt < this.config.retryAttempts) {
                    await this._delay(100 * attempt);
                }
            }
        }
        
        // 所有重试都失败
        const decodeTime = performance.now() - startTime;
        this._updateStats(decodeTime, false);
        
        if (this.config.enableLogging) {
            console.error('❌ 所有解码尝试都失败:', lastError);
        }
        
        throw lastError;
    }

    /**
     * 执行实际的解码操作
     * @private
     */
    async _performDecode(data, options, attempt) {
        // 确保数据是 Uint8Array 格式
        const uint8Data = this._ensureUint8Array(data);
        
        if (this.config.enableLogging && attempt === 1) {
            console.log(`🔍 开始解码 ${uint8Data.length} 字节的数据...`);
        }
        
        // 验证和解析头部信息
        const headerInfo = this._parseHeader(uint8Data);
        
        if (this.config.enableLogging && attempt === 1) {
            console.log(`📊 格式信息: 版本=${headerInfo.version}, 压缩=${headerInfo.compressedSize}字节, 原始=${headerInfo.originalSize}字节`);
        }
        
        // 提取压缩数据
        const compressedData = uint8Data.slice(20, 20 + headerInfo.compressedSize);
        
        // 解压缩数据
        const decompressedData = await this._decompressData(compressedData, headerInfo.originalSize);
        
        // 解析 JSON 数据
        const jsonString = new TextDecoder().decode(decompressedData);
        const gltfData = JSON.parse(jsonString);
        
        if (this.config.enableLogging) {
            console.log(`⚡ JavaScript 解码完成`);
        }
        
        return {
            success: true,
            data: gltfData,
            stats: {
                originalSize: headerInfo.originalSize,
                compressedSize: headerInfo.compressedSize,
                compressionRatio: headerInfo.compressedSize / headerInfo.originalSize,
                formatVersion: headerInfo.version,
                attempt: attempt
            }
        };
    }
    
    /**
     * 解析文件头部信息
     * @private
     */
    _parseHeader(uint8Data) {
        if (uint8Data.length < 20) {
            throw new Error('数据太短，不是有效的 FastDog 格式');
        }
        
        // 检查魔数 "FASTDOG1" (8字节)
        const magic = new TextDecoder().decode(uint8Data.slice(0, 8));
        if (magic !== 'FASTDOG1') {
            throw new Error(`无效的魔数: ${magic}，期望: FASTDOG1`);
        }
        
        // 读取版本号
        const version = new DataView(uint8Data.buffer, uint8Data.byteOffset + 8, 4).getUint32(0, true);
        
        // 读取压缩数据长度
        const compressedSize = new DataView(uint8Data.buffer, uint8Data.byteOffset + 12, 4).getUint32(0, true);
        
        // 读取原始数据长度
        const originalSize = new DataView(uint8Data.buffer, uint8Data.byteOffset + 16, 4).getUint32(0, true);
        
        // 验证数据长度
        if (uint8Data.length < 20 + compressedSize) {
            throw new Error(`数据长度不足: 期望至少${20 + compressedSize}字节, 实际${uint8Data.length}字节`);
        }
        
        return { version, compressedSize, originalSize };
    }
    
    /**
     * 解压缩数据
     * @private
     */
    async _decompressData(compressedData, expectedSize) {
        let decompressedData;
        
        // 优先使用 pako 库
        if (typeof pako !== 'undefined') {
            try {
                decompressedData = pako.inflate(compressedData);
            } catch (error) {
                throw new Error(`pako 解压缩失败: ${error.message}`);
            }
        } else if ('DecompressionStream' in window) {
            // 使用浏览器原生的 DecompressionStream
            try {
                decompressedData = await this._decompressWithStream(compressedData);
            } catch (error) {
                throw new Error(`DecompressionStream 解压缩失败: ${error.message}`);
            }
        } else {
            throw new Error('无法解压缩数据：需要 pako 库或浏览器支持 DecompressionStream');
        }
        
        // 验证解压后的数据长度
        if (decompressedData.length !== expectedSize) {
            throw new Error(`解压后数据长度不匹配: 期望=${expectedSize}, 实际=${decompressedData.length}`);
        }
        
        return decompressedData;
    }
    
    /**
     * 使用 DecompressionStream 解压缩
     * @private
     */
    async _decompressWithStream(compressedData) {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('解压缩超时'));
            }, this.config.compressionTimeout);
            
            try {
                const stream = new DecompressionStream('deflate');
                const writer = stream.writable.getWriter();
                const reader = stream.readable.getReader();
                
                writer.write(compressedData);
                writer.close();
                
                const chunks = [];
                
                const readChunks = async () => {
                    try {
                        let done = false;
                        while (!done) {
                            const { value, done: readerDone } = await reader.read();
                            done = readerDone;
                            if (value) {
                                chunks.push(value);
                            }
                        }
                        
                        // 合并所有块
                        const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
                        const result = new Uint8Array(totalLength);
                        let offset = 0;
                        for (const chunk of chunks) {
                            result.set(chunk, offset);
                            offset += chunk.length;
                        }
                        
                        clearTimeout(timeout);
                        resolve(result);
                    } catch (error) {
                        clearTimeout(timeout);
                        reject(error);
                    }
                };
                
                readChunks();
            } catch (error) {
                clearTimeout(timeout);
                reject(error);
            }
        });
    }
    
    /**
     * 验证数据格式
     * @param {ArrayBuffer|Uint8Array} data - 二进制数据
     * @returns {Promise<boolean>} 是否为有效的 FastDog 格式
     */
    async validate(data) {
        try {
            const uint8Data = this._ensureUint8Array(data);
            
            if (uint8Data.length < 20) {
                return false;
            }
            
            // 检查魔数
            const magic = new TextDecoder().decode(uint8Data.slice(0, 8));
            return magic === 'FASTDOG1';
        } catch (error) {
            return false;
        }
    }

    /**
     * 获取格式信息
     * @param {ArrayBuffer|Uint8Array} data - 二进制数据
     * @returns {Promise<Object>} 格式信息
     */
    async getFormatInfo(data) {
        const uint8Data = this._ensureUint8Array(data);
        
        if (uint8Data.length < 20) {
            throw new Error('数据太短');
        }
        
        const magic = new TextDecoder().decode(uint8Data.slice(0, 8));
        const version = new DataView(uint8Data.buffer, uint8Data.byteOffset + 8, 4).getUint32(0, true);
        const compressedSize = new DataView(uint8Data.buffer, uint8Data.byteOffset + 12, 4).getUint32(0, true);
        const originalSize = new DataView(uint8Data.buffer, uint8Data.byteOffset + 16, 4).getUint32(0, true);
        
        return {
            magic,
            version,
            compressedSize,
            originalSize,
            compressionRatio: compressedSize / originalSize,
            totalSize: uint8Data.length
        };
    }
    
    /**
     * 确保数据格式正确
     * @private
     */
    _ensureUint8Array(data) {
        if (!data) {
            throw new Error('数据不能为空');
        }
        return data instanceof ArrayBuffer ? new Uint8Array(data) : data;
    }
    
    /**
     * 生成缓存键
     * @private
     */
    _generateCacheKey(data) {
        const uint8Data = this._ensureUint8Array(data);
        // 使用数据长度和前几个字节生成简单的哈希
        const sample = uint8Data.slice(0, Math.min(32, uint8Data.length));
        let hash = uint8Data.length;
        for (let i = 0; i < sample.length; i++) {
            hash = ((hash << 5) - hash + sample[i]) & 0xffffffff;
        }
        return `cache_${hash}_${uint8Data.length}`;
    }
    
    /**
     * 设置缓存
     * @private
     */
    _setCached(key, value) {
        // 如果缓存已满，删除最旧的条目
        if (this.cache.size >= this.config.maxCacheSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
            this.cacheStats.evictions++;
        }
        
        this.cache.set(key, value);
    }
    
    /**
     * 更新性能统计
     * @private
     */
    _updateStats(decodeTime, success) {
        this.performanceStats.totalDecodes++;
        this.performanceStats.totalTime += decodeTime;
        this.performanceStats.averageTime = this.performanceStats.totalTime / this.performanceStats.totalDecodes;
        
        if (success) {
            this.performanceStats.successCount++;
        }
    }
    
    /**
     * 延迟函数
     * @private
     */
    async _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * 清理缓存
     */
    clearCache() {
        this.cache.clear();
        this.cacheStats.hits = 0;
        this.cacheStats.misses = 0;
        this.cacheStats.evictions = 0;
        
        if (this.config.enableLogging) {
            console.log('🗑️ 缓存已清理');
        }
    }
    
    /**
     * 重置性能统计
     */
    resetStats() {
        this.performanceStats = {
            totalDecodes: 0,
            totalTime: 0,
            averageTime: 0,
            successCount: 0,
            errorCount: 0
        };
        
        if (this.config.enableLogging) {
            console.log('📊 性能统计已重置');
        }
    }
    
    /**
     * 获取解码器状态
     * @returns {Object} 状态信息
     */
    getStatus() {
        return {
            initialized: this.isInitialized,
            config: { ...this.config },
            performance: { ...this.performanceStats },
            cache: {
                size: this.cache.size,
                maxSize: this.config.maxCacheSize,
                stats: { ...this.cacheStats }
            },
            capabilities: FastDogJSDecoder.getCapabilities()
        };
    }

    /**
     * 性能基准测试（增强版）
     * @param {ArrayBuffer|Uint8Array} data - 二进制数据
     * @param {number} iterations - 迭代次数
     * @param {Object} options - 测试选项
     * @returns {Promise<Object>} 基准测试结果
     */
    async benchmark(data, iterations = 100, options = {}) {
        const {
            warmupRounds = 5,
            enableDetailedStats = false,
            disableCache = true
        } = options;
        
        if (!this.isInitialized) {
            await this.init();
        }
        
        // 临时禁用缓存以获得准确的性能数据
        const originalCacheEnabled = this.config.enableCache;
        if (disableCache) {
            this.config.enableCache = false;
        }
        
        if (this.config.enableLogging) {
            console.log(`🏃 开始 JavaScript 基准测试，预热 ${warmupRounds} 次，测试 ${iterations} 次...`);
        }
        
        try {
            // 预热阶段
            for (let i = 0; i < warmupRounds; i++) {
                try {
                    await this.decode(data);
                } catch (error) {
                    if (this.config.enableLogging) {
                        console.warn(`预热轮次 ${i + 1} 失败:`, error.message);
                    }
                }
            }
            
            // 正式测试
            const times = [];
            const errors = [];
            let successCount = 0;
            
            for (let i = 0; i < iterations; i++) {
                try {
                    const startTime = performance.now();
                    await this.decode(data);
                    const endTime = performance.now();
                    
                    const duration = endTime - startTime;
                    times.push(duration);
                    successCount++;
                } catch (error) {
                    errors.push({
                        iteration: i + 1,
                        error: error.message
                    });
                    
                    if (this.config.enableLogging) {
                        console.warn(`迭代 ${i + 1} 失败:`, error.message);
                    }
                }
            }
            
            if (times.length === 0) {
                throw new Error('所有迭代都失败了');
            }
            
            // 计算统计数据
            const avgTime = times.reduce((sum, time) => sum + time, 0) / times.length;
            const minTime = Math.min(...times);
            const maxTime = Math.max(...times);
            const successRate = successCount / iterations;
            
            // 计算百分位数
            const sortedTimes = [...times].sort((a, b) => a - b);
            const p50 = sortedTimes[Math.floor(sortedTimes.length * 0.5)];
            const p90 = sortedTimes[Math.floor(sortedTimes.length * 0.9)];
            const p95 = sortedTimes[Math.floor(sortedTimes.length * 0.95)];
            const p99 = sortedTimes[Math.floor(sortedTimes.length * 0.99)];
            
            const result = {
                iterations: iterations,
                successful_iterations: successCount,
                failed_iterations: iterations - successCount,
                avg_time_ms: avgTime,
                min_time_ms: minTime,
                max_time_ms: maxTime,
                p50_time_ms: p50,
                p90_time_ms: p90,
                p95_time_ms: p95,
                p99_time_ms: p99,
                success_rate: successRate,
                throughput_ops_per_sec: 1000 / avgTime
            };
            
            if (enableDetailedStats) {
                result.all_times = times;
                result.errors = errors;
            }
            
            if (this.config.enableLogging) {
                console.log('📊 JavaScript 基准测试结果:', {
                    iterations: result.iterations,
                    successRate: (result.success_rate * 100).toFixed(1) + '%',
                    avgTime: result.avg_time_ms.toFixed(2) + 'ms',
                    minTime: result.min_time_ms.toFixed(2) + 'ms',
                    maxTime: result.max_time_ms.toFixed(2) + 'ms',
                    p95Time: result.p95_time_ms.toFixed(2) + 'ms',
                    throughput: result.throughput_ops_per_sec.toFixed(2) + ' ops/sec'
                });
            }
            
            return result;
            
        } finally {
            // 恢复缓存设置
            this.config.enableCache = originalCacheEnabled;
        }
    }

    /**
     * 检查 JavaScript 解码器支持
     * @returns {boolean} 是否支持
     */
    static isSupported() {
        return typeof TextDecoder !== 'undefined' && 
               typeof DataView !== 'undefined' &&
               typeof Uint8Array !== 'undefined';
    }

    /**
     * 获取解码器功能信息
     * @returns {Object} 功能信息
     */
    static getCapabilities() {
        return {
            jsDecoderSupported: FastDogJSDecoder.isSupported(),
            pakoSupported: typeof pako !== 'undefined',
            decompressionStreamSupported: 'DecompressionStream' in window,
            textDecoderSupported: typeof TextDecoder !== 'undefined',
            dataViewSupported: typeof DataView !== 'undefined'
        };
    }
}

// 导出类
if (typeof window !== 'undefined') {
    window.FastDogJSDecoder = FastDogJSDecoder;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = FastDogJSDecoder;
}

console.log('📦 FastDog JavaScript 解码器已加载');
console.log('🔧 JavaScript 解码器功能支持:', FastDogJSDecoder.getCapabilities());