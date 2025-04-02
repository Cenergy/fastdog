import os
from pathlib import Path
from typing import Dict, Optional
import requests
from uuid import UUID
from apps.tasks.models import TaskStatus
from .models import ImageGenerationTask, ImageGenerationType
from .genImage import ImageGenerator
from core.config import settings
from loguru import logger

async def generate_image_task(task: Optional[ImageGenerationTask] = None):
    """图片生成任务的执行函数
    
    Args:
        task: 可选参数，图片生成任务实例。如果为None，则处理所有未完成的任务
    """
    # 获取任务信息
    # 查询所有状态为PENDING或FAILED的任务
    tasks = await ImageGenerationTask.filter(status__in=[TaskStatus.PENDING, TaskStatus.FAILED]).all()
    logger.info("这是一条测试日志消息-------+++++++++++++--》")
    logger.info("这是+++++++++++++--》",tasks)
    if not tasks:
        print("没有找到待处理的任务")
        return

    
    # 批量处理任务
    for task in tasks:
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
            generation_params = task.model_params or {}
            
            # 调用生成器生成图片
            result = generator.generate(
                prompt=task.prompt,
                output_dir=str(output_dir),
                n=1,  # 默认生成1张图片
                size=str(task.size) if task.size else None,
                **generation_params
            )
            print("result====================================",result)
            
            # 验证result字典结构并添加详细日志
            logger.info("图片生成结果: {}", result)
            if not isinstance(result, dict):
                raise Exception(f"无效的结果格式: {type(result)}")
            
            if 'status' not in result:
                raise Exception("结果中缺少status字段")
                
            if result['status'] == 'completed':
                if not result.get('results') or not isinstance(result['results'], list):
                    raise Exception("结果中缺少有效的results数组")
                
                if len(result['results']) == 0:
                    raise Exception("results数组为空")
                    
                # 生成成功，更新任务状态和结果路径
                first_result = result['results'][0]
                if not isinstance(first_result, dict):
                    raise Exception(f"无效的结果项格式: {type(first_result)}")
                    
                # 验证result_path是否存在且有效
                result_path = first_result.get('result_path')
                if not result_path or not Path(result_path).exists():
                    raise Exception(f"无效的结果路径: {result_path}")
                
                task.status = TaskStatus.COMPLETED
                task.result_path = result_path
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