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
                    decodeBinary: (data) => {
                        // 简单的解压缩实现
                        return this.fallbackDecode(data);
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
    fallbackDecode(arrayBuffer) {
        try {
            const view = new DataView(arrayBuffer);
            
            // 验证魔数
            const magic = new TextDecoder().decode(arrayBuffer.slice(0, 8));
            if (magic !== 'FASTDOG1') {
                throw new Error('无效的文件格式');
            }
            
            // 读取头部信息
            const version = view.getUint32(8, true);
            const compressedLength = view.getUint32(12, true);
            
            console.log(`📋 解码信息: 版本=${version}, 压缩长度=${compressedLength}`);
            console.log(`📋 总数据长度: ${arrayBuffer.byteLength}`);
            
            // 提取压缩数据 (从偏移16开始，长度为compressedLength)
            const compressedData = arrayBuffer.slice(16, 16 + compressedLength);
            
            // 读取原始数据长度 (在压缩数据之后)
            const originalLength = view.getUint32(16 + compressedLength, true);
            console.log(`📋 原始长度: ${originalLength}`);
            console.log(`📋 压缩数据实际长度: ${compressedData.byteLength}`);
            
            // 使用pako解压缩（如果可用）
            if (typeof pako !== 'undefined') {
                try {
                    const uint8Data = new Uint8Array(compressedData);
                    
                    console.log(`🔧 尝试解压缩 ${uint8Data.length} 字节的数据`);
                    
                    // 显示压缩数据的前几个字节用于调试
                    const firstBytes = Array.from(uint8Data.slice(0, 16)).map(b => b.toString(16).padStart(2, '0')).join(' ');
                    console.log(`🔍 压缩数据前16字节: ${firstBytes}`);
                    
                    // 检查zlib头部 (78 da 是标准zlib头部)
                    if (uint8Data.length >= 2) {
                        const header = (uint8Data[0] << 8) | uint8Data[1];
                        console.log(`🔍 压缩头部: 0x${header.toString(16)}`);
                    }
                    
                    // 直接使用标准zlib解压缩
                    const decompressed = pako.inflate(uint8Data);
                    console.log('✅ 标准zlib解压成功');
                    
                    const result = new TextDecoder().decode(decompressed);
                    console.log(`✅ 解压缩完成，得到 ${result.length} 字符的JSON数据`);
                    return result;
                } catch (error) {
                    console.error('所有解压缩方法都失败:', error);
                    throw new Error(`解压缩失败: ${error.message}`);
                }
            } else {
                throw new Error('需要pako库进行解压缩');
            }
        } catch (error) {
            console.error('JavaScript解码失败:', error);
            throw error;
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
            console.error('获取模型信息失败:', error);
            throw error;
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
            console.error('获取模型清单失败:', error);
            throw error;
        }
    }

    /**
     * 使用blob方式加载模型（推荐）
     */
    async loadModelBlob(filename, onProgress = null) {
        const startTime = performance.now();
        try {
            console.log(`🚀 开始blob方式加载模型: ${filename}`);
            
            const fetchStart = performance.now();
            const response = await fetch(`${this.baseUrl}/models/${filename}/blob`, {
                headers: this.getHeaders()
            });
            const fetchTime = performance.now() - fetchStart;
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // 获取响应头信息
            const originalSize = response.headers.get('X-Original-Size');
            const compressedSize = response.headers.get('X-Compressed-Size');
            const compressionRatio = response.headers.get('X-Compression-Ratio');
            const format = response.headers.get('X-Format');

            console.log(`📊 模型信息:`);
            console.log(`   原始大小: ${originalSize} bytes`);
            console.log(`   压缩大小: ${compressedSize} bytes`);
            console.log(`   压缩比: ${compressionRatio}`);
            console.log(`   格式: ${format}`);

            // 直接获取ArrayBuffer数据（优化性能）
            const downloadStart = performance.now();
            const arrayBuffer = await response.arrayBuffer();
            const downloadTime = performance.now() - downloadStart;
            console.log(`✅ 数据下载完成: ${arrayBuffer.byteLength} bytes (耗时: ${downloadTime.toFixed(2)}ms)`);
            
            // 解码二进制数据
            const decodeStart = performance.now();
            const decodedData = await this.decodeBinaryData(arrayBuffer);
            const decodeTime = performance.now() - decodeStart;
            
            // 转换为完整的Three.js模型（包含材质）
            const convertStart = performance.now();
            const modelResult = await this.convertToThreeModel(decodedData);
            const convertTime = performance.now() - convertStart;
            
            const totalTime = performance.now() - startTime;
            console.log(`⚡ Blob模式性能统计:`);
            console.log(`   网络请求: ${fetchTime.toFixed(2)}ms`);
            console.log(`   数据下载: ${downloadTime.toFixed(2)}ms`);
            console.log(`   数据解码: ${decodeTime.toFixed(2)}ms`);
            console.log(`   模型转换: ${convertTime.toFixed(2)}ms`);
            console.log(`   总耗时: ${totalTime.toFixed(2)}ms`);
            
            return {
                model: modelResult.model,
                geometry: modelResult.geometry, // 保持向后兼容
                format: format || 'blob',
                originalSize: parseInt(originalSize),
                compressedSize: parseInt(compressedSize),
                compressionRatio: parseFloat(compressionRatio),
                performanceStats: {
                    fetchTime: fetchTime.toFixed(2),
                    downloadTime: downloadTime.toFixed(2),
                    decodeTime: decodeTime.toFixed(2),
                    convertTime: convertTime.toFixed(2),
                    totalTime: totalTime.toFixed(2)
                }
            };
            
        } catch (error) {
            console.error('Blob方式加载模型失败:', error);
            throw error;
        }
    }

    /**
     * 使用流式传输加载模型
     */
    async loadModelStream(filename, onProgress = null) {
        const startTime = performance.now();
        try {
            console.log(`🌊 开始流式加载模型: ${filename}`);
            
            const fetchStart = performance.now();
            const response = await fetch(`${this.baseUrl}/models/${filename}/binary`, {
                headers: this.getHeaders()
            });
            const fetchTime = performance.now() - fetchStart;
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentLength = parseInt(response.headers.get('Content-Length'));
            const reader = response.body.getReader();
            const chunks = [];
            let receivedLength = 0;

            const streamStart = performance.now();
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
            const streamTime = performance.now() - streamStart;

            // 合并所有chunks
            const mergeStart = performance.now();
            const arrayBuffer = new ArrayBuffer(receivedLength);
            const uint8Array = new Uint8Array(arrayBuffer);
            let position = 0;
            
            for (const chunk of chunks) {
                uint8Array.set(chunk, position);
                position += chunk.length;
            }
            const mergeTime = performance.now() - mergeStart;

            console.log(`✅ 流式下载完成: ${receivedLength} bytes (耗时: ${streamTime.toFixed(2)}ms)`);
            
            // 解码二进制数据
            const decodeStart = performance.now();
            const decodedData = await this.decodeBinaryData(arrayBuffer);
            const decodeTime = performance.now() - decodeStart;
            
            // 转换为完整的Three.js模型（包含材质）
            const convertStart = performance.now();
            const modelResult = await this.convertToThreeModel(decodedData);
            const convertTime = performance.now() - convertStart;
            
            const totalTime = performance.now() - startTime;
            console.log(`⚡ Stream模式性能统计:`);
            console.log(`   网络请求: ${fetchTime.toFixed(2)}ms`);
            console.log(`   流式下载: ${streamTime.toFixed(2)}ms`);
            console.log(`   数据合并: ${mergeTime.toFixed(2)}ms`);
            console.log(`   数据解码: ${decodeTime.toFixed(2)}ms`);
            console.log(`   模型转换: ${convertTime.toFixed(2)}ms`);
            console.log(`   总耗时: ${totalTime.toFixed(2)}ms`);
            
            return { 
                model: modelResult.model,
                geometry: modelResult.geometry, // 保持向后兼容
                format: 'stream',
                size: receivedLength,
                performanceStats: {
                    fetchTime: fetchTime.toFixed(2),
                    streamTime: streamTime.toFixed(2),
                    mergeTime: mergeTime.toFixed(2),
                    decodeTime: decodeTime.toFixed(2),
                    convertTime: convertTime.toFixed(2),
                    totalTime: totalTime.toFixed(2)
                }
            };
            
        } catch (error) {
            console.error('流式加载模型失败:', error);
            throw error;
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
            // 将ArrayBuffer转换为Uint8Array
            const uint8Array = new Uint8Array(arrayBuffer);
            
            // 验证魔数
            const magicBytes = uint8Array.slice(0, 8);
            const magic = new TextDecoder().decode(magicBytes);
            
            if (magic !== 'FASTDOG1') {
                throw new Error('无效的二进制格式');
            }

            // 读取版本号
            const version = new DataView(arrayBuffer, 8, 4).getUint32(0, true);
            console.log(`📋 二进制格式版本: ${version}`);

            // 读取压缩数据长度
            const compressedLength = new DataView(arrayBuffer, 12, 4).getUint32(0, true);
            console.log(`📋 压缩长度: ${compressedLength}`);
            
            // 提取压缩数据 (从偏移16开始，长度为compressedLength)
            const compressedData = arrayBuffer.slice(16, 16 + compressedLength);
            
            // 读取原始数据长度 (在压缩数据之后)
            const originalLength = new DataView(arrayBuffer, 16 + compressedLength, 4).getUint32(0, true);
            console.log(`📋 原始长度: ${originalLength}`);
            console.log(`📋 压缩数据实际长度: ${compressedData.byteLength}`);
            
            // 使用解码器解压缩
            if (this.wasmModule && this.wasmModule.decodeBinary) {
                // 使用WASM或JavaScript解码器
                const result = this.wasmModule.decodeBinary(arrayBuffer);
                return JSON.parse(result);
            } else {
                // 直接使用pako库解压缩
                if (typeof pako !== 'undefined') {
                    try {
                        const uint8Data = new Uint8Array(compressedData);
                        
                        // 显示压缩数据的前几个字节用于调试
                        const firstBytes = Array.from(uint8Data.slice(0, 16)).map(b => b.toString(16).padStart(2, '0')).join(' ');
                        console.log(`🔍 压缩数据前16字节: ${firstBytes}`);
                        
                        // 检查zlib头部 (78 da 是标准zlib头部)
                        if (uint8Data.length >= 2) {
                            const header = (uint8Data[0] << 8) | uint8Data[1];
                            console.log(`🔍 压缩头部: 0x${header.toString(16)}`);
                        }
                        
                        // 直接使用标准zlib解压缩
                        const decompressed = pako.inflate(uint8Data);
                        console.log('✅ 标准zlib解压成功');
                        
                        const result = new TextDecoder().decode(decompressed);
                        console.log(`✅ 解压缩完成，得到 ${result.length} 字符的JSON数据`);
                        return JSON.parse(result);
                    } catch (error) {
                        console.error('解压缩失败:', error);
                        throw new Error(`解压缩失败: ${error.message}`);
                    }
                } else {
                    throw new Error('解码器和pako库都不可用');
                }
            }
            
        } catch (error) {
            console.error('解码二进制数据失败:', error);
            throw error;
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
            // 检查是否有GLTFLoader可用
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
            
        } catch (error) {
            console.error('转换Three.js模型失败:', error);
            throw error;
        }
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
     * 渐进式加载（分片加载）
     */
    async loadModelProgressive(filename, onProgress = null) {
        try {
            console.log(`📦 开始渐进式加载模型: ${filename}`);
            
            // 获取模型清单
            const manifest = await this.getModelManifest(filename);
            
            // 首先加载预览版本
            if (onProgress) {
                onProgress({ stage: 'preview', percentage: 0 });
            }
            
            // 这里可以实现分片加载逻辑
            // 例如先加载低精度版本，再逐步加载高精度版本
            
            return await this.loadModelBlob(filename, onProgress);
            
        } catch (error) {
            console.error('渐进式加载失败:', error);
            throw error;
        }
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WASMModelLoader;
} else {
    window.WASMModelLoader = WASMModelLoader;
}