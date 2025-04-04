from tortoise import Tortoise
from core.config import settings
from core.app_models import ALL_MODELS
from core.database_config import get_db_config, get_db_type
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import pandas as pd

TORTOISE_ORM = get_db_config()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def init_db():
    try:
        logger.info("正在初始化数据库连接...")
        await Tortoise.init(
            config=TORTOISE_ORM
        )
        logger.info("数据库连接初始化成功")

        # 生成数据库 schema
        logger.info("正在生成数据库 schema...")
        await Tortoise.generate_schemas(safe=True)
        logger.info("数据库 schema 生成成功")

        # 创建默认管理员账户
        from apps.users.crud import get_user_by_username_or_email, create_user
        from core.security import get_password_hash

        admin_email = settings.DEFAULT_ADMIN_EMAIL
        admin_user = await get_user_by_username_or_email(admin_email)
        
        if not admin_user:
            logger.info("正在创建默认管理员账户...")
            admin_data = {
                "email": admin_email,
                "username": settings.DEFAULT_ADMIN_USERNAME,
                "hashed_password": get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                "is_active": True,
                "is_superuser": True,
                "email_verified": True,
                "role": "admin"
            }
            await create_user(admin_data, is_admin_creation=True)
            logger.info("默认管理员账户创建成功")
        else:
            logger.info("默认管理员账户已存在，跳过创建")


    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise Exception(f"数据库初始化失败: {str(e)}")

async def close_db():
    try:
        logger.info("正在关闭数据库连接...")
        await Tortoise.close_connections()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接时发生错误: {str(e)}")
        raise Exception(f"关闭数据库连接失败: {str(e)}")

async def get_connection_for_pandas():
    """
    获取可用于pandas的数据库连接对象
    
    Returns:
        connection: 可用于pandas.read_sql的数据库连接对象
    
    Example:
        ```python
        import pandas as pd
        from core.database import get_connection_for_pandas
        
        # 在异步函数中使用
        async def get_data():
            conn = await get_connection_for_pandas()
            df = pd.read_sql("SELECT * FROM users", conn)
            return df
        ```
    """
    try:
        # 获取Tortoise ORM的连接对象
        connection = Tortoise.get_connection('default')
        
        # 获取数据库类型
        db_type = get_db_type(settings.DATABASE_URL)
        
        # 根据数据库类型获取适用于pandas的连接对象
        if db_type == 'sqlite':
            # 对于SQLite，我们可以直接使用connection._connection对象
            # 这是底层的sqlite3.Connection对象
            return connection._connection
        elif db_type == 'mysql':
            # 对于MySQL，我们需要获取底层的pymysql连接
            return connection._connection._conn
        elif db_type == 'postgres':
            # 对于PostgreSQL，我们需要获取底层的asyncpg连接
            # 但pandas不直接支持asyncpg连接，需要使用psycopg2
            # 这里需要额外处理，可能需要安装psycopg2包
            logger.warning("PostgreSQL连接可能需要额外配置才能与pandas一起使用")
            return connection._connection._pool._pool
        else:
            logger.error(f"不支持的数据库类型: {db_type}")
            raise ValueError(f"不支持的数据库类型: {db_type}")
    except Exception as e:
        logger.error(f"获取数据库连接失败: {str(e)}")
        raise Exception(f"获取数据库连接失败: {str(e)}")