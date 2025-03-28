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
        """禁止直接添加任务"""
        return False
    
    async def has_delete_permission(self, user_id: int | None = None) -> bool:
        """禁止直接删除任务"""
        return False
    
    async def save_model(self, id: str | None, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        """保存前的处理"""
        if not id:
            # 新任务默认为等待状态
            payload["status"] = TaskStatus.PENDING
        return await super().save_model(id, payload)
    
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