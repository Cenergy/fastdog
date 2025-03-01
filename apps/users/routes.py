from fastapi import APIRouter, HTTPException, Depends
from .crud import create_user, get_users, get_user, update_user, delete_user
from .models import UserCreate, User_Pydantic

router = APIRouter()

@router.post("/", response_model=User_Pydantic)
async def create_new_user(user: UserCreate):
    return await create_user(user)

@router.get("/", response_model=list[User_Pydantic])
async def read_users(skip: int = 0, limit: int = 100):
    return await get_users(skip=skip, limit=limit)

@router.get("/{user_id}", response_model=User_Pydantic)
async def read_user(user_id: int):
    return await get_user(user_id)

@router.put("/{user_id}", response_model=User_Pydantic)
async def update_user_info(user_id: int, user: UserCreate):
    return await update_user(user_id, user)

@router.delete("/{user_id}")
async def remove_user(user_id: int):
    return await delete_user(user_id)