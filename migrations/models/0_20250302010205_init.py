from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "username" VARCHAR(50) NOT NULL UNIQUE,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "hashed_password" VARCHAR(255) NOT NULL,
    "is_active" INT NOT NULL DEFAULT 1,
    "is_superuser" INT NOT NULL DEFAULT 0,
    "role" VARCHAR(20) NOT NULL DEFAULT 'user',
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "email_verified" INT NOT NULL DEFAULT 0,
    "email_verification_token" VARCHAR(255),
    "password_retry_count" INT NOT NULL DEFAULT 0,
    "password_retry_lockout_until" TIMESTAMP,
    "password_reset_token" VARCHAR(255),
    "password_reset_token_expires" TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
