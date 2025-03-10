from fastapi import FastAPI
from fastadmin import fastapi_app as admin_app
from fastadmin import TortoiseModelAdmin, register, ModelAdmin
from apps.users.models import User
from core.config import settings
from apps.users.crud import get_user_by_username_or_email
from core.security import verify_password

# 创建用户管理类
@register(User)
class UserAdmin(TortoiseModelAdmin):
    """用户管理类"""
    model = User
    icon = "user"
    display_name = "用户管理"
    searchable_fields = ["username", "email"]
    exclude_fields = ["hashed_password", "email_verification_token", 
                     "password_reset_token", "password_reset_token_expires"]
    list_display = ["id", "username", "email", "is_active", "is_superuser", "role", "created_at"]
    list_per_page = 15
    ordering = ["-created_at"]
    
    async def authenticate(self, username: str, password: str) -> int | None:
        """验证用户名和密码
        
        Args:
            username: 用户名或邮箱
            password: 密码
            
        Returns:
            int | None: 认证成功返回用户ID，失败返回None
        """
        # 获取用户
        user = await get_user_by_username_or_email(username)
        if not user:
            return None
            
        # 验证用户是否是管理员或超级用户
        if not user.is_superuser and user.role != "admin":
            return None
            
        # 验证密码
        if not verify_password(password, user.hashed_password):
            return None
            
        # 验证邮箱是否已验证
        if not user.email_verified:
            return None
            
        return user.id

def setup_admin(app: FastAPI):
    """
    设置FastAdmin
    
    Args:
        app (FastAPI): FastAPI应用实例
    """
    # 配置FastAdmin
    admin_app.title = settings.PROJECT_NAME + " 管理后台"
    admin_app.logo = "/static/logo.png"
    admin_app.theme = "blue"
    
    # 设置用户模型和用户名字段
    import os
    # 确保使用正确的模型路径
    os.environ["ADMIN_USER_MODEL"] = "apps.users.models.User"
    os.environ["ADMIN_USER_MODEL_USERNAME_FIELD"] = "username"
    os.environ["ADMIN_SECRET_KEY"] = settings.SECRET_KEY
    
    # 挂载FastAdmin
    app.mount("/admin", admin_app)
    return app