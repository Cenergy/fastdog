from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from apps.users.models import User_Pydantic
from apps.users.crud import get_users, get_user, update_user, delete_user
from api.v1.deps import get_current_superuser

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=List[User_Pydantic])
async def list_users(skip: int = 0, limit: int = 10, current_user: User_Pydantic = Depends(get_current_superuser)):
    """获取用户列表"""
    return await get_users(skip=skip, limit=limit)

@router.get("/users/{user_id}", response_model=User_Pydantic)
async def get_user_detail(user_id: int, current_user: User_Pydantic = Depends(get_current_superuser)):
    """获取用户详情"""
    user = await get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

@router.put("/users/{user_id}", response_model=User_Pydantic)
async def update_user_detail(user_id: int, user_data: User_Pydantic, current_user: User_Pydantic = Depends(get_current_superuser)):
    """更新用户信息"""
    user = await update_user(user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

@router.delete("/users/{user_id}")
async def delete_user_detail(user_id: int, current_user: User_Pydantic = Depends(get_current_superuser)):
    """删除用户"""
    result = await delete_user(user_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return {"message": "用户已成功删除"}