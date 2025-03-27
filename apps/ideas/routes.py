from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException
from tortoise.exceptions import DoesNotExist
from apps.tasks.models import Task, TaskType
from .models import ImageGenerationTask
from .job import generate_image_task

router = APIRouter(prefix="/api/v1/ideas", tags=["ideas"])

@router.post("/generate-image")
async def create_image_generation_task(prompt: str, model_params: Optional[dict] = None):
    """创建新的图片生成任务
    
    Args:
        prompt: 图片生成的提示词
        model_params: 可选的模型参数配置
    
    Returns:
        包含任务ID的响应
    """
    # 创建图片生成任务记录
    image_task = await ImageGenerationTask.create(
        prompt=prompt,
        model_params=model_params
    )
    
    # 创建后台任务
    task = await Task.create(
        name=f"Generate Image {image_task.id}",
        description=f"Generate image with prompt: {prompt}",
        func_path="apps.ideas.job.generate_image_task",
        func_args={"task_id": str(image_task.id)},
        task_type=TaskType.DATE,  # 立即执行一次的任务
    )
    
    # 更新图片任务的关联任务ID
    image_task.task_id = task.id
    await image_task.save()
    
    return {"task_id": str(image_task.id)}

@router.get("/generate-image/{task_id}")
async def get_image_generation_task(task_id: UUID):
    """获取图片生成任务的状态和结果
    
    Args:
        task_id: 图片生成任务的ID
    
    Returns:
        任务的当前状态和结果信息
    """
    try:
        task = await ImageGenerationTask.get(id=task_id)
        return {
            "id": str(task.id),
            "status": task.status,
            "result_path": task.result_path,
            "error_message": task.error_message,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Task not found")