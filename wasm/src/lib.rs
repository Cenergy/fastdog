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
pub use console_error_panic_hook::set_panic_hook;

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
    
    if version != 1 {
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
            
            // 转换为 UTF-8 字符串
            match String::from_utf8(decompressed) {
                Ok(json_str) => {
                    let decode_time = js_sys::Date::now() - start_time;
                    
                    Ok(DecodeResult {
                        success: true,
                        data: Some(json_str),
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
                Err(e) => Err(format!("UTF-8 解码失败: {}", e)),
            }
        }
        Err(e) => Err(format!("解压缩失败: {}", e)),
    }
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
    version == 1
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