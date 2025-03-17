from tortoise import fields, models
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class TaskType(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"
    DATE = "date"

class Task(models.Model):
    """任务模型"""
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, description="任务名称")
    description = fields.TextField(null=True, description="任务描述")
    func_path = fields.CharField(max_length=255, description="任务函数路径")
    func_args = fields.JSONField(null=True, description="任务函数参数")
    task_type = fields.CharEnumField(TaskType, description="任务类型")
    cron_expression = fields.CharField(max_length=100, null=True, description="Cron表达式")
    interval_seconds = fields.IntField(null=True, description="间隔秒数")
    run_date = fields.DatetimeField(null=True, description="运行日期时间")
    next_run_time = fields.DatetimeField(null=True, description="下次运行时间")
    last_run_time = fields.DatetimeField(null=True, description="上次运行时间")
    status = fields.CharEnumField(TaskStatus, default=TaskStatus.PENDING, description="任务状态")
    is_active = fields.BooleanField(default=True, description="是否激活")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "tasks"
        description = "后台任务"

    def __str__(self):
        return self.name