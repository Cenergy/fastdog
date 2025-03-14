# FastDog

FastDog是一个基于FastAPI的现代化Web后端框架，提供了完整的用户认证、权限管理和API开发功能。

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

3. **服务层架构**
   - 将业务逻辑从路由处理器中分离出来
   - 实现用户服务层，集中管理用户相关业务逻辑
   - 提高代码可维护性和可测试性

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

## 项目结构

```
fastdog/
├── api/                  # API路由
│   └── v1/               # API v1版本
├── apps/                 # 应用模块
│   └── users/            # 用户模块
├── core/                 # 核心功能
│   ├── middleware/       # 中间件
│   ├── config.py         # 配置
│   ├── database.py       # 数据库
│   ├── security.py       # 安全
│   └── cache.py          # 缓存
├── migrations/           # 数据库迁移
├── tests/                # 测试
├── utils/                # 工具函数
├── .env.example          # 环境变量示例
├── main.py               # 应用入口
├── requirements.txt      # 依赖
└── README.md             # 说明文档
```

## 贡献

欢迎提交Pull Request或Issue来改进项目。

## 许可

MIT