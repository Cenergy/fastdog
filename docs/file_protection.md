# 文件访问保护功能

## 概述

为了保护敏感的模型文件，系统实现了对特定文件类型的直接 HTTP 访问限制。目前受保护的文件类型包括：
- `.gltf` 文件
- `.fastdog` 文件

## 实现原理

### 1. 自定义静态文件处理器

创建了 `ProtectedStaticFiles` 类，继承自 FastAPI 的 `StaticFiles`，用于拦截对受保护文件类型的直接访问。

**文件位置**: `core/protected_static.py`

### 2. 访问控制逻辑

- **受保护路径**: `/static/uploads/models/` 目录下的文件
- **受保护扩展名**: `.gltf` 和 `.fastdog`
- **访问结果**: 直接访问返回 `403 Forbidden`

### 3. API 访问不受影响

通过 API 端点访问模型文件不受限制，例如：
- `/api/v1/resources/models/{filename}`
- `/api/v1/resources/models/{filename}/info`
- `/api/v1/resources/models/{filename}/binary`

## 配置说明

### 修改受保护的文件类型

在 `core/static.py` 文件中修改 `protected_extensions` 参数：

```python
app.mount("/static", ProtectedStaticFiles(
    directory=static_dir,
    protected_extensions=[".gltf", ".fastdog", ".新扩展名"],
    protected_paths=["/uploads/models/"]
), name="static")
```

### 修改受保护的路径

在 `core/static.py` 文件中修改 `protected_paths` 参数：

```python
app.mount("/static", ProtectedStaticFiles(
    directory=static_dir,
    protected_extensions=[".gltf", ".fastdog"],
    protected_paths=["/uploads/models/", "/uploads/sensitive/", "/private/"]
), name="static")
```

## 测试验证

### 运行测试脚本

```bash
python test_file_protection.py
```

### 测试结果说明

- ✅ **受保护文件**: 直接访问返回 403 Forbidden
- ✅ **非受保护文件**: 正常访问或返回 404（文件不存在）
- ✅ **API 端点**: 正常访问，不受限制

### 手动测试

1. **直接访问受保护文件**（应该被拒绝）:
   ```
   http://localhost:8008/static/uploads/models/example.gltf
   ```

2. **通过 API 访问**（应该正常）:
   ```
   http://localhost:8008/api/v1/resources/models/example.gltf
   ```

## 安全考虑

1. **文件扩展名检查**: 基于文件扩展名进行保护，确保重命名文件不能绕过限制
2. **路径检查**: 只对特定路径下的文件进行保护，避免影响其他静态资源
3. **API 访问控制**: API 端点可以实现更细粒度的访问控制（如用户认证）

## 注意事项

1. **性能影响**: 每个静态文件请求都会经过保护检查，但性能影响很小
2. **缓存**: 浏览器可能缓存 403 响应，测试时注意清除缓存
3. **日志记录**: 可以在 `ProtectedStaticFiles` 中添加日志记录来监控访问尝试

## 扩展功能

### 添加日志记录

```python
import logging

class ProtectedStaticFiles(StaticFiles):
    def _is_protected_file(self, path: str) -> bool:
        if "/uploads/models/" in path:
            _, ext = os.path.splitext(path)
            if ext.lower() in self.protected_extensions:
                logging.warning(f"Blocked access to protected file: {path}")
                return True
        return False
```

### 添加白名单 IP

```python
class ProtectedStaticFiles(StaticFiles):
    def __init__(self, directory: str, protected_extensions: List[str] = None, 
                 whitelist_ips: List[str] = None, **kwargs):
        super().__init__(directory=directory, **kwargs)
        self.protected_extensions = protected_extensions or []
        self.whitelist_ips = whitelist_ips or []
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            # 检查客户端 IP
            client_ip = scope.get("client", ["", 0])[0]
            if client_ip in self.whitelist_ips:
                await super().__call__(scope, receive, send)
                return
            
            # 继续原有的保护逻辑
            # ...
```