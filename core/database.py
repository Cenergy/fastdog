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

        # 创建默认管理员账户
        from apps.users.crud import get_user_by_username_or_email, create_user
        from core.security import get_password_hash

        admin_email = "admin@example.com"
        admin_user = await get_user_by_username_or_email(admin_email)
        
        if not admin_user:
            logger.info("正在创建默认管理员账户...")
            admin_data = {
                "email": admin_email,
                "username": "admin",
                "hashed_password": get_password_hash("admin123"),
                "is_active": True,
                "is_superuser": True,
                "email_verified": True,
                "role": "admin"
            }
            await create_user(admin_data)
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