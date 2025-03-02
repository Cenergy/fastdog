import asyncio
from typing import List, Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from loguru import logger
from core.config import settings

conf = ConnectionConfig(**settings.EMAIL_CONNECTION_CONFIG)
fastmail = FastMail(conf)

async def send_email(
    email_to: str,
    subject: str,
    body: str,
    template_name: Optional[str] = None
) -> None:
    """发送邮件

    Args:
        email_to: 收件人邮箱
        subject: 邮件主题
        body: 邮件内容
        template_name: 模板名称，如果提供则使用模板发送邮件
    """
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body,
        subtype='html'
    )
    
    for attempt in range(settings.EMAIL_RETRY_COUNT):
        try:
            logger.info(f"尝试发送邮件到 {email_to}，主题：{subject}，配置信息：{conf.MAIL_USERNAME}, {conf.MAIL_SERVER}:{conf.MAIL_PORT}")
            await fastmail.send_message(message)
            logger.info(f"邮件发送成功: {email_to}")
            return
        except Exception as e:
            logger.error(f"邮件发送失败 (尝试 {attempt + 1}/{settings.EMAIL_RETRY_COUNT}): {str(e)}\n配置信息：{conf.MAIL_USERNAME}, {conf.MAIL_SERVER}:{conf.MAIL_PORT}")
            if attempt < settings.EMAIL_RETRY_COUNT - 1:
                logger.info(f"等待 {settings.EMAIL_RETRY_INTERVAL} 秒后重试...")
                await asyncio.sleep(settings.EMAIL_RETRY_INTERVAL)
            else:
                logger.error(f"邮件发送最终失败: {email_to}，已达到最大重试次数 {settings.EMAIL_RETRY_COUNT}")
                raise

async def send_verification_email(email_to: str, token: str) -> None:
    """发送验证邮件

    Args:
        email_to: 收件人邮箱
        token: 验证令牌
    """
    subject = "请验证您的邮箱"
    verification_url = f"{settings.SERVER_HOST}{settings.API_V1_STR}/auth/verify-email/{token}"
    body = f"""
    <h3>欢迎注册！</h3>
    <p>请点击下面的链接验证您的邮箱：</p>
    <p><a href="{verification_url}">{verification_url}</a></p>
    <p>此链接将在{settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES//60}小时后过期。</p>
    <p>如果这不是您的操作，请忽略此邮件。</p>
    """
    
    # 创建异步任务发送邮件，不等待结果
    asyncio.create_task(send_email(email_to, subject, body))