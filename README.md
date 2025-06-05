# FastDog

FastDog是一个基于FastAPI的现代化Web后端框架，提供了完整的用户认证、权限管理和API开发功能。fastdog的设计目标是提供一个简单易用的后端开发框架，帮助开发者快速构建高性能的Web应用。
## 特点
- 基于FastAPI，提供高性能的异步API
- 基于Tortoise ORM的数据库操作

## 主要特性

- 基于FastAPI的高性能异步API
- JWT认证系统，支持访问令牌和刷新令牌
- 基于Tortoise ORM的数据库操作
- Redis缓存层，提高性能
- 服务层架构，分离业务逻辑
- 完整的用户管理系统
- 邮箱验证功能
- 密码安全存储（Argon2哈希）
- API限流保护
- 全局异常处理
- 结构化日志记录

## 最近改进

1. **安全性增强**
   - 从环境变量读取密钥，增强安全性
   - 实现JWT刷新令牌机制，缩短访问令牌有效期
   - 令牌类型验证，防止令牌混用

2. **Redis缓存层**
   - 添加Redis缓存支持，提高频繁访问数据的响应速度
   - 实现缓存装饰器，方便缓存函数结果
   - 自动缓存失效管理
   - 新增缓存预热机制，减少冷启动时间

3. **服务层架构**
   - 将业务逻辑从路由处理器中分离出来
   - 实现用户服务层，集中管理用户相关业务逻辑
   - 提高代码可维护性和可测试性
   - 新增任务调度服务，支持定时任务管理

4. **API增强**
   - 新增健康检查端点(/health)
   - 添加数据库连接状态监控
   - 实现API限流保护
   - 优化全局异常处理

## 快速开始

1. 克隆仓库
```bash
git clone https://github.com/yourusername/fastdog.git
cd fastdog
```

### 本地启动
#### 后端
启动项目需要以下环境：
- Python 3.11

#### 方法一（推荐）：使用 uv 安装依赖
1. 安装 uv
```sh
pip install uv
```

2. 创建并激活虚拟环境
```sh
uv venv
source .venv/bin/activate  # Linux/Mac
# 或
.\.venv\Scripts\activate  # Windows
```

3. 安装依赖
```sh
uv add pyproject.toml
```

4. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，设置你的环境变量
```

5. 运行应用
```bash
uvicorn main:app --reload
```

6. 访问API文档
```
http://localhost:8000/docs
```

## 🔧 配置说明

### 环境变量配置
项目使用`.env`文件进行配置，主要配置项包括：

```bash
# 基础配置
PROJECT_NAME="Fast Go Go"
SECRET_KEY="your-secret-key"
ADMIN_SECRET_KEY="your-admin-secret-key"

# 数据库配置
DATABASE_URL="sqlite://./data/test.db"

# 邮件配置
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-password"

# AI服务配置
DASHSCOPE_API_KEY="your-dashscope-key"
HUGGINGFACE_API_KEY="your-huggingface-key"

# 管理员配置
DEFAULT_ADMIN_EMAIL="admin@example.com"
DEFAULT_ADMIN_USERNAME="admin"
DEFAULT_ADMIN_PASSWORD="admin123"
```

### 部署配置
项目提供了完整的部署脚本和配置：

- `deploy.sh` - 自动化部署脚本
- `deploy/nginx.conf` - Nginx配置
- `deploy/gunicorn_conf.py` - Gunicorn配置
- `deploy/fastdog.conf` - Supervisor配置

## 📚 API文档

### 主要API端点

- **认证相关**
  - `POST /api/v1/auth/login` - 用户登录
  - `POST /api/v1/auth/register` - 用户注册
  - `POST /api/v1/auth/refresh` - 刷新令牌

- **用户管理**
  - `GET /api/v1/users/me` - 获取当前用户信息
  - `PUT /api/v1/users/me` - 更新用户信息

- **相册系统**
  - `GET /api/v1/albums/` - 获取相册列表
  - `POST /api/v1/albums/` - 创建相册
  - `POST /api/v1/albums/{id}/photos` - 上传照片

- **坐标转换**
  - `POST /api/v1/converters/coordinate` - 坐标系转换

- **创意生成**
  - `POST /api/v1/ideas/generate` - AI创意生成

- **系统监控**
  - `GET /health` - 健康检查
  - `GET /docs` - API文档

## 贡献

欢迎提交Pull Request或Issue来改进项目。

## 许可

MIT