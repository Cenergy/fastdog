/**
 * WASM模型加载器 - 支持blob传输
 * 使用WebAssembly + 自定义二进制格式加载3D模型
 */

class WASMModelLoader {
    constructor(baseUrl = '/api/v1/resources', authToken = null) {
        this.baseUrl = baseUrl;
        this.authToken = authToken;
        this.wasmModule = null;
        this.isWasmReady = false;
        
        // 性能监控配置
        this.performanceConfig = {
            enableLogging: true,
            logPrefix: '⚡'
        };
        
        // 缓存配置
        this.cache = new Map();
        this.maxCacheSize = 10;
    }

    /**
     * 初始化WASM解码器
     */
    async initWASM() {
        if (this.isWasmReady) return true;
        
        try {
            // 检查是否已经有WASM模块可用
            if (typeof Module !== 'undefined') {
                this.wasmModule = await Module();
            } else {
                // 如果没有WASM模块，使用模拟解码器
                console.warn('⚠️ WASM模块未找到，使用JavaScript解码器');
                this.wasmModule = {
                    // 模拟WASM接口
                    decodeBinary: (data, version = 1) => {
                        // 简单的解压缩实现
                        return this.fallbackDecode(data, version);
                    }
                };
            }
            this.isWasmReady = true;
            console.log('✅ 解码器初始化成功');
            return true;
        } catch (error) {
            console.error('❌ 解码器初始化失败:', error);
            return false;
        }
    }

    /**
     * 备用JavaScript解码器
     */
    fallbackDecode(arrayBuffer, version = 1) {
        try {
            // 使用统一的解析方法
            const header = this.parseBinaryHeader(arrayBuffer);
            
            if (this.performanceConfig.enableLogging) {
                console.log(`📋 解码信息: 版本=${header.version}, 压缩长度=${header.compressedLength}`);
                console.log(`📋 总数据长度: ${arrayBuffer.byteLength}`);
                console.log(`📋 原始长度: ${header.originalLength}`);
                console.log(`📋 压缩数据实际长度: ${header.compressedData.byteLength}`);
            }
            
            // 使用统一的解压缩方法
            const result = this.decompressWithPako(header.compressedData, header.version);
            
            // 对于版本1，返回字符串而不是解析后的JSON
            if (header.version === 1 && typeof result === 'object') {
                return JSON.stringify(result);
            }
            
            return result;
            
        } catch (error) {
            this.handleError('备用解码', error);
        }
    }

    /**
     * 获取请求头
     */
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        if (this.authToken) {
            headers['Authorization'] = `Bearer ${this.authToken}`;
        }
        return headers;
    }

    /**
     * 性能监控工具
     */
    createPerformanceTracker(operationName) {
        const startTime = performance.now();
        const steps = new Map();
        
        return {
            step: (stepName) => {
                steps.set(stepName, performance.now() - startTime);
            },
            finish: () => {
                const totalTime = performance.now() - startTime;
                if (this.performanceConfig.enableLogging) {
                    console.log(`${this.performanceConfig.logPrefix} ${operationName}性能统计:`);
                    for (const [step, time] of steps) {
                        console.log(`   ${step}: ${time.toFixed(2)}ms`);
                    }
                    console.log(`   总耗时: ${totalTime.toFixed(2)}ms`);
                }
                return { steps: Object.fromEntries(steps), totalTime };
            }
        };
    }

    /**
     * 统一错误处理
     */
    handleError(operation, error) {
        const errorMessage = `${operation}失败: ${error.message}`;
        console.error(errorMessage, error);
        throw new Error(errorMessage);
    }

    /**
     * 缓存管理
     */
    getCached(key) {
        return this.cache.get(key);
    }

    setCached(key, value) {
        if (this.cache.size >= this.maxCacheSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        this.cache.set(key, value);
    }

    /**
     * 配置管理
     */
    setPerformanceLogging(enabled) {
        this.performanceConfig.enableLogging = enabled;
    }

    setCacheSize(size) {
        this.maxCacheSize = Math.max(1, size);
        // 如果当前缓存超过新限制，清理多余项
        while (this.cache.size > this.maxCacheSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
    }

    clearCache() {
        this.cache.clear();
    }

    getCacheStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxCacheSize,
            keys: Array.from(this.cache.keys())
        };
    }

    /**
     * 解析二进制数据头部信息
     */
    parseBinaryHeader(arrayBuffer) {
        const uint8Array = new Uint8Array(arrayBuffer);
        
        // 验证魔数
        const magicBytes = uint8Array.slice(0, 8);
        const magic = new TextDecoder().decode(magicBytes);
        
        if (magic !== 'FASTDOG1') {
            throw new Error('无效的二进制格式');
        }

        // 读取版本号
        const version = new DataView(arrayBuffer, 8, 4).getUint32(0, true);
        
        // 读取压缩数据长度
        const compressedLength = new DataView(arrayBuffer, 12, 4).getUint32(0, true);
        
        // 提取压缩数据
        const compressedData = arrayBuffer.slice(16, 16 + compressedLength);
        
        // 读取原始数据长度
        const originalLength = new DataView(arrayBuffer, 16 + compressedLength, 4).getUint32(0, true);
        
        return {
            version,
            compressedLength,
            compressedData,
            originalLength,
            magic
        };
    }

    /**
     * 使用pako解压缩数据
     */
    decompressWithPako(compressedData, version) {
        if (typeof pako === 'undefined') {
            throw new Error('pako库不可用');
        }

        try {
            const uint8Data = new Uint8Array(compressedData);
            
            // 调试信息
            if (this.performanceConfig.enableLogging) {
                const firstBytes = Array.from(uint8Data.slice(0, 16))
                    .map(b => b.toString(16).padStart(2, '0')).join(' ');
                console.log(`🔍 压缩数据前16字节: ${firstBytes}`);
                
                if (uint8Data.length >= 2) {
                    const header = (uint8Data[0] << 8) | uint8Data[1];
                    console.log(`🔍 压缩头部: 0x${header.toString(16)}`);
                }
            }
            
            // 解压缩
            const decompressed = pako.inflate(uint8Data);
            console.log('✅ 标准zlib解压成功');
            
            if (version === 1) {
                // 版本1是GLTF JSON格式
                const result = new TextDecoder().decode(decompressed);
                console.log(`✅ 解压缩完成，得到 ${result.length} 字符的JSON数据`);
                return JSON.parse(result);
            } else if (version === 2) {
                // 版本2是GLB二进制格式
                console.log(`✅ 解压缩完成，得到 ${decompressed.byteLength} 字节的GLB数据`);
                return decompressed.buffer;
            } else {
                throw new Error(`不支持的版本号: ${version}`);
            }
        } catch (error) {
            throw new Error(`解压缩失败: ${error.message}`);
        }
    }

    /**
     * 获取模型信息
     */
    async getModelInfo(filename) {
        try {
            const response = await fetch(`${this.baseUrl}/models/${filename}/info`, {
                headers: this.getHeaders()
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            this.handleError('获取模型信息', error);
        }
    }

    /**
     * 获取模型清单
     */
    async getModelManifest(filename) {
        try {
            const response = await fetch(`${this.baseUrl}/models/${filename}/manifest`, {
                headers: this.getHeaders()
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            this.handleError('获取模型清单', error);
        }
    }

    /**
     * 使用blob方式加载模型（推荐）
     */
    async loadModelBlob(filename, onProgress = null) {
        const tracker = this.createPerformanceTracker('Blob模式加载');
        
        try {
            console.log(`🚀 开始blob方式加载模型: ${filename}`);
            
            // 检查缓存
            const cacheKey = `blob_${filename}`;
            const cached = this.getCached(cacheKey);
            if (cached) {
                console.log('✅ 使用缓存数据');
                return cached;
            }
            
            // 网络请求
            const response = await fetch(`${this.baseUrl}/models/${filename}/blob`, {
                headers: this.getHeaders()
            });
            tracker.step('网络请求');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // 获取响应头信息
            const headers = {
                originalSize: response.headers.get('X-Original-Size'),
                compressedSize: response.headers.get('X-Compressed-Size'),
                compressionRatio: response.headers.get('X-Compression-Ratio'),
                format: response.headers.get('X-Format')
            };

            if (this.performanceConfig.enableLogging) {
                console.log(`📊 模型信息:`);
                console.log(`   原始大小: ${headers.originalSize} bytes`);
                console.log(`   压缩大小: ${headers.compressedSize} bytes`);
                console.log(`   压缩比: ${headers.compressionRatio}`);
                console.log(`   格式: ${headers.format}`);
            }

            // 下载数据
            const arrayBuffer = await response.arrayBuffer();
            tracker.step('数据下载');
            console.log(`✅ 数据下载完成: ${arrayBuffer.byteLength} bytes`);
            
            // 解码二进制数据
            const decodedData = await this.decodeBinaryData(arrayBuffer);
            tracker.step('数据解码');
            
            // 转换为完整的Three.js模型
            const modelResult = await this.convertToThreeModel(decodedData);
            tracker.step('模型转换');
            
            const performanceStats = tracker.finish();
            
            const result = {
                model: modelResult.model,
                geometry: modelResult.geometry, // 保持向后兼容
                format: headers.format || 'blob',
                originalSize: parseInt(headers.originalSize),
                compressedSize: parseInt(headers.compressedSize),
                compressionRatio: parseFloat(headers.compressionRatio),
                performanceStats
            };
            
            // 缓存结果
            this.setCached(cacheKey, result);
            
            return result;
            
        } catch (error) {
            this.handleError('Blob方式加载模型', error);
        }
    }

    /**
     * 合并数据块为ArrayBuffer
     */
    mergeChunks(chunks, totalLength) {
        const arrayBuffer = new ArrayBuffer(totalLength);
        const uint8Array = new Uint8Array(arrayBuffer);
        let position = 0;
        
        for (const chunk of chunks) {
            uint8Array.set(chunk, position);
            position += chunk.length;
        }
        
        return arrayBuffer;
    }

    /**
     * 使用流式传输加载模型
     */
    async loadModelStream(filename, onProgress = null) {
        const tracker = this.createPerformanceTracker('Stream模式加载');
        
        try {
            console.log(`🌊 开始流式加载模型: ${filename}`);
            
            // 检查缓存
            const cacheKey = `stream_${filename}`;
            const cached = this.getCached(cacheKey);
            if (cached) {
                console.log('✅ 使用缓存数据');
                return cached;
            }
            
            // 网络请求
            const response = await fetch(`${this.baseUrl}/models/${filename}/binary`, {
                headers: this.getHeaders()
            });
            tracker.step('网络请求');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentLength = parseInt(response.headers.get('Content-Length'));
            const reader = response.body.getReader();
            const chunks = [];
            let receivedLength = 0;

            // 流式下载
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                chunks.push(value);
                receivedLength += value.length;
                
                if (onProgress) {
                    onProgress({
                        loaded: receivedLength,
                        total: contentLength,
                        percentage: (receivedLength / contentLength) * 100
                    });
                }
            }
            tracker.step('流式下载');

            // 合并数据块
            const arrayBuffer = this.mergeChunks(chunks, receivedLength);
            tracker.step('数据合并');
            console.log(`✅ 流式下载完成: ${receivedLength} bytes`);
            
            // 解码二进制数据
            const decodedData = await this.decodeBinaryData(arrayBuffer);
            tracker.step('数据解码');
            
            // 转换为完整的Three.js模型
            const modelResult = await this.convertToThreeModel(decodedData);
            tracker.step('模型转换');
            
            const performanceStats = tracker.finish();
            
            const result = { 
                model: modelResult.model,
                geometry: modelResult.geometry, // 保持向后兼容
                format: 'stream',
                size: receivedLength,
                performanceStats
            };
            
            // 缓存结果
            this.setCached(cacheKey, result);
            
            return result;
            
        } catch (error) {
            this.handleError('流式加载模型', error);
        }
    }

    /**
     * 解码二进制数据
     */
    async decodeBinaryData(arrayBuffer) {
        if (!this.isWasmReady) {
            await this.initWASM();
        }

        try {
            // 解析二进制头部
            const header = this.parseBinaryHeader(arrayBuffer);
            
            if (this.performanceConfig.enableLogging) {
                console.log(`📋 二进制格式版本: ${header.version}`);
                console.log(`📋 压缩长度: ${header.compressedLength}`);
                console.log(`📋 原始长度: ${header.originalLength}`);
                console.log(`📋 压缩数据实际长度: ${header.compressedData.byteLength}`);
            }
            
            // 使用解码器解压缩
            if (this.wasmModule && this.wasmModule.decodeBinary) {
                // 使用WASM解码器
                const result = this.wasmModule.decodeBinary(arrayBuffer, header.version);
                if (header.version === 1) {
                    return JSON.parse(result);
                } else if (header.version === 2) {
                    return result;
                }
            } else {
                // 使用pako库解压缩
                return this.decompressWithPako(header.compressedData, header.version);
            }
            
        } catch (error) {
            this.handleError('解码二进制数据', error);
        }
    }

    /**
     * 使用Three.js GLTFLoader转换GLTF数据
     */
    async convertToThreeGeometry(gltfData) {
        try {
            // 检查是否有GLTFLoader可用
            if (typeof window !== 'undefined' && window.GLTFLoader) {
                return await this.loadWithGLTFLoader(gltfData);
            }
            
            // 降级到完整的GLTF解析
            return this.parseGLTFData(gltfData);
            
        } catch (error) {
            console.error('转换Three.js几何体失败:', error);
            throw error;
        }
    }

    /**
     * 转换为完整的Three.js模型（包含材质）
     */
    async convertToThreeModel(gltfData) {
        try {
            // 检查数据类型
            if (gltfData instanceof ArrayBuffer) {
                // GLB二进制数据
                console.log('🔧 处理GLB二进制数据');
                if (typeof window !== 'undefined' && window.GLTFLoader) {
                    return await this.loadGLBFromArrayBuffer(gltfData);
                } else {
                    throw new Error('GLTFLoader不可用，无法加载GLB数据');
                }
            } else {
                // GLTF JSON数据
                console.log('🔧 处理GLTF JSON数据');
                
                // 检查是否包含原始格式数据（FBX等）
                if (gltfData.extensions && gltfData.extensions.FASTDOG_ORIGINAL_FORMAT) {
                    const originalFormat = gltfData.extensions.FASTDOG_ORIGINAL_FORMAT;
                    console.log(`🔧 检测到原始格式: ${originalFormat.format}`);
                    
                    if (originalFormat.format === '.fbx' && typeof window !== 'undefined' && window.FBXLoader) {
                        return await this.loadFBXFromBase64(originalFormat.data);
                    } else {
                        throw new Error(`不支持的原始格式: ${originalFormat.format} 或缺少相应的加载器`);
                    }
                }
                
                if (typeof window !== 'undefined' && window.GLTFLoader) {
                    return await this.loadCompleteModelWithGLTFLoader(gltfData);
                }
                
                // 降级到完整的GLTF解析
                const geometry = this.parseGLTFData(gltfData);
                const material = new window.THREE.MeshStandardMaterial({
                    color: 0x667eea,
                    metalness: 0.3,
                    roughness: 0.4,
                });
                const model = new window.THREE.Mesh(geometry, material);
                
                return {
                    model: model,
                    geometry: geometry
                };
            }
            
        } catch (error) {
            this.handleError('转换Three.js模型', error);
        }
    }

    /**
     * 将base64数据转换为ArrayBuffer
     */
    base64ToArrayBuffer(base64Data) {
        const binaryString = atob(base64Data);
        const arrayBuffer = new ArrayBuffer(binaryString.length);
        const uint8Array = new Uint8Array(arrayBuffer);
        for (let i = 0; i < binaryString.length; i++) {
            uint8Array[i] = binaryString.charCodeAt(i);
        }
        return arrayBuffer;
    }

    /**
     * 从模型中提取几何体
     */
    extractGeometry(model) {
        let geometry = null;
        model.traverse((child) => {
            if (child.isMesh && child.geometry && !geometry) {
                geometry = child.geometry;
            }
        });
        
        if (!geometry) {
            // 如果没有找到几何体，创建一个默认的
            geometry = new window.THREE.BoxGeometry(1, 1, 1);
        }
        
        return geometry;
    }

    /**
     * 从base64编码的FBX数据加载模型
     */
    async loadFBXFromBase64(base64Data) {
        const tracker = this.createPerformanceTracker('FBX加载');
        
        return new Promise((resolve, reject) => {
            try {
                if (this.performanceConfig.enableLogging) {
                    console.log('🎨 使用FBXLoader加载FBX数据');
                }
                
                // 转换数据格式
                const arrayBuffer = this.base64ToArrayBuffer(base64Data);
                tracker.step('数据转换');
                
                // 加载FBX模型
                const loader = new window.FBXLoader();
                const fbxModel = loader.parse(arrayBuffer, '');
                tracker.step('FBX解析');
                
                console.log('✅ FBXLoader加载成功');
                
                // 提取几何体
                const geometry = this.extractGeometry(fbxModel);
                tracker.step('几何体提取');
                
                const performanceStats = tracker.finish();
                
                // 返回完整的模型和几何体
                resolve({
                    model: fbxModel,
                    geometry: geometry,
                    performanceStats
                });
                
            } catch (error) {
                reject(new Error(`FBXLoader加载失败: ${error.message}`));
            }
        });
    }

    /**
     * 使用GLTFLoader加载GLTF数据
     */
    async loadWithGLTFLoader(gltfData) {
        return new Promise((resolve, reject) => {
            try {
                // 将GLTF数据转换为Blob URL
                const gltfBlob = new Blob([JSON.stringify(gltfData)], { type: 'application/json' });
                const gltfUrl = URL.createObjectURL(gltfBlob);
                
                const loader = new window.GLTFLoader();
                loader.load(
                    gltfUrl,
                    (gltf) => {
                        // 清理Blob URL
                        URL.revokeObjectURL(gltfUrl);
                        
                        // 提取几何体
                        let geometry = null;
                        gltf.scene.traverse((child) => {
                            if (child.isMesh && child.geometry) {
                                geometry = child.geometry;
                                return;
                            }
                        });
                        
                        if (!geometry) {
                            // 如果没有找到几何体，创建一个默认的
                            geometry = new window.THREE.BoxGeometry(1, 1, 1);
                        }
                        
                        resolve(geometry);
                    },
                    undefined,
                    (error) => {
                        URL.revokeObjectURL(gltfUrl);
                        reject(error);
                    }
                );
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 使用GLTFLoader加载完整模型（包含材质）
     */
    async loadCompleteModelWithGLTFLoader(gltfData) {
        return new Promise((resolve, reject) => {
            try {
                console.log('🎨 使用GLTFLoader加载完整模型（包含材质）');
                
                // 将GLTF数据转换为Blob URL
                const gltfBlob = new Blob([JSON.stringify(gltfData)], { type: 'application/json' });
                const gltfUrl = URL.createObjectURL(gltfBlob);
                
                const loader = new window.GLTFLoader();
                loader.load(
                    gltfUrl,
                    (gltf) => {
                        // 清理Blob URL
                        URL.revokeObjectURL(gltfUrl);
                        
                        console.log('✅ GLTFLoader加载成功，保留完整材质');
                        
                        // 提取第一个几何体用于向后兼容
                        let geometry = null;
                        gltf.scene.traverse((child) => {
                            if (child.isMesh && child.geometry && !geometry) {
                                geometry = child.geometry;
                            }
                        });
                        
                        if (!geometry) {
                            // 如果没有找到几何体，创建一个默认的
                            geometry = new window.THREE.BoxGeometry(1, 1, 1);
                        }
                        
                        // 返回完整的模型和几何体
                        resolve({
                            model: gltf.scene,
                            geometry: geometry
                        });
                    },
                    undefined,
                    (error) => {
                        URL.revokeObjectURL(gltfUrl);
                        console.error('❌ GLTFLoader加载失败:', error);
                        reject(error);
                    }
                );
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 使用GLTFLoader加载GLB二进制数据
     */
    async loadGLBFromArrayBuffer(arrayBuffer) {
        return new Promise((resolve, reject) => {
            try {
                console.log('🔧 加载GLB ArrayBuffer数据，大小:', arrayBuffer.byteLength);
                
                // 直接从ArrayBuffer创建Blob URL，使用正确的GLB MIME类型
                const blob = new Blob([arrayBuffer], { type: 'model/gltf-binary' });
                const url = URL.createObjectURL(blob);
                
                const loader = new window.GLTFLoader();
                loader.load(
                    url,
                    (gltf) => {
                        // 清理Blob URL
                        URL.revokeObjectURL(url);
                        console.log('✅ GLB模型加载成功');
                        
                        // 提取第一个几何体用于向后兼容
                        let geometry = null;
                        gltf.scene.traverse((child) => {
                            if (child.isMesh && child.geometry && !geometry) {
                                geometry = child.geometry;
                            }
                        });
                        
                        if (!geometry) {
                            // 如果没有找到几何体，创建一个默认的
                            geometry = new window.THREE.BoxGeometry(1, 1, 1);
                        }
                        
                        // 返回完整的模型和几何体
                        resolve({
                            model: gltf.scene,
                            geometry: geometry
                        });
                    },
                    undefined,
                    (error) => {
                        URL.revokeObjectURL(url);
                        console.error('❌ GLB模型加载失败:', error);
                        reject(error);
                    }
                );
            } catch (error) {
                console.error('❌ 创建GLB Blob失败:', error);
                reject(error);
            }
        });
    }

    /**
     * 完整解析GLTF数据（降级方案）
     */
    parseGLTFData(gltfData) {
        try {
            const geometry = new window.THREE.BufferGeometry();
            
            if (!gltfData.meshes || gltfData.meshes.length === 0) {
                console.warn('GLTF数据中没有网格信息，使用默认几何体');
                return new window.THREE.BoxGeometry(1, 1, 1);
            }
            
            const mesh = gltfData.meshes[0];
            const primitive = mesh.primitives[0];
            
            // 解析顶点属性
            if (primitive.attributes) {
                // 位置数据
                if (primitive.attributes.POSITION !== undefined) {
                    const positionAccessor = gltfData.accessors[primitive.attributes.POSITION];
                    const positionData = this.extractAccessorData(gltfData, positionAccessor);
                    geometry.setAttribute('position', new window.THREE.BufferAttribute(positionData, 3));
                }
                
                // 法线数据
                if (primitive.attributes.NORMAL !== undefined) {
                    const normalAccessor = gltfData.accessors[primitive.attributes.NORMAL];
                    const normalData = this.extractAccessorData(gltfData, normalAccessor);
                    geometry.setAttribute('normal', new window.THREE.BufferAttribute(normalData, 3));
                }
                
                // UV坐标
                if (primitive.attributes.TEXCOORD_0 !== undefined) {
                    const uvAccessor = gltfData.accessors[primitive.attributes.TEXCOORD_0];
                    const uvData = this.extractAccessorData(gltfData, uvAccessor);
                    geometry.setAttribute('uv', new window.THREE.BufferAttribute(uvData, 2));
                }
            }
            
            // 索引数据
            if (primitive.indices !== undefined) {
                const indexAccessor = gltfData.accessors[primitive.indices];
                const indexData = this.extractAccessorData(gltfData, indexAccessor);
                geometry.setIndex(new window.THREE.BufferAttribute(indexData, 1));
            }
            
            // 计算边界盒和法线
            geometry.computeBoundingBox();
            if (primitive.attributes.NORMAL === undefined) {
                geometry.computeVertexNormals();
            }
            
            return geometry;
            
        } catch (error) {
            console.error('解析GLTF数据失败:', error);
            // 返回默认几何体
            return new window.THREE.BoxGeometry(1, 1, 1);
        }
    }

    /**
     * 提取访问器数据
     */
    extractAccessorData(gltfData, accessor) {
        try {
            const bufferView = gltfData.bufferViews[accessor.bufferView];
            const buffer = gltfData.buffers[bufferView.buffer];
            
            // 处理base64编码的缓冲区数据
            let arrayBuffer;
            if (buffer.uri && buffer.uri.startsWith('data:')) {
                const base64Data = buffer.uri.split(',')[1];
                const binaryString = atob(base64Data);
                arrayBuffer = new ArrayBuffer(binaryString.length);
                const uint8Array = new Uint8Array(arrayBuffer);
                for (let i = 0; i < binaryString.length; i++) {
                    uint8Array[i] = binaryString.charCodeAt(i);
                }
            } else {
                throw new Error('不支持的缓冲区格式');
            }
            
            const byteOffset = (bufferView.byteOffset || 0) + (accessor.byteOffset || 0);
            const componentType = accessor.componentType;
            const count = accessor.count * this.getComponentCount(accessor.type);
            
            // 根据组件类型创建相应的类型化数组
            switch (componentType) {
                case 5120: // BYTE
                    return new Int8Array(arrayBuffer, byteOffset, count);
                case 5121: // UNSIGNED_BYTE
                    return new Uint8Array(arrayBuffer, byteOffset, count);
                case 5122: // SHORT
                    return new Int16Array(arrayBuffer, byteOffset, count);
                case 5123: // UNSIGNED_SHORT
                    return new Uint16Array(arrayBuffer, byteOffset, count);
                case 5125: // UNSIGNED_INT
                    return new Uint32Array(arrayBuffer, byteOffset, count);
                case 5126: // FLOAT
                    return new Float32Array(arrayBuffer, byteOffset, count);
                default:
                    throw new Error(`不支持的组件类型: ${componentType}`);
            }
        } catch (error) {
            console.error('提取访问器数据失败:', error);
            return new Float32Array([]);
        }
    }

    /**
     * 获取组件数量
     */
    getComponentCount(type) {
        switch (type) {
            case 'SCALAR': return 1;
            case 'VEC2': return 2;
            case 'VEC3': return 3;
            case 'VEC4': return 4;
            case 'MAT2': return 4;
            case 'MAT3': return 9;
            case 'MAT4': return 16;
            default: return 1;
        }
    }

    /**
     * 智能模型加载 - 自动选择最佳加载策略
     */
    async loadModel(filename, options = {}) {
        const {
            method = 'auto', // 'auto', 'blob', 'stream'
            onProgress = null,
            useCache = true
        } = options;
        
        const tracker = this.createPerformanceTracker('智能加载');
        
        try {
            console.log(`🤖 智能加载模型: ${filename}`);
            
            // 检查缓存
            if (useCache) {
                const cacheKey = `smart_${filename}`;
                const cached = this.getCached(cacheKey);
                if (cached) {
                    console.log('✅ 使用缓存数据');
                    return cached;
                }
            }
            
            let result;
            
            if (method === 'auto') {
                // 自动选择最佳方法
                try {
                    // 首先尝试获取模型信息来决定加载策略
                    const info = await this.getModelInfo(filename);
                    tracker.step('获取模型信息');
                    
                    // 根据文件大小选择加载方法
                    const sizeThreshold = 10 * 1024 * 1024; // 10MB
                    const useStream = info.size && info.size > sizeThreshold;
                    
                    if (useStream) {
                        console.log('📊 文件较大，使用流式加载');
                        result = await this.loadModelStream(filename, onProgress);
                    } else {
                        console.log('📊 文件较小，使用blob加载');
                        result = await this.loadModelBlob(filename, onProgress);
                    }
                } catch (infoError) {
                    // 如果获取信息失败，默认使用blob方法
                    console.log('⚠️ 无法获取模型信息，使用默认blob加载');
                    result = await this.loadModelBlob(filename, onProgress);
                }
            } else if (method === 'blob') {
                result = await this.loadModelBlob(filename, onProgress);
            } else if (method === 'stream') {
                result = await this.loadModelStream(filename, onProgress);
            } else {
                throw new Error(`不支持的加载方法: ${method}`);
            }
            
            tracker.step('模型加载');
            
            // 缓存结果
            if (useCache) {
                const cacheKey = `smart_${filename}`;
                this.setCached(cacheKey, result);
            }
            
            const performanceStats = tracker.finish();
            result.smartLoadStats = performanceStats;
            
            return result;
            
        } catch (error) {
            this.handleError('智能加载模型', error);
        }
    }

    /**
     * 渐进式加载（分片加载）
     */
    async loadModelProgressive(filename, onProgress = null) {
        try {
            console.log(`📦 开始渐进式加载模型: ${filename}`);
            
            // 使用智能加载作为默认实现
            return await this.loadModel(filename, { onProgress });
            
        } catch (error) {
            this.handleError('渐进式加载模型', error);
        }
    }

    /**
     * 批量加载多个模型（支持并发和智能加载）
     */
    async loadMultipleModels(filenames, options = {}) {
        const {
            concurrent = 3, // 并发数量
            onProgress = null,
            useSmartLoad = true,
            continueOnError = true
        } = options;
        
        const tracker = this.createPerformanceTracker('批量加载');
        
        try {
            console.log(`📦 开始批量加载 ${filenames.length} 个模型（并发: ${concurrent}）`);
            
            const results = [];
            const total = filenames.length;
            let completed = 0;
            
            // 分批处理
            for (let i = 0; i < filenames.length; i += concurrent) {
                const batch = filenames.slice(i, i + concurrent);
                
                const batchPromises = batch.map(async (filename, batchIndex) => {
                    const globalIndex = i + batchIndex;
                    
                    try {
                        const loadMethod = useSmartLoad ? 
                            this.loadModel.bind(this) : 
                            this.loadModelBlob.bind(this);
                            
                        const result = await loadMethod(filename);
                        
                        completed++;
                        if (onProgress) {
                            onProgress({
                                stage: 'loading',
                                current: completed,
                                total: total,
                                filename: filename,
                                percentage: Math.round((completed / total) * 100)
                            });
                        }
                        
                        return { filename, result, success: true, index: globalIndex };
                        
                    } catch (error) {
                        completed++;
                        console.error(`加载模型失败: ${filename}`, error);
                        
                        if (onProgress) {
                            onProgress({
                                stage: 'error',
                                current: completed,
                                total: total,
                                filename: filename,
                                error: error.message,
                                percentage: Math.round((completed / total) * 100)
                            });
                        }
                        
                        if (!continueOnError) {
                            throw error;
                        }
                        
                        return { filename, error, success: false, index: globalIndex };
                    }
                });
                
                const batchResults = await Promise.all(batchPromises);
                results.push(...batchResults);
                
                tracker.step(`批次 ${Math.floor(i / concurrent) + 1}`);
            }
            
            // 按原始顺序排序
            results.sort((a, b) => a.index - b.index);
            
            const successCount = results.filter(r => r.success).length;
            const performanceStats = tracker.finish();
            
            console.log(`✅ 批量加载完成，成功: ${successCount}/${total}`);
            
            return {
                results: results.map(r => ({ filename: r.filename, result: r.result, error: r.error, success: r.success })),
                stats: {
                    total,
                    success: successCount,
                    failed: total - successCount,
                    performance: performanceStats
                }
            };
            
        } catch (error) {
            this.handleError('批量加载模型', error);
        }
    }
    
    /**
     * 预加载模型（后台加载，不阻塞当前操作）
     */
    async preloadModels(filenames, options = {}) {
        const {
            priority = 'low', // 'low', 'normal', 'high'
            onComplete = null
        } = options;
        
        console.log(`🔄 开始预加载 ${filenames.length} 个模型`);
        
        // 使用 setTimeout 来降低优先级
        const delay = priority === 'low' ? 100 : priority === 'normal' ? 50 : 0;
        
        setTimeout(async () => {
            try {
                const results = await this.loadMultipleModels(filenames, {
                    concurrent: priority === 'high' ? 5 : 2,
                    useSmartLoad: true,
                    continueOnError: true
                });
                
                console.log(`✅ 预加载完成: ${results.stats.success}/${results.stats.total}`);
                
                if (onComplete) {
                    onComplete(results);
                }
                
            } catch (error) {
                console.warn('预加载失败:', error);
                if (onComplete) {
                    onComplete({ error });
                }
            }
        }, delay);
        
        return Promise.resolve(); // 立即返回，不阻塞
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WASMModelLoader;
} else {
    window.WASMModelLoader = WASMModelLoader;
}