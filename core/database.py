from tortoise import Tortoise
from core.config import settings
from core.app_models import ALL_MODELS
from core.database_config import get_db_config
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

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