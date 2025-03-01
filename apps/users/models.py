from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator

class User(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    email = fields.CharField(max_length=255, unique=True)
    hashed_password = fields.CharField(max_length=255)
    is_active = fields.BooleanField(default=True)
    is_superuser = fields.BooleanField(default=False)
    role = fields.CharField(max_length=20, default="user")
    created_at = fields.DatetimeField(auto_now_add=True)
    email_verified = fields.BooleanField(default=False)
    email_verification_token = fields.CharField(max_length=255, null=True)
    password_retry_count = fields.IntField(default=0)
    password_retry_lockout_until = fields.DatetimeField(null=True)
    password_reset_token = fields.CharField(max_length=255, null=True)
    password_reset_token_expires = fields.DatetimeField(null=True)

    class Meta:
        table = "users"

    def __str__(self):
        return f"{self.username}"

User_Pydantic = pydantic_model_creator(User, name="User", exclude=("hashed_password", "email_verification_token", "password_reset_token", "password_reset_token_expires"))
UserIn_Pydantic = pydantic_model_creator(User, name="UserIn", exclude_readonly=True, exclude=("hashed_password", "email_verification_token", "password_reset_token", "password_reset_token_expires"))

class UserCreate(UserIn_Pydantic):
    password: str