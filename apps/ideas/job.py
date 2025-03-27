from pathlib import Path
from typing import Dict, Optional
import requests
from uuid import UUID
from apps.tasks.models import TaskStatus
from .models import ImageGenerationTask

API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",  # 需要替换为实际的API密钥
    "Content-Type": "application/json"
}

def create_session_with_retry(retries: int = 3) -> requests.Session:
    """创建带有重试机制的会话"""
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

async def generate_image_task(task_id: UUID):
    """图片生成任务的执行函数
    
    Args:
        task_id: 图片生成任务的ID
    """
    # 获取任务信息
    task = await ImageGenerationTask.get(id=task_id)
    if not task:
        return
    
    # 更新任务状态为运行中
    task.status = TaskStatus.RUNNING
    await task.save()
    
    try:
        # 创建输出目录
        output_dir = Path("static/results/ideas")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{task_id}.jpg"
        
        # 调用API生成图片
        session = create_session_with_retry()
        payload = {"inputs": task.prompt}
        if task.model_params:
            payload.update(task.model_params)
        
        response = session.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            # 保存生成的图片
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            # 更新任务状态和结果路径
            task.status = TaskStatus.COMPLETED
            task.result_path = str(output_path)
        else:
            error_messages = {
                401: "认证失败，请检查API密钥",
                403: "没有访问权限",
                404: "服务未找到",
                429: "请求过于频繁，请稍后重试",
                500: "服务器内部错误",
                503: "服务暂时不可用"
            }
            error_msg = error_messages.get(
                response.status_code,
                f"生成失败（错误码：{response.status_code}）"
            )
            raise Exception(error_msg)
            
    except Exception as e:
        # 更新任务状态为失败并记录错误信息
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
    
    # 保存任务状态更新
    await task.save()