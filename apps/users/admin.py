from fastadmin import TortoiseModelAdmin, register
from .models import User
from .crud import get_user_by_username_or_email
from core.security import verify_password

@register(User)
class UserModelAdmin(TortoiseModelAdmin):
    model = User
    icon = "user"
    display_name = "用户管理"
    list_display = ["id", "username", "email", "is_active", "is_superuser", "role", "created_at"]
    list_display_links = ["id", "username", "email"]
    list_filter = ["is_active", "is_superuser", "role", "created_at"]
    search_fields = ["username", "email"]
    list_per_page = 15
    ordering = ["-created_at"]
    exclude_fields = ["hashed_password", "email_verification_token", "password_reset_token", "password_reset_token_expires"]
    
    async def save_model(self, id: int | None, payload: dict) -> dict | None:
        if "hashed_password" in payload:
            from core.security import get_password_hash
            payload["hashed_password"] = get_password_hash(payload.pop("hashed_password"))
        return await super().save_model(id, payload)
    
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