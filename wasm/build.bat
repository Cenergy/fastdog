@echo off
chcp 65001 >nul
REM FastDog WASM Decoder Build Script for Windows
REM Build WebAssembly module

echo Starting FastDog WASM decoder build...

REM Check if wasm-pack is installed
wasm-pack --version >nul 2>&1
if %errorlevel% neq 0 (
    echo wasm-pack not installed, please install from:
    echo https://rustwasm.github.io/wasm-pack/installer/
    pause
    exit /b 1
)

REM Check if Rust is installed
rustc --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Rust not installed, please install from:
    echo https://rustup.rs/
    pause
    exit /b 1
)

REM Clean previous builds
echo Cleaning previous builds...
if exist pkg rmdir /s /q pkg
if exist target rmdir /s /q target

REM Build WASM package
echo Building WASM package...
wasm-pack build --target web --out-dir pkg --release

if %errorlevel% equ 0 (
    echo Build successful!
    echo Output directory: pkg/
    echo Generated files:
    dir pkg
    
    REM Copy to static files directory
    echo Copying to static files directory...
    if not exist "..\static\wasm" mkdir "..\static\wasm"
    copy "pkg\fastdog_decoder.js" "..\static\wasm\"
    copy "pkg\fastdog_decoder_bg.wasm" "..\static\wasm\"
    copy "pkg\fastdog_decoder.d.ts" "..\static\wasm\"
    
    echo Files copied to ..\static\wasm\
    echo Build complete! You can now use the WASM decoder in HTML.
) else (
    echo Build failed!
    pause
    exit /b 1
)

pause