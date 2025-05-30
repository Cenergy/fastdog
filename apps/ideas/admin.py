import re
from fastadmin import TortoiseModelAdmin, register, action, display, WidgetType
from tortoise.fields import CharField, TextField, JSONField
from .models import ImageGenerationTask
from apps.tasks.models import TaskStatus
from typing import Dict, Any, List
from core.settings import settings
from ..albums.admin import CustomModelAdmin

@register(ImageGenerationTask)
class ImageGenerationTaskAdmin(CustomModelAdmin):
    """图片生成任务管理
    
    提供图片生成任务的后台管理功能，包括：
    - 任务状态监控和管理
    - 生成结果预览
    - 任务参数配置
    - 批量操作和状态更新
    """
    model = ImageGenerationTask
    max_num: int = 2
    icon = "magic"
    verbose_name="图片生成"
    verbose_name_plural="图片生成任务"
    display_name = "图片生成任务"
    list_display = ["id", "prompt_preview", "status", "result_preview", "created_at", "updated_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["id", "prompt"]
    list_per_page = 15
    ordering = ["-created_at"]
    readonly_fields = ["status","result_path", "error_message","result_urls"]
    
    form_fields = {
        "prompt": TextField(description="生成提示词", required=True),
        "model_params": JSONField(description="模型参数", required=False, default={}),
        "status": WidgetType.Select,
        "result_path": CharField(max_length=1024, description="生成结果路径", required=False),
        "error_message": TextField(description="错误信息", required=False)
    }

    formfield_overrides = {
        "result_urls": (WidgetType.Upload, {"required": False, "upload_action_name": "upload", "multiple": True}),
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
        """显示生成结果预览
        
        如果有多张图片(result_urls)，则显示所有图片的预览
        如果只有单张图片(result_path)，则显示单张图片预览
        """
        # 优先显示result_urls中的所有图片
        if hasattr(obj, 'result_urls') and obj.result_urls and isinstance(obj.result_urls, list) and len(obj.result_urls) > 0:
            previews = []
            for url in obj.result_urls:
                if url and isinstance(url, str):
                    # 确保URL以/开头
                    url_with_slash = url if url.startswith('/') else f'/{url}'
                    previews.append(f'<a href="{url_with_slash}" target="_blank"><img src="{url_with_slash}" height="50" style="margin-right: 5px;" /></a>')
            if previews:
                return ''.join(previews)
        
        # 如果没有result_urls或为空，则显示result_path
        if obj.result_path:
            # 确保URL以/开头
            path_with_slash = obj.result_path if obj.result_path.startswith('/') else f'/{obj.result_path}'
            return f'<a href="{path_with_slash}" target="_blank"><img src="{path_with_slash}" height="50" /></a>'
        
        return "-"
    
    async def has_add_permission(self, user_id: int | None = None) -> bool:
        """允许直接添加任务"""
        return True
    
    async def has_delete_permission(self, user_id: int | None = None) -> bool:
        """禁止直接删除任务"""
        return True
    
    async def save_model(self, id: str | None, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        """保存前的处理
        
        Args:
            id: 任务ID，新建任务时为None
            payload: 任务数据
        Returns:
            保存后的任务数据
        """
        try:
            if not id:
                # 新任务默认为等待状态
                payload["status"] = TaskStatus.PENDING
            else:
                # 获取当前任务实例以比较result_urls的变化
                current_task = await self.model.get(id=id)
                if "result_urls" in payload and hasattr(current_task, "result_urls"):
                    # 获取当前和新的result_urls列表
                    current_urls = current_task.result_urls or []
                    new_urls = payload["result_urls"] if isinstance(payload["result_urls"], list) else []
                    
                    # 找出被删除的URL
                    deleted_urls = [url for url in current_urls if url and url not in new_urls]
                    
                    if deleted_urls:
                        # 删除对应的物理文件
                        import os
                        from pathlib import Path
                        import logging
                        logger = logging.getLogger(__name__)
                        
                        for url in deleted_urls:
                            try:
                                # 将URL转换为文件系统路径（移除开头的斜杠）
                                clean_url = url.lstrip('/')
                                
                                # 构建文件的绝对路径 - 使用更直接的方法
                                if clean_url.startswith('static/'):
                                    # 如果URL以static/开头，直接使用STATIC_DIR作为基础路径
                                    relative_path = clean_url[7:]  # 移除'static/'前缀
                                    file_path = os.path.join(settings.STATIC_DIR, relative_path)
                                else:
                                    # 否则，尝试多种可能的路径组合
                                    file_path = os.path.join(settings.STATIC_DIR, clean_url)
                                
                                # 检查文件是否存在
                                if os.path.exists(file_path):
                                    # 确保文件路径在允许的目录中，防止误删除其他文件
                                    normalized_path = file_path.replace("\\", "/")
                                    if "results/ideas" in normalized_path:
                                        os.remove(file_path)
                                    else:
                                        logger.warning(f"文件不在允许的目录中: {file_path}")
                                else:
                                    # 尝试其他可能的路径
                                    basename = os.path.basename(file_path)
                                    alt_path = os.path.join(settings.STATIC_DIR, "results", "ideas", basename)
                                    
                                    if os.path.exists(alt_path):
                                        os.remove(alt_path)

                            except Exception as e:
                                logger.error(f"删除文件时出错: {str(e)}, URL: {url}")
            
            # 确保result_urls字段被正确处理
            if "result_urls" in payload:
                # 确保result_urls是一个列表
                if isinstance(payload["result_urls"], list):
                    # 过滤掉无效的URL
                    payload["result_urls"] = [url for url in payload["result_urls"] if url and isinstance(url, str)]
                    # 如果有result_urls，将第一个URL设置为result_path
                    if payload["result_urls"]:
                        payload["result_path"] = payload["result_urls"][0]
            
            # 保存任务
            result = await super().save_model(id, payload)
            
            if result:
                # 验证保存结果
                saved_task = await self.model.get(id=result["id"])
                
                # 如果result_urls没有正确保存，尝试直接更新
                if "result_urls" in payload and saved_task.result_urls != payload["result_urls"]:
                    saved_task.result_urls = payload["result_urls"]
                    saved_task.result_path = payload["result_urls"][0] if payload["result_urls"] else None
                    await saved_task.save()
            
            # 如果是新任务，启动异步处理
            if result and not id:
                # 获取保存后的任务实例
                task = await self.model.get(id=result["id"])
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"准备提交任务 {task.id} 到异步队列")
                
                # 使用一个单独的函数来启动异步任务，确保表单立即返回
                from concurrent.futures import ThreadPoolExecutor
                import asyncio
                
                # 创建一个执行器来运行异步任务
                executor = ThreadPoolExecutor(max_workers=1)
                
                # 提交任务到线程池，确保不阻塞当前请求
                def start_task():
                    # 创建一个新的事件循环来运行异步任务
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # 在新的事件循环中运行任务
                        loop.run_until_complete(self.execute_generation_task(task))
                    finally:
                        loop.close()
                
                # 在线程池中启动任务
                executor.submit(start_task)
                executor.shutdown(wait=False)  # 不等待任务完成
                
                logger.info(f"任务 {task.id} 已提交到线程池执行")
            
            return result
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"保存任务时出错: {str(e)}")
            raise e
        
    async def _run_task_in_threadpool(self, task: ImageGenerationTask) -> None:
        """在线程池中执行任务
        
        Args:
            task: 图片生成任务实例
        """
        # 不应该使用run_in_threadpool执行异步函数，直接调用异步函数
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"开始执行任务 {task.id}")
        try:
            await self.execute_generation_task(task)
            logger.info(f"任务 {task.id} 执行完成")
        except Exception as e:
            logger.error(f"任务 {task.id} 执行失败: {str(e)}")
            # 确保任务状态被更新为失败
            task.status = TaskStatus.FAILED
            task.error_message = f"任务执行过程中发生错误: {str(e)}"
            await task.save()
        
    async def execute_generation_task(self, task: ImageGenerationTask) -> None:
        """执行图片生成任务
        
        Args:
            task: 图片生成任务实例
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"开始执行任务: {task.id}")
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
            num_images =task.num_images or 1
            if num_images > self.max_num:
                num_images = self.max_num
            
            # 执行图片生成
            result = generator.generate(
                prompt=task.prompt,
                output_dir=str(output_dir),
                n=num_images,
                size=size,
                **model_params
            )
            
            # 处理生成结果
            if isinstance(result, dict) and result.get('status') == 'completed' and result.get('results') and len(result.get('results')) > 0:
                # 成功生成图片
                try:
                    # 保存所有生成的图片URL到result_urls字段
                    result_urls = []
                    for img_result in result['results']:
                        if img_result and isinstance(img_result, dict) and img_result.get('result_path'):
                            # 确保URL以/开头
                            path = img_result.get('result_path')
                            path_with_slash = path if path.startswith('/') else f'/{path}'
                            result_urls.append(path_with_slash)
                    
                    # 设置result_urls字段
                    if result_urls:
                        task.result_urls = result_urls
                        # 同时保持向后兼容，将第一张图片路径保存到result_path
                        task.result_path = result_urls[0]  # 这里已经确保了URL以/开头
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
    
    async def delete_model(self, id: str) -> bool:
        """删除任务及其关联的所有图片文件
        
        Args:
            id: 任务ID
            
        Returns:
            删除是否成功
        """
        try:
            # 获取任务对象
            task = await self.model.get(id=id)
            
            # 删除result_urls中的所有图片文件
            if hasattr(task, 'result_urls') and task.result_urls and isinstance(task.result_urls, list):
                import os
                from pathlib import Path
                import logging
                logger = logging.getLogger(__name__)
                
                logger.info(f"删除任务 {id} 的图片文件")
                
                for url in task.result_urls:
                    if url and isinstance(url, str):
                        try:
                            # 将URL转换为文件系统路径（移除开头的斜杠）
                            clean_url = url.lstrip('/')
                            
                            # 构建文件的绝对路径
                            if clean_url.startswith('static/'):
                                # 如果URL以static/开头，直接使用STATIC_DIR作为基础路径
                                relative_path = clean_url[7:]  # 移除'static/'前缀
                                file_path = os.path.join(settings.STATIC_DIR, relative_path)
                            else:
                                # 否则，尝试多种可能的路径组合
                                file_path = os.path.join(settings.STATIC_DIR, clean_url)
                            
                            # 检查文件是否存在
                            if os.path.exists(file_path):
                                # 确保文件路径在允许的目录中，防止误删除其他文件
                                normalized_path = file_path.replace("\\", "/")
                                if "results/ideas" in normalized_path:
                                    os.remove(file_path)
                                else:
                                    logger.warning(f"文件不在允许的目录中: {file_path}")
                            else:
                                # 尝试其他可能的路径
                                basename = os.path.basename(file_path)
                                alt_path = os.path.join(settings.STATIC_DIR, "results", "ideas", basename)
                                
                                if os.path.exists(alt_path):
                                    os.remove(alt_path)
                        except Exception as e:
                            logger.error(f"删除文件时出错: {str(e)}, URL: {url}")
            # 删除任务记录
            return await super().delete_model(id)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"删除任务及其图片文件时出错: {str(e)}")
            raise e