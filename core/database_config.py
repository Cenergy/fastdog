from typing import Dict, Any
from urllib.parse import urlparse
from tortoise import Tortoise
from tortoise.backends.base.config_generator import generate_config
from functools import wraps
from loguru import logger
from core.config import settings
from core.app_models import ALL_MODELS

print(ALL_MODELS)

# 不同数据库类型的连接池配置
DB_POOL_CONFIGS = {
    'sqlite': {
        "max_size": 50,  # 增加最大连接数
        "min_size": 10,  # 增加最小连接数
        "max_inactive_connection_lifetime": 180,  # 减少非活动连接的生命周期
        "connection_timeout": 30,  # 减少连接超时时间
        "retry_limit": 2,  # 减少重试次数
        "retry_interval": 0.5  # 减少重试间隔
    },
    'postgres': {
        "max_size": 50,
        "min_size": 10,
        "max_inactive_connection_lifetime": 300,
        "connection_timeout": 60,
        "retry_limit": 3,
        "retry_interval": 1
    },
    'mysql': {
        "max_size": 50,
        "min_size": 10,
        "max_inactive_connection_lifetime": 300,
        "connection_timeout": 60,
        "retry_limit": 3,
        "retry_interval": 1,
        "pool_recycle": 300
    }
}

def get_db_type(db_url: str) -> str:
    parsed = urlparse(db_url)
    return parsed.scheme.split('+')[0]

def get_db_config() -> Dict[str, Any]:
    try:
        db_type = get_db_type(settings.DATABASE_URL)
        if db_type not in DB_POOL_CONFIGS:
            logger.warning(f"未找到数据库类型 {db_type} 的连接池配置，将使用默认配置")
            db_type = 'sqlite'

        config = generate_config(
            db_url=settings.DATABASE_URL,
            app_modules={
                'models': [*ALL_MODELS, 'aerich.models']
            },
            connection_label='default'
        )
        
        # 添加对应数据库类型的连接池配置
        for db_config in config['connections'].values():
            db_config.update(DB_POOL_CONFIGS[db_type])
        
        return config
    except Exception as e:
        logger.error(f"生成数据库配置失败: {str(e)}")
        raise

# 事务装饰器
def transaction():
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                connection = Tortoise.get_connection('default')
                await connection.start_transaction()
                try:
                    result = await func(*args, **kwargs)
                    await connection.commit_transaction()
                    DatabaseMetrics().increment_transactions()
                    return result
                except Exception as e:
                    await connection.rollback_transaction()
                    DatabaseMetrics().increment_transactions(failed=True)
                    logger.error(f"事务执行失败: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"数据库错误: {str(e)}")
                raise
        return wrapper
    return decorator

# 数据库健康检查
async def check_db_health() -> bool:
    try:
        connection = Tortoise.get_connection('default')
        await connection.execute_query('SELECT 1')
        DatabaseMetrics().increment_queries()
        return True
    except Exception as e:
        DatabaseMetrics().increment_queries(failed=True)
        logger.error(f"数据库健康检查失败: {str(e)}")
        return False

# 数据库监控指标收集
class DatabaseMetrics:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.total_queries = 0
            cls._instance.failed_queries = 0
            cls._instance.total_transactions = 0
            cls._instance.failed_transactions = 0
        return cls._instance
    
    def increment_queries(self, failed: bool = False):
        self.total_queries += 1
        if failed:
            self.failed_queries += 1
    
    def increment_transactions(self, failed: bool = False):
        self.total_transactions += 1
        if failed:
            self.failed_transactions += 1
    
    def get_metrics(self) -> Dict[str, int]:
        return {
            "total_queries": self.total_queries,
            "failed_queries": self.failed_queries,
            "total_transactions": self.total_transactions,
            "failed_transactions": self.failed_transactions
        }