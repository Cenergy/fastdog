from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
from typing import Optional, Dict, Any
import importlib
import logging
from .models import Task, TaskStatus, TaskType

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
        # 配置调度器
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(20),
            'processpool': ProcessPoolExecutor(5)
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler.configure(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )
    
    async def start(self):
        """启动调度器并加载所有激活的任务"""
        if not self.scheduler.running:
            self.scheduler.start()
            await self._load_tasks()
            logger.info("Task scheduler started successfully")
    
    async def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Task scheduler shutdown")
    
    async def _load_tasks(self):
        """加载所有激活的任务"""
        tasks = await Task.filter(is_active=True)
        for task in tasks:
            await self.add_task(task)
    
    async def add_task(self, task: Task) -> bool:
        """添加任务到调度器"""
        try:
            # 检查任务是否处于激活状态
            if not task.is_active:
                logger.info(f"Task {task.name} is not active, skipping")
                return False

            # 导入任务函数
            module_path, func_name = task.func_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            
            # 创建触发器
            trigger = self._create_trigger(task)
            if not trigger:
                return False
            
            # 添加任务到调度器
            self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=str(task.id),
                name=task.name,
                kwargs=task.func_args or {},
                misfire_grace_time=None
            )
            
            # 更新任务状态
            task.status = TaskStatus.PENDING
            await task.save()
            
            return True
        except Exception as e:
            logger.error(f"Failed to add task {task.name}: {str(e)}")
            task.status = TaskStatus.FAILED
            await task.save()
            return False
    
    def _create_trigger(self, task: Task):
        """根据任务类型创建触发器"""
        try:
            if task.task_type == TaskType.CRON:
                return CronTrigger.from_crontab(task.cron_expression)
            elif task.task_type == TaskType.INTERVAL:
                return IntervalTrigger(seconds=task.interval_seconds)
            elif task.task_type == TaskType.DATE:
                return DateTrigger(run_date=task.run_date)
            else:
                logger.error(f"Unknown task type: {task.task_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to create trigger for task {task.name}: {str(e)}")
            return None
    
    async def remove_task(self, task_id: str) -> bool:
        """从调度器中移除任务"""
        try:
            self.scheduler.remove_job(task_id)
            task = await Task.get(id=task_id)
            task.status = TaskStatus.PAUSED
            await task.save()
            return True
        except Exception as e:
            logger.error(f"Failed to remove task {task_id}: {str(e)}")
            return False
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(task_id)
            task = await Task.get(id=task_id)
            task.status = TaskStatus.PAUSED
            await task.save()
            return True
        except Exception as e:
            logger.error(f"Failed to pause task {task_id}: {str(e)}")
            return False
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(task_id)
            task = await Task.get(id=task_id)
            task.status = TaskStatus.PENDING
            await task.save()
            return True
        except Exception as e:
            logger.error(f"Failed to resume task {task_id}: {str(e)}")
            return False
    
    async def modify_task(self, task: Task) -> bool:
        """修改任务配置"""
        try:
            # 先移除旧任务
            await self.remove_task(str(task.id))
            # 根据is_active状态决定是否添加新任务
            if task.is_active:
                return await self.add_task(task)
            else:
                logger.info(f"Task {task.name} is not active, not adding to scheduler")
                return True
        except Exception as e:
            logger.error(f"Failed to modify task {task.name}: {str(e)}")
            return False

    async def update_task_active_status(self, task: Task) -> bool:
        """更新任务的激活状态"""
        try:
            if task.is_active:
                # 如果任务变为激活状态，尝试添加到调度器
                return await self.add_task(task)
            else:
                # 如果任务变为非激活状态，从调度器中移除
                return await self.remove_task(str(task.id))
        except Exception as e:
            logger.error(f"Failed to update task active status for {task.name}: {str(e)}")
            return False

# 创建全局调度器实例
scheduler = TaskScheduler()