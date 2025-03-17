from tortoise import fields, models
from enum import Enum

class TaskStatus(str, Enum):
    """任务状态枚举
    
    - PENDING: 等待执行的任务
    - RUNNING: 正在执行中的任务
    - COMPLETED: 已成功完成的任务
    - FAILED: 执行失败的任务
    - PAUSED: 已暂停的任务
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class TaskType(str, Enum):
    """任务类型枚举
    
    - CRON: 基于Cron表达式的定时任务，可以设置复杂的执行计划
    - INTERVAL: 固定时间间隔执行的任务
    - DATE: 在指定日期时间执行一次的任务
    """
    CRON = "cron"
    INTERVAL = "interval"
    DATE = "date"

class Task(models.Model):
    """任务模型
    
    用于管理系统中的定时任务，支持多种任务类型：
    1. Cron定时任务：通过cron表达式设置复杂的执行计划
    2. 固定间隔任务：按照固定的时间间隔重复执行
    3. 定时任务：在指定的日期时间执行一次
    
    任务状态流转：
    PENDING -> RUNNING -> COMPLETED/FAILED
    任务可以随时被暂停(PAUSED)或重新激活
    """
    id = fields.UUIDField(pk=True, description="任务唯一标识符")
    name = fields.CharField(max_length=255, description="任务名称，用于标识和区分不同的任务")
    description = fields.TextField(null=True, description="任务的详细描述信息，可以包含任务的目的、注意事项等")
    func_path = fields.CharField(max_length=255, description="任务函数的导入路径，例如'module.submodule.function'")
    func_args = fields.JSONField(null=True, description="任务函数的参数，使用JSON格式存储，可以包含位置参数和关键字参数")
    task_type = fields.CharEnumField(TaskType, description="任务类型，支持cron定时、固定间隔和指定时间三种类型")
    cron_expression = fields.CharField(max_length=100, null=True, description="Cron表达式，用于设置复杂的定时规则，仅在task_type为CRON时有效")
    interval_seconds = fields.IntField(null=True, description="任务执行的时间间隔（秒），仅在task_type为INTERVAL时有效")
    run_date = fields.DatetimeField(null=True, description="任务的计划执行时间，仅在task_type为DATE时有效")
    next_run_time = fields.DatetimeField(null=True, description="任务的下一次计划执行时间，由调度器自动更新")
    last_run_time = fields.DatetimeField(null=True, description="任务的上一次执行时间，用于跟踪任务执行历史")
    status = fields.CharEnumField(TaskStatus, default=TaskStatus.PENDING, description="任务当前状态，反映任务的生命周期状态")
    is_active = fields.BooleanField(default=True, description="任务是否处于激活状态，False表示任务被禁用")
    created_at = fields.DatetimeField(auto_now_add=True, description="任务创建的时间戳")
    updated_at = fields.DatetimeField(auto_now=True, description="任务最后一次更新的时间戳")

    class Meta:
        table = "tasks"
        description = "后台任务"

    def __str__(self):
        return self.name