import os
from pathlib import Path
from typing import Dict, Optional
import requests
from uuid import UUID
from apps.tasks.models import TaskStatus
from .models import ImageGenerationTask, ImageGenerationType
from .genImage import ImageGenerator
from core.config import settings

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
        
        # 根据任务配置选择生成器类型
        provider_type = None
        if task.model_type == ImageGenerationType.WANX:
            # 使用通义万相生成
            if not settings.DASHSCOPE_API_KEY:
                raise ValueError("未配置通义万相API密钥，请在环境变量中设置DASHSCOPE_API_KEY")
            provider_type = "WANX"
        elif task.model_type == ImageGenerationType.HUGGINGFACE:
            # 使用HuggingFace生成
            if not settings.HUGGINGFACE_API_KEY:
                raise ValueError("未配置HuggingFace API密钥，请在环境变量中设置HUGGINGFACE_API_KEY")
            provider_type = "HUGGINGFACE"
        else:
            raise ValueError(f"不支持的模型类型: {task.model_type}")
        
        # 创建图片生成器
        generator = ImageGenerator(provider=provider_type)
        
        # 准备生成参数
        generation_params = {}
        if task.model_params:
            generation_params.update(task.model_params)
        
        # 获取图片尺寸
        size = None
        if task.size:
            size = str(task.size)
        
        # 调用生成器生成图片
        result = generator.generate(
            prompt=task.prompt,
            output_dir=str(output_dir),
            n=1,  # 默认生成1张图片
            size=size,
            **generation_params
        )
        
        if result['status'] == 'completed' and result.get('results'):
            # 生成成功，更新任务状态和结果路径
            first_result = result['results'][0]
            task.status = TaskStatus.COMPLETED
            task.result_path = first_result.get('result_path')
        else:
            # 生成失败，抛出异常
            error_msg = result.get('error_message', '图片生成失败，未知错误')
            raise Exception(error_msg)
            
    except Exception as e:
        # 更新任务状态为失败并记录错误信息
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
    
    # 保存任务状态更新
    await task.save()