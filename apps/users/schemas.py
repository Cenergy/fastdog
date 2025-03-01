from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, IPvAnyAddress
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None
    avatar_url: Optional[str] = None

class UserInDB(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    email_verified: bool = False
    email_verification_token: Optional[str] = None
    password_retry_count: int = 0
    password_retry_lockout_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class User(UserInDB):
    pass

class UserSession(BaseModel):
    user_id: int
    session_id: str
    expires_at: datetime
    last_activity: datetime

    model_config = ConfigDict(from_attributes=True)