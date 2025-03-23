from tortoise import Tortoise
import asyncio
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from core.config import settings
from apps.albums.models import Photo


async def update_photos_original_url():
    """更新照片记录中的original_url字段，使用thumbnail_url替代空值或默认值"""
    
    # 初始化Tortoise ORM
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={"models": ["apps.albums.models"]}
    )
    
    # 查找所有有thumbnail_url但original_url为空或默认值的记录
    photos = await Photo.filter(thumbnail_url__isnull=False).all()
    updated_count = 0
    
    for photo in photos:
        # 检查original_url是否为空或默认值
        if (not photo.original_url or 
            photo.original_url == [] or 
            photo.original_url == ["/static/default.png"] or 
            photo.original_url == "/static/default.png"):
            # 更新original_url为thumbnail_url
            photo.original_url = [photo.thumbnail_url]
            await photo.save()
            updated_count += 1
            print(f"更新照片 ID: {photo.id}, 将original_url设置为: {photo.thumbnail_url}")
    
    print(f"共更新了 {updated_count} 条记录")
    
    # 关闭数据库连接
    await Tortoise.close_connections()


if __name__ == "__main__":
    # 运行迁移脚本
    asyncio.run(update_photos_original_url()) 