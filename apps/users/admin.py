from fastadmin import TortoiseModelAdmin, register
from fastadmin import TortoiseInlineModelAdmin, TortoiseModelAdmin, WidgetType, action, display
from .models import User
from .crud import get_user_by_username_or_email
from core.security import verify_password, get_password_hash


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

    formfield_overrides = {  # noqa: RUF012
        "username": (WidgetType.SlugInput, {"required": True}),
        "hashed_password": (WidgetType.PasswordInput, {"passwordModalForm": True}),
    }

    
    async def save_model(self, id: int | None, payload: dict) -> dict | None:
        if "hashed_password" in payload:
            payload["hashed_password"] = get_password_hash(payload.pop("hashed_password"))
        
        # 如果是新建用户（id为None），则直接使用create_user函数创建
        # 并标记为管理后台创建，允许设置email_verified为True
        if id is None:
            from .crud import create_user
            user = await create_user(payload, is_admin_creation=True)
            return user.model_dump()
        return await super().save_model(id, payload)
    
    async def change_password(self, user_id: int, password: str) -> bool:
        """修改用户密码
        
        Args:
            user_id: 用户ID
            password: 新密码
            
        Returns:
            bool: 修改成功返回True，失败返回False
        """
        user = await self.model_cls.filter(id=user_id).first()
        if not user:
            return False
            
        user.hashed_password = get_password_hash(password)
        await user.save()
        return True
    
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