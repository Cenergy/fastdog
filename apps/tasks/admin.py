from fastadmin import TortoiseModelAdmin, register, action, display
from .models import Task, TaskStatus
from .scheduler import scheduler

@register(Task)
class TaskModelAdmin(TortoiseModelAdmin):
    model = Task
    icon = "clock"
    display_name = "任务管理"
    list_display = ["id", "name", "task_type", "status", "is_active", "next_run_time", "last_run_time", "created_at"]
    list_display_links = ["id", "name"]
    list_filter = ["task_type", "status", "is_active", "created_at"]
    search_fields = ["name", "description", "func_path"]
    list_per_page = 15
    ordering = ["-created_at"]
    
    @action(description="暂停任务")
    async def pause(self, request, queryset):
        success_count = 0
        for task in queryset:
            if await scheduler.pause_task(str(task.id)):
                success_count += 1
        return f"成功暂停 {success_count} 个任务"
    
    @action(description="恢复任务")
    async def resume(self, request, queryset):
        success_count = 0
        for task in queryset:
            if await scheduler.resume_task(str(task.id)):
                success_count += 1
        return f"成功恢复 {success_count} 个任务"
    
    async def save_model(self, id: str | None, payload: dict) -> dict | None:
        # 保存任务
        result = await super().save_model(id, payload)
        if result:
            # 获取保存后的任务实例
            task = await self.model.get(id=result["id"])
            # 如果是新建任务或修改了任务配置
            if id is None:
                # 添加新任务到调度器
                await scheduler.add_task(task)
            else:
                # 修改现有任务
                await scheduler.modify_task(task)
        return result
    
    async def delete_model(self, id: str) -> bool:
        # 从调度器中移除任务
        await scheduler.remove_task(id)
        # 删除任务记录
        return await super().delete_model(id)