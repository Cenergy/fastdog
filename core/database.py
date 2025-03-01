from tortoise import Tortoise
from core.config import settings

from core.app_models import ALL_MODELS
def get_tortoise_config():
    return {
        "connections": {"default": settings.DATABASE_URL},
        "apps": {
            "models": {
                "models": [*ALL_MODELS, "aerich.models"],
                "default_connection": "default",
            },
        },
    }

TORTOISE_ORM = get_tortoise_config()

async def init_db():
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={'models': ALL_MODELS},
    )
    # 生成数据库 schema
    await Tortoise.generate_schemas()

async def close_db():
    await Tortoise.close_connections()