from tortoise.exceptions import DoesNotExist, IntegrityError
from fastapi import HTTPException
from .models import User, User_Pydantic
from core.middleware.security import get_password_hash

async def get_user(user_id: int):
    try:
        return await User_Pydantic.from_queryset_single(User.get(id=user_id))
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

async def get_user_by_username_or_email(username_or_email: str):
    """通过用户名或邮箱获取用户

    Args:
        username_or_email: 用户名或邮箱

    Returns:
        User: 用户对象，如果未找到则返回None
    """
    try:
        return await User.get(email=username_or_email)
    except DoesNotExist:
        try:
            return await User.get(username=username_or_email)
        except DoesNotExist:
            return None

async def get_user_by_username_or_email(username_or_email: str):
    """通过用户名或邮箱获取用户

    Args:
        username_or_email: 用户名或邮箱

    Returns:
        User: 用户对象，如果未找到则返回None
    """
    try:
        return await User.get(email=username_or_email)
    except DoesNotExist:
        try:
            return await User.get(username=username_or_email)
        except DoesNotExist:
            return None

async def get_user_by_verification_token(token: str):
    """通过验证令牌获取用户

    Args:
        token: 验证令牌

    Returns:
        User: 用户对象，如果未找到则返回None
    """
    try:
        return await User.get(email_verification_token=token)
    except DoesNotExist:
        return None

async def create_user(user_data, is_admin_creation=False):
    try:
        # 检查是否为Pydantic模型实例，如果是则转换为字典
        if hasattr(user_data, 'model_dump'):
            user_dict = user_data.model_dump()
            # 如果是UserCreate，需要处理密码字段
            if 'password' in user_dict:
                password = user_dict.pop('password')  # 从字典中移除密码
                user_dict['hashed_password'] = get_password_hash(password)  # 添加哈希后的密码
        else:
            user_dict = user_data
        
        # 根据创建来源设置email_verified
        # 如果是管理后台创建（超级用户），允许直接设置email_verified为True
        # 如果是API创建，强制设置email_verified为False，确保用户必须通过邮箱验证
        if not is_admin_creation:
            user_dict['email_verified'] = False
        elif 'email_verified' not in user_dict:
            # 管理后台创建但未指定email_verified时，默认设为True
            user_dict['email_verified'] = True
        
        user_obj = await User.create(**user_dict)
        return await User_Pydantic.from_tortoise_orm(user_obj)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Username or email already exists")

async def get_users(skip: int = 0, limit: int = 100):
    return await User_Pydantic.from_queryset(User.all().offset(skip).limit(limit))

async def update_user(user_id: int, user_data: dict):
    try:
        db_user = await User.get(id=user_id)
        if "password" in user_data:
            hashed_password = get_password_hash(user_data["password"])
            del user_data["password"]
            user_data["hashed_password"] = hashed_password
        await db_user.update_from_dict(user_data).save()
        return await User_Pydantic.from_tortoise_orm(db_user)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

async def delete_user(user_id: int):
    deleted_count = await User.filter(id=user_id).delete()
    if not deleted_count:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}