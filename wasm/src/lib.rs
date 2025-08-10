use wasm_bindgen::prelude::*;
use web_sys::console;
use flate2::read::ZlibDecoder;
use std::io::Read;
use serde::{Deserialize, Serialize};
use serde_wasm_bindgen;

// 当 `console_error_panic_hook` 功能启用时，我们可以调用
// `set_panic_hook` 函数至少一次在初始化期间，然后我们将获得
// 更好的错误消息，如果我们的代码发生 panic。
#[cfg(feature = "console_error_panic_hook")]
extern crate console_error_panic_hook;

#[cfg(feature = "console_error_panic_hook")]
fn set_panic_hook() {
    console_error_panic_hook::set_once();
}

// 使用 `wee_alloc` 作为全局分配器。
#[cfg(feature = "wee_alloc")]
#[global_allocator]
static ALLOC: wee_alloc::WeeAlloc = wee_alloc::WeeAlloc::INIT;

// 定义解码结果结构
#[derive(Serialize, Deserialize)]
pub struct DecodeResult {
    pub success: bool,
    pub data: Option<String>,
    pub error: Option<String>,
    pub stats: DecodeStats,
}

#[derive(Serialize, Deserialize)]
pub struct DecodeStats {
    pub original_size: u32,
    pub compressed_size: u32,
    pub decode_time_ms: f64,
    pub compression_ratio: f32,
    pub format_version: u32,
}

// 日志宏
macro_rules! log {
    ( $( $t:tt )* ) => {
        console::log_1(&format!( $( $t )* ).into());
    }
}

// 简单的base64编码实现
fn base64_encode(data: &[u8]) -> String {
    const CHARS: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut result = String::new();
    
    for chunk in data.chunks(3) {
        let mut buf = [0u8; 3];
        for (i, &byte) in chunk.iter().enumerate() {
            buf[i] = byte;
        }
        
        let b = ((buf[0] as u32) << 16) | ((buf[1] as u32) << 8) | (buf[2] as u32);
        
        result.push(CHARS[((b >> 18) & 63) as usize] as char);
        result.push(CHARS[((b >> 12) & 63) as usize] as char);
        result.push(if chunk.len() > 1 { CHARS[((b >> 6) & 63) as usize] as char } else { '=' });
        result.push(if chunk.len() > 2 { CHARS[(b & 63) as usize] as char } else { '=' });
    }
    
    result
}

// 初始化函数
#[wasm_bindgen(start)]
pub fn init() {
    #[cfg(feature = "console_error_panic_hook")]
    set_panic_hook();
    
    log!("🚀 FastDog WASM Decoder initialized");
}

// 主要的解码函数
#[wasm_bindgen]
pub fn decode_fastdog_binary(data: &[u8]) -> JsValue {
    let start_time = js_sys::Date::now();
    
    match decode_binary_internal(data, start_time) {
        Ok(result) => serde_wasm_bindgen::to_value(&result).unwrap(),
        Err(error) => {
            let error_result = DecodeResult {
                success: false,
                data: None,
                error: Some(error),
                stats: DecodeStats {
                    original_size: 0,
                    compressed_size: data.len() as u32,
                    decode_time_ms: js_sys::Date::now() - start_time,
                    compression_ratio: 0.0,
                    format_version: 0,
                },
            };
            serde_wasm_bindgen::to_value(&error_result).unwrap()
        }
    }
}

// 零拷贝二进制解码结果结构
#[derive(Serialize, Deserialize)]
pub struct BinaryDecodeResult {
    pub success: bool,
    pub data_ptr: u32,
    pub data_len: u32,
    pub error: Option<String>,
    pub stats: DecodeStats,
}

// 零拷贝二进制解码函数
#[wasm_bindgen]
pub fn decode_fastdog_binary_zero_copy(data: &[u8]) -> JsValue {
    let start_time = js_sys::Date::now();
    
    match decode_binary_internal_zero_copy(data, start_time) {
        Ok(result) => serde_wasm_bindgen::to_value(&result).unwrap(),
        Err(error) => {
            let error_result = BinaryDecodeResult {
                success: false,
                data_ptr: 0,
                data_len: 0,
                error: Some(error),
                stats: DecodeStats {
                    original_size: 0,
                    compressed_size: data.len() as u32,
                    decode_time_ms: js_sys::Date::now() - start_time,
                    compression_ratio: 0.0,
                    format_version: 0,
                },
            };
            serde_wasm_bindgen::to_value(&error_result).unwrap()
        }
    }
}

// 直接返回二进制数据的解码函数
#[wasm_bindgen]
pub fn decode_fastdog_to_binary(data: &[u8]) -> Vec<u8> {
    match decode_binary_raw(data) {
        Ok(binary_data) => binary_data,
        Err(_) => Vec::new(), // 错误时返回空向量
    }
}

// 获取解码统计信息的单独函数
#[wasm_bindgen]
pub fn get_decode_stats(data: &[u8]) -> JsValue {
    let start_time = js_sys::Date::now();
    
    match decode_binary_internal(data, start_time) {
        Ok(result) => serde_wasm_bindgen::to_value(&result.stats).unwrap(),
        Err(_) => {
            let error_stats = DecodeStats {
                original_size: 0,
                compressed_size: data.len() as u32,
                decode_time_ms: js_sys::Date::now() - start_time,
                compression_ratio: 0.0,
                format_version: 0,
            };
            serde_wasm_bindgen::to_value(&error_stats).unwrap()
        }
    }
}

// 内部解码实现
fn decode_binary_internal(data: &[u8], start_time: f64) -> Result<DecodeResult, String> {
    if data.len() < 20 {
        return Err("数据太短，不是有效的 FastDog 格式".to_string());
    }
    
    let mut cursor = 0;
    
    // 1. 验证魔数 (8字节)
    let magic = &data[cursor..cursor + 8];
    if magic != b"FASTDOG1" {
        return Err(format!("无效的魔数: {:?}", magic));
    }
    cursor += 8;
    
    // 2. 读取版本号 (4字节)
    let version = u32::from_le_bytes([
        data[cursor], data[cursor + 1], data[cursor + 2], data[cursor + 3]
    ]);
    cursor += 4;
    
    if version != 1 && version != 2 {
        return Err(format!("不支持的版本: {}", version));
    }
    
    // 3. 读取压缩数据长度 (4字节)
    let compressed_len = u32::from_le_bytes([
        data[cursor], data[cursor + 1], data[cursor + 2], data[cursor + 3]
    ]) as usize;
    cursor += 4;
    
    // 4. 读取压缩数据
    if cursor + compressed_len > data.len() {
        return Err("压缩数据长度超出范围".to_string());
    }
    
    let compressed_data = &data[cursor..cursor + compressed_len];
    cursor += compressed_len;
    
    // 5. 读取原始数据长度 (4字节) - 用于验证
    if cursor + 4 > data.len() {
        return Err("缺少原始数据长度字段".to_string());
    }
    
    let original_len = u32::from_le_bytes([
        data[cursor], data[cursor + 1], data[cursor + 2], data[cursor + 3]
    ]);
    
    // 6. 解压缩数据
    let mut decoder = ZlibDecoder::new(compressed_data);
    let mut decompressed = Vec::new();
    
    match decoder.read_to_end(&mut decompressed) {
        Ok(_) => {
            // 验证解压后的数据长度
            if decompressed.len() != original_len as usize {
                return Err(format!(
                    "解压后数据长度不匹配: 期望 {}, 实际 {}",
                    original_len,
                    decompressed.len()
                ));
            }
            
            let decode_time = js_sys::Date::now() - start_time;
            
            // 根据版本处理数据
            let data_result = if version == 1 {
                // 版本1: JSON格式，转换为UTF-8字符串
                match String::from_utf8(decompressed) {
                    Ok(json_str) => json_str,
                    Err(e) => return Err(format!("UTF-8 解码失败: {}", e)),
                }
            } else if version == 2 {
                // 版本2: GLB二进制格式，使用简单的base64编码
                let base64_str = base64_encode(&decompressed);
                format!("{{\"type\":\"glb\",\"data\":\"{}\"}}", base64_str)
            } else {
                return Err(format!("不支持的版本: {}", version));
            };
            
            Ok(DecodeResult {
                success: true,
                data: Some(data_result),
                error: None,
                stats: DecodeStats {
                    original_size: original_len,
                    compressed_size: compressed_len as u32,
                    decode_time_ms: decode_time,
                    compression_ratio: compressed_len as f32 / original_len as f32,
                    format_version: version,
                },
            })
        }
        Err(e) => Err(format!("解压缩失败: {}", e)),
    }
}

// 零拷贝解码内部实现
fn decode_binary_internal_zero_copy(data: &[u8], start_time: f64) -> Result<BinaryDecodeResult, String> {
    let decompressed = decode_binary_raw(data)?;
    let decode_time = js_sys::Date::now() - start_time;
    
    // 将数据存储在静态内存中，返回指针
    let data_ptr = decompressed.as_ptr() as u32;
    let data_len = decompressed.len() as u32;
    
    // 防止数据被释放，使用Box::leak
    let leaked_data = Box::leak(decompressed.into_boxed_slice());
    
    // 获取格式信息
    let (original_len, compressed_len, version) = get_format_metadata(data)?;
    
    Ok(BinaryDecodeResult {
        success: true,
        data_ptr,
        data_len,
        error: None,
        stats: DecodeStats {
            original_size: original_len,
            compressed_size: compressed_len,
            decode_time_ms: decode_time,
            compression_ratio: compressed_len as f32 / original_len as f32,
            format_version: version,
        },
    })
}

// 原始二进制解码函数
fn decode_binary_raw(data: &[u8]) -> Result<Vec<u8>, String> {
    if data.len() < 20 {
        return Err("数据太短，不是有效的 FastDog 格式".to_string());
    }
    
    let mut cursor = 0;
    
    // 1. 验证魔数 (8字节)
    let magic = &data[cursor..cursor + 8];
    if magic != b"FASTDOG1" {
        return Err(format!("无效的魔数: {:?}", magic));
    }
    cursor += 8;
    
    // 2. 读取版本号 (4字节)
    let version = u32::from_le_bytes([
        data[cursor], data[cursor + 1], data[cursor + 2], data[cursor + 3]
    ]);
    cursor += 4;
    
    if version != 1 && version != 2 {
        return Err(format!("不支持的版本: {}", version));
    }
    
    // 3. 读取压缩数据长度 (4字节)
    let compressed_len = u32::from_le_bytes([
        data[cursor], data[cursor + 1], data[cursor + 2], data[cursor + 3]
    ]) as usize;
    cursor += 4;
    
    // 4. 读取压缩数据
    if cursor + compressed_len > data.len() {
        return Err("压缩数据长度超出范围".to_string());
    }
    
    let compressed_data = &data[cursor..cursor + compressed_len];
    cursor += compressed_len;
    
    // 5. 读取原始数据长度 (4字节) - 用于验证
    if cursor + 4 > data.len() {
        return Err("缺少原始数据长度字段".to_string());
    }
    
    let original_len = u32::from_le_bytes([
        data[cursor], data[cursor + 1], data[cursor + 2], data[cursor + 3]
    ]);
    
    // 6. 解压缩数据
    let mut decoder = ZlibDecoder::new(compressed_data);
    let mut decompressed = Vec::with_capacity(original_len as usize);
    
    match decoder.read_to_end(&mut decompressed) {
        Ok(_) => {
            // 验证解压后的数据长度
            if decompressed.len() != original_len as usize {
                return Err(format!(
                    "解压后数据长度不匹配: 期望 {}, 实际 {}",
                    original_len,
                    decompressed.len()
                ));
            }
            
            Ok(decompressed)
        }
        Err(e) => Err(format!("解压缩失败: {}", e)),
    }
}

// 获取格式元数据
fn get_format_metadata(data: &[u8]) -> Result<(u32, u32, u32), String> {
    if data.len() < 20 {
        return Err("数据太短".to_string());
    }
    
    let mut cursor = 8; // 跳过魔数
    
    // 读取版本号
    let version = u32::from_le_bytes([
        data[cursor], data[cursor + 1], data[cursor + 2], data[cursor + 3]
    ]);
    cursor += 4;
    
    // 读取压缩数据长度
    let compressed_len = u32::from_le_bytes([
        data[cursor], data[cursor + 1], data[cursor + 2], data[cursor + 3]
    ]);
    cursor += 4;
    
    cursor += compressed_len as usize; // 跳过压缩数据
    
    // 读取原始数据长度
    let original_len = u32::from_le_bytes([
        data[cursor], data[cursor + 1], data[cursor + 2], data[cursor + 3]
    ]);
    
    Ok((original_len, compressed_len, version))
}

// 验证二进制格式的函数
#[wasm_bindgen]
pub fn validate_fastdog_format(data: &[u8]) -> bool {
    if data.len() < 12 {
        return false;
    }
    
    // 检查魔数
    let magic = &data[0..8];
    if magic != b"FASTDOG1" {
        return false;
    }
    
    // 检查版本
    let version = u32::from_le_bytes([data[8], data[9], data[10], data[11]]);
    version == 1 || version == 2
}

// 获取格式信息的函数
#[wasm_bindgen]
pub fn get_format_info(data: &[u8]) -> JsValue {
    #[derive(Serialize)]
    struct FormatInfo {
        valid: bool,
        magic: String,
        version: u32,
        compressed_size: u32,
        original_size: u32,
        total_size: u32,
    }
    
    if data.len() < 20 {
        let info = FormatInfo {
            valid: false,
            magic: "N/A".to_string(),
            version: 0,
            compressed_size: 0,
            original_size: 0,
            total_size: data.len() as u32,
        };
        return serde_wasm_bindgen::to_value(&info).unwrap();
    }
    
    let magic = String::from_utf8_lossy(&data[0..8]).to_string();
    let version = u32::from_le_bytes([data[8], data[9], data[10], data[11]]);
    let compressed_size = u32::from_le_bytes([data[12], data[13], data[14], data[15]]);
    let original_size = if data.len() >= 20 + compressed_size as usize {
        u32::from_le_bytes([
            data[16 + compressed_size as usize],
            data[17 + compressed_size as usize],
            data[18 + compressed_size as usize],
            data[19 + compressed_size as usize],
        ])
    } else {
        0
    };
    
    let info = FormatInfo {
        valid: magic == "FASTDOG1" && version == 1,
        magic,
        version,
        compressed_size,
        original_size,
        total_size: data.len() as u32,
    };
    
    serde_wasm_bindgen::to_value(&info).unwrap()
}

// 性能基准测试函数
#[wasm_bindgen]
pub fn benchmark_decode(data: &[u8], iterations: u32) -> JsValue {
    #[derive(Serialize)]
    struct BenchmarkResult {
        iterations: u32,
        total_time_ms: f64,
        avg_time_ms: f64,
        min_time_ms: f64,
        max_time_ms: f64,
        success_rate: f32,
    }
    
    let mut times = Vec::new();
    let mut successes = 0;
    
    for _ in 0..iterations {
        let start = js_sys::Date::now();
        match decode_binary_internal(data, start) {
            Ok(_) => {
                successes += 1;
                times.push(js_sys::Date::now() - start);
            }
            Err(_) => {
                times.push(js_sys::Date::now() - start);
            }
        }
    }
    
    let total_time: f64 = times.iter().sum();
    let avg_time = total_time / iterations as f64;
    let min_time = times.iter().fold(f64::INFINITY, |a, &b| a.min(b));
    let max_time = times.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
    
    let result = BenchmarkResult {
        iterations,
        total_time_ms: total_time,
        avg_time_ms: avg_time,
        min_time_ms: min_time,
        max_time_ms: max_time,
        success_rate: successes as f32 / iterations as f32,
    };
    
    serde_wasm_bindgen::to_value(&result).unwrap()
}

// 流式解码器结构
#[wasm_bindgen]
pub struct StreamDecoder {
    buffer: Vec<u8>,
    header_parsed: bool,
    expected_size: Option<u32>,
    compressed_size: Option<u32>,
    original_size: Option<u32>,
    version: Option<u32>,
    chunks_processed: u32,
    total_received: u32,
}

#[derive(Serialize, Deserialize)]
pub struct StreamDecodeResult {
    pub success: bool,
    pub data: Option<String>,
    pub error: Option<String>,
    pub progress: f32,
    pub is_complete: bool,
    pub chunks_processed: u32,
    pub total_received: u32,
    pub stats: Option<DecodeStats>,
}

#[wasm_bindgen]
impl StreamDecoder {
    #[wasm_bindgen(constructor)]
    pub fn new() -> StreamDecoder {
        StreamDecoder {
            buffer: Vec::new(),
            header_parsed: false,
            expected_size: None,
            compressed_size: None,
            original_size: None,
            version: None,
            chunks_processed: 0,
            total_received: 0,
        }
    }

    #[wasm_bindgen]
    pub fn add_chunk(&mut self, chunk: &[u8]) -> JsValue {
        let start_time = js_sys::Date::now();
        
        // 添加数据块到缓冲区
        self.buffer.extend_from_slice(chunk);
        self.total_received += chunk.len() as u32;
        self.chunks_processed += 1;
        
        // 尝试解析头部信息
        if !self.header_parsed && self.buffer.len() >= 20 {
            match self.parse_header() {
                Ok(_) => {
                    log!("📋 流式解码: 头部解析成功, 预期大小: {} bytes", self.expected_size.unwrap_or(0));
                }
                Err(e) => {
                    let result = StreamDecodeResult {
                        success: false,
                        data: None,
                        error: Some(format!("头部解析失败: {}", e)),
                        progress: 0.0,
                        is_complete: false,
                        chunks_processed: self.chunks_processed,
                        total_received: self.total_received,
                        stats: None,
                    };
                    return serde_wasm_bindgen::to_value(&result).unwrap();
                }
            }
        }
        
        // 计算进度
        let progress = if let Some(expected) = self.expected_size {
            (self.buffer.len() as f32 / expected as f32).min(1.0)
        } else {
            0.0
        };
        
        // 检查是否可以尝试解码
        let can_decode = self.header_parsed && 
            self.expected_size.map_or(false, |size| self.buffer.len() >= size as usize);
        
        if can_decode {
            // 尝试完整解码
            match self.try_decode(start_time) {
                Ok(decode_result) => {
                    let result = StreamDecodeResult {
                        success: true,
                        data: decode_result.data,
                        error: None,
                        progress: 1.0,
                        is_complete: true,
                        chunks_processed: self.chunks_processed,
                        total_received: self.total_received,
                        stats: Some(decode_result.stats),
                    };
                    return serde_wasm_bindgen::to_value(&result).unwrap();
                }
                Err(e) => {
                    let result = StreamDecodeResult {
                        success: false,
                        data: None,
                        error: Some(e),
                        progress,
                        is_complete: false,
                        chunks_processed: self.chunks_processed,
                        total_received: self.total_received,
                        stats: None,
                    };
                    return serde_wasm_bindgen::to_value(&result).unwrap();
                }
            }
        }
        
        // 返回进度信息
        let result = StreamDecodeResult {
            success: true,
            data: None,
            error: None,
            progress,
            is_complete: false,
            chunks_processed: self.chunks_processed,
            total_received: self.total_received,
            stats: None,
        };
        
        serde_wasm_bindgen::to_value(&result).unwrap()
    }
    
    #[wasm_bindgen]
    pub fn reset(&mut self) {
        self.buffer.clear();
        self.header_parsed = false;
        self.expected_size = None;
        self.compressed_size = None;
        self.original_size = None;
        self.version = None;
        self.chunks_processed = 0;
        self.total_received = 0;
    }
    
    #[wasm_bindgen]
    pub fn get_progress(&self) -> f32 {
        if let Some(expected) = self.expected_size {
            (self.buffer.len() as f32 / expected as f32).min(1.0)
        } else {
            0.0
        }
    }
    
    #[wasm_bindgen]
    pub fn get_buffer_size(&self) -> u32 {
        self.buffer.len() as u32
    }
    
    #[wasm_bindgen]
    pub fn get_expected_size(&self) -> Option<u32> {
        self.expected_size
    }
}

impl StreamDecoder {
    fn parse_header(&mut self) -> Result<(), String> {
        if self.buffer.len() < 20 {
            return Err("数据不足以解析头部".to_string());
        }
        
        // 检查魔数
        let magic = &self.buffer[0..8];
        if magic != b"FASTDOG1" {
            return Err("无效的文件格式".to_string());
        }
        
        // 解析版本
        self.version = Some(u32::from_le_bytes([
            self.buffer[8], self.buffer[9], self.buffer[10], self.buffer[11]
        ]));
        
        // 解析压缩大小
        self.compressed_size = Some(u32::from_le_bytes([
            self.buffer[12], self.buffer[13], self.buffer[14], self.buffer[15]
        ]));
        
        // 计算预期总大小 (头部 + 压缩数据 + 原始大小字段)
        if let Some(compressed_size) = self.compressed_size {
            self.expected_size = Some(20 + compressed_size);
        }
        
        self.header_parsed = true;
        Ok(())
    }
    
    fn try_decode(&self, start_time: f64) -> Result<DecodeResult, String> {
        decode_binary_internal(&self.buffer, start_time)
    }
}