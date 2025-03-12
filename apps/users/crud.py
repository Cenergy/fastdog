from tortoise.exceptions import DoesNotExist, IntegrityError
from fastapi import HTTPException
from .models import User, User_Pydantic
from core.security import get_password_hash

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

async def create_user(user_dict: dict):
    try:
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