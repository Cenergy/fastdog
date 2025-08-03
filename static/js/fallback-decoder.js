/**
 * FastDog 解码器 JavaScript 备选实现
 * 当 WASM 不可用时使用的纯 JavaScript 解码器
 */

class FastDogJSDecoder {
    constructor() {
        this.isInitialized = false;
    }

    /**
     * 初始化解码器
     */
    async init() {
        this.isInitialized = true;
        console.log('✅ JavaScript 解码器初始化成功');
    }

    /**
     * 解码 FastDog 二进制数据
     * @param {ArrayBuffer|Uint8Array} data - 二进制数据
     * @returns {Promise<Object>} 解码结果
     */
    async decode(data) {
        if (!this.isInitialized) {
            throw new Error('解码器未初始化');
        }

        const startTime = performance.now();
        
        try {
            // 确保数据是 Uint8Array 格式
            const uint8Data = data instanceof ArrayBuffer ? new Uint8Array(data) : data;
            
            console.log(`🔍 开始解码 ${uint8Data.length} 字节的数据...`);
            
            // 验证魔数
            if (uint8Data.length < 16) {
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
            
            console.log(`📊 格式信息: 版本=${version}, 压缩=${compressedSize}字节, 原始=${originalSize}字节`);
            
            // 提取压缩数据
            const compressedData = uint8Data.slice(20, 20 + compressedSize);
            
            // 使用 pako 解压缩（需要引入 pako 库）
            let decompressedData;
            if (typeof pako !== 'undefined') {
                decompressedData = pako.inflate(compressedData);
            } else {
                // 如果没有 pako，尝试使用浏览器原生的 DecompressionStream
                if ('DecompressionStream' in window) {
                    const stream = new DecompressionStream('deflate');
                    const writer = stream.writable.getWriter();
                    const reader = stream.readable.getReader();
                    
                    writer.write(compressedData);
                    writer.close();
                    
                    const chunks = [];
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
                    decompressedData = new Uint8Array(totalLength);
                    let offset = 0;
                    for (const chunk of chunks) {
                        decompressedData.set(chunk, offset);
                        offset += chunk.length;
                    }
                } else {
                    throw new Error('无法解压缩数据：需要 pako 库或浏览器支持 DecompressionStream');
                }
            }
            
            // 验证解压后的数据长度
            if (decompressedData.length !== originalSize) {
                throw new Error(`解压后数据长度不匹配: 期望=${originalSize}, 实际=${decompressedData.length}`);
            }
            
            // 解析 JSON 数据
            const jsonString = new TextDecoder().decode(decompressedData);
            const gltfData = JSON.parse(jsonString);
            
            const endTime = performance.now();
            const decodeTime = endTime - startTime;
            
            console.log(`⚡ JavaScript 解码完成，耗时: ${decodeTime.toFixed(2)}ms`);
            
            return {
                success: true,
                data: gltfData,
                stats: {
                    originalSize: originalSize,
                    compressedSize: compressedSize,
                    compressionRatio: compressedSize / originalSize,
                    decodeTimeMs: decodeTime,
                    formatVersion: version,
                    jsDecodeTime: decodeTime
                }
            };
            
        } catch (error) {
            console.error('❌ JavaScript 解码失败:', error);
            throw error;
        }
    }

    /**
     * 验证数据格式
     * @param {ArrayBuffer|Uint8Array} data - 二进制数据
     * @returns {Promise<boolean>} 是否为有效的 FastDog 格式
     */
    async validate(data) {
        try {
            const uint8Data = data instanceof ArrayBuffer ? new Uint8Array(data) : data;
            
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
        const uint8Data = data instanceof ArrayBuffer ? new Uint8Array(data) : data;
        
        if (uint8Data.length < 16) {
            throw new Error('数据太短');
        }
        
        const magic = new TextDecoder().decode(uint8Data.slice(0, 4));
        const version = new DataView(uint8Data.buffer, uint8Data.byteOffset + 4, 4).getUint32(0, true);
        const compressedSize = new DataView(uint8Data.buffer, uint8Data.byteOffset + 8, 4).getUint32(0, true);
        const originalSize = new DataView(uint8Data.buffer, uint8Data.byteOffset + 12, 4).getUint32(0, true);
        
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
     * 性能基准测试
     * @param {ArrayBuffer|Uint8Array} data - 二进制数据
     * @param {number} iterations - 迭代次数
     * @returns {Promise<Object>} 基准测试结果
     */
    async benchmark(data, iterations = 100) {
        console.log(`🏃 开始 JavaScript 基准测试，迭代 ${iterations} 次...`);
        
        const times = [];
        let successCount = 0;
        
        for (let i = 0; i < iterations; i++) {
            try {
                const startTime = performance.now();
                await this.decode(data);
                const endTime = performance.now();
                
                times.push(endTime - startTime);
                successCount++;
            } catch (error) {
                console.warn(`迭代 ${i + 1} 失败:`, error.message);
            }
        }
        
        if (times.length === 0) {
            throw new Error('所有迭代都失败了');
        }
        
        const avgTime = times.reduce((sum, time) => sum + time, 0) / times.length;
        const minTime = Math.min(...times);
        const maxTime = Math.max(...times);
        const successRate = successCount / iterations;
        
        const result = {
            iterations: iterations,
            successful_iterations: successCount,
            avg_time_ms: avgTime,
            min_time_ms: minTime,
            max_time_ms: maxTime,
            success_rate: successRate
        };
        
        console.log('📊 JavaScript 基准测试结果:', {
            iterations: result.iterations,
            avgTime: result.avg_time_ms.toFixed(2) + 'ms',
            minTime: result.min_time_ms.toFixed(2) + 'ms',
            maxTime: result.max_time_ms.toFixed(2) + 'ms',
            successRate: (result.success_rate * 100).toFixed(1) + '%'
        });
        
        return result;
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