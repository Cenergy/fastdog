import pytest
from httpx import AsyncClient
from main import app
from apps.users.models import User
from core.security import verify_password

@pytest.mark.asyncio
async def test_create_user():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User",
            "is_active": True
        }
        response = await ac.post("/api/v1/users/", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        
        # 验证密码是否正确加密
        user = await User.get(email=user_data["email"])
        assert verify_password(user_data["password"], user.hashed_password)

@pytest.mark.asyncio
async def test_get_users():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/users/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_user():
    # 首先创建一个用户
    user = await User.create(
        email="get_test@example.com",
        hashed_password="testpass",
        full_name="Get Test User"
    )
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/users/{user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email
        assert data["full_name"] == user.full_name

@pytest.mark.asyncio
async def test_update_user():
    # 首先创建一个用户
    user = await User.create(
        email="update_test@example.com",
        hashed_password="testpass",
        full_name="Update Test User"
    )
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        update_data = {
            "email": "updated@example.com",
            "full_name": "Updated User",
            "password": "newpassword123"
        }
        response = await ac.put(f"/api/v1/users/{user.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == update_data["email"]
        assert data["full_name"] == update_data["full_name"]

@pytest.mark.asyncio
async def test_delete_user():
    # 首先创建一个用户
    user = await User.create(
        email="delete_test@example.com",
        hashed_password="testpass",
        full_name="Delete Test User"
    )
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete(f"/api/v1/users/{user.id}")
        assert response.status_code == 200
        
        # 验证用户是否已被删除
        response = await ac.get(f"/api/v1/users/{user.id}")
        assert response.status_code == 404