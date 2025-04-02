from fastadmin import TortoiseModelAdmin, register, action, display, WidgetType
from tortoise.fields import CharField, TextField, JSONField
from .models import ImageGenerationTask
from apps.tasks.models import TaskStatus
from typing import Dict, Any, List

@register(ImageGenerationTask)
class ImageGenerationTaskAdmin(TortoiseModelAdmin):
    """图片生成任务管理
    
    提供图片生成任务的后台管理功能，包括：
    - 任务状态监控和管理
    - 生成结果预览
    - 任务参数配置
    - 批量操作和状态更新
    """
    model = ImageGenerationTask
    icon = "magic"
    display_name = "图片生成任务"
    list_display = ["id", "prompt_preview", "status", "result_preview", "created_at", "updated_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["id", "prompt"]
    list_per_page = 15
    ordering = ["-created_at"]
    
    form_fields = {
        "prompt": TextField(description="生成提示词", required=True),
        "model_params": JSONField(description="模型参数", required=False),
        "status": WidgetType.Select,
        "result_path": CharField(max_length=1024, description="生成结果路径", required=False),
        "error_message": TextField(description="错误信息", required=False)
    }
    
    @display
    async def prompt_preview(self, obj) -> str:
        """显示截断的提示词预览"""
        max_length = 50
        if len(obj.prompt) > max_length:
            return f"{obj.prompt[:max_length]}..."
        return obj.prompt
    
    @display
    async def result_preview(self, obj) -> str:
        """显示生成结果预览"""
        if obj.result_path:
            return f'<a href="{obj.result_path}" target="_blank"><img src="{obj.result_path}" height="50" /></a>'
        return "-"
    
    async def has_add_permission(self, user_id: int | None = None) -> bool:
        """允许直接添加任务"""
        return True
    
    async def has_delete_permission(self, user_id: int | None = None) -> bool:
        """禁止直接删除任务"""
        return True
    
    async def save_model(self, id: str | None, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        """保存前的处理"""
        if not id:
            # 新任务默认为等待状态
            payload["status"] = TaskStatus.PENDING
            
        # 保存任务
        result = await super().save_model(id, payload)
        
        if result and not id:  # 只在创建新任务时执行
            # 获取保存后的任务实例
            task = await self.model.get(id=result["id"])
            # 执行图片生成任务
            await self.execute_generation_task(task)
            
        return result
        
    async def execute_generation_task(self, task: ImageGenerationTask) -> None:
        """执行图片生成任务
        
        Args:
            task: 图片生成任务实例
        """
        from .genImage import ImageGenerator, ImageGenerationType
        import os
        from pathlib import Path
        
        # 更新任务状态为运行中
        task.status = TaskStatus.RUNNING
        await task.save()
        
        try:
            # 创建输出目录
            output_dir = Path("static/results/ideas")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 初始化图片生成器 - 使用任务中指定的模型类型，如果没有则使用默认值
            model_type = None
            if hasattr(task, 'model_type') and task.model_type is not None:
                model_type = task.model_type.value
            else:
                model_type = ImageGenerationType.WANX.value
            generator = ImageGenerator(provider=model_type)
            
            # 准备生成参数 - 安全地获取size值
            size = None
            if hasattr(task, 'size') and task.size is not None:
                size = task.size.value
            model_params = task.model_params or {}
            
            # 执行图片生成
            result = generator.generate(
                prompt=task.prompt,
                output_dir=str(output_dir),
                n=1,
                size=size,
                **model_params
            )
            
            # 处理生成结果
            if isinstance(result, dict) and result.get('status') == 'completed' and result.get('results') and len(result.get('results')) > 0:
                # 成功生成图片
                try:
                    first_result = result['results'][0]
                    if first_result and isinstance(first_result, dict):
                        task.result_path = first_result.get('result_path')
                        task.status = TaskStatus.COMPLETED
                        task.error_message = None
                    else:
                        # 结果格式不正确
                        task.status = TaskStatus.FAILED
                        task.error_message = "图片生成结果格式不正确"
                except (IndexError, TypeError) as e:
                    # 处理索引错误或类型错误
                    task.status = TaskStatus.FAILED
                    task.error_message = f"处理图片生成结果时出错: {str(e)}"
            else:
                # 生成失败
                task.status = TaskStatus.FAILED
                error_msg = "图片生成失败，未返回有效结果"
                if isinstance(result, dict):
                    error_msg = result.get('error_message') or error_msg
                task.error_message = error_msg
                
        except Exception as e:
            # 捕获异常并记录错误信息
            task.status = TaskStatus.FAILED
            task.error_message = f"图片生成过程中发生错误: {str(e)}"
        
        # 保存任务状态更新
        await task.save()
    
    @action
    async def retry_failed_tasks(self, ids: List[str]) -> None:
        """重试失败的任务"""
        updated = 0
        for id in ids:
            task = await self.model.get_or_none(id=id)
            if task and task.status == TaskStatus.FAILED:
                task.status = TaskStatus.PENDING
                task.error_message = None
                await task.save()
                updated += 1
        return f"成功重置 {updated} 个失败任务到等待状态"
    
    @action
    async def pause_tasks(self, ids: List[str]) -> None:
        """暂停选中的任务"""
        updated = 0
        for id in ids:
            task = await self.model.get_or_none(id=id)
            if task and task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task.status = TaskStatus.PAUSED
                await task.save()
                updated += 1
        return f"成功暂停 {updated} 个任务"
    
    @action
    async def resume_tasks(self, ids: List[str]) -> None:
        """恢复暂停的任务"""
        updated = 0
        for id in ids:
            task = await self.model.get_or_none(id=id)
            if task and task.status == TaskStatus.PAUSED:
                task.status = TaskStatus.PENDING
                await task.save()
                updated += 1
        return f"成功恢复 {updated} 个任务"