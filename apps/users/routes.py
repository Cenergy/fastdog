from fastapi import APIRouter, HTTPException, Depends
from .crud import create_user, get_users, get_user, update_user, delete_user
from .models import UserCreate, User_Pydantic
from api.v1.deps import get_current_active_user, get_current_superuser

router = APIRouter()

@router.post("/", response_model=User_Pydantic)
async def create_new_user(user: UserCreate):
    # 通过API创建的用户，明确设置is_admin_creation=False
    return await create_user(user, is_admin_creation=False)

@router.get("/", response_model=list[User_Pydantic])
async def read_users(skip: int = 0, limit: int = 100, current_user: User_Pydantic = Depends(get_current_superuser)):
    return await get_users(skip=skip, limit=limit)

@router.get("/{user_id}", response_model=User_Pydantic)
async def read_user(user_id: int, current_user: User_Pydantic = Depends(get_current_active_user)):
    return await get_user(user_id)

@router.put("/{user_id}", response_model=User_Pydantic)
async def update_user_info(user_id: int, user: UserCreate, current_user: User_Pydantic = Depends(get_current_active_user)):
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="没有权限修改其他用户信息")
    return await update_user(user_id, user)

@router.delete("/{user_id}")
async def remove_user(user_id: int, current_user: User_Pydantic = Depends(get_current_superuser)):
    return await delete_user(user_id)