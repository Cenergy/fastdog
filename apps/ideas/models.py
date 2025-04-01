from tortoise import fields, models
from enum import Enum
from apps.tasks.models import TaskStatus
from core.constants import ProviderType



class ImageSize(str, Enum):
    """转换器类型枚举"""
    square_small="512*512"
    square_medium= "768*768"
    square_large="1024*1024"
    portrait_small= "512*768"
    portrait_medium= "768*1024"
    portrait_large= "1024*1536"
    landscape_small= "768*512"
    landscape_medium= "1024*768"
    landscape_large= "1536*1024"
    
    @property
    def width(self) -> int:
        """获取宽度"""
        return int(self.value.split("*")[0])
    
    @property
    def height(self) -> int:
        """获取高度"""
        return int(self.value.split("*")[1])
    
    @classmethod
    def from_dimensions(cls, width: int, height: int) -> 'ImageSize':
        """根据宽高创建尺寸枚举
        
        Args:
            width: 图片宽度
            height: 图片高度
            
        Returns:
            最接近的标准尺寸枚举
        """
        size_str = f"{width}*{height}"
        for size in cls:
            if size.value == size_str:
                return size
        raise ValueError(f"No matching size for {size_str}")



class ImageGenerationTask(models.Model):
    """图片生成任务模型
    
    用于管理AI图片生成任务，支持异步生成和状态跟踪：
    - 可以设置图片生成的提示词和参数
    - 通过任务系统异步执行生成过程
    - 跟踪任务状态和存储生成结果
    
    任务状态流转：
    PENDING -> RUNNING -> COMPLETED/FAILED
    任务可以随时被暂停(PAUSED)或重新激活
    """
    id = fields.UUIDField(pk=True, description="任务唯一标识符")
    prompt = fields.TextField(description="图片生成的提示词描述")
    model_type = fields.CharEnumField(ImageGenerationType, description="生成模型类型", default=ImageGenerationType.WANX)
    model_params = fields.JSONField(null=True, description="模型参数配置，如图片大小、生成数量等")
    size = fields.CharEnumField(ImageSize, description="图片大小", default=ImageSize.landscape_medium)
    result_path = fields.CharField(max_length=255, null=True, description="生成图片的存储路径")
    status = fields.CharEnumField(TaskStatus, default=TaskStatus.PENDING, description="任务状态")
    error_message = fields.TextField(null=True, description="如果任务失败，记录错误信息")
    is_regenerate = fields.BooleanField(default=False, description="标识是否为重新生成的任务")
    task_id = fields.UUIDField(null=True, description="关联的后台任务ID")
    created_at = fields.DatetimeField(auto_now_add=True, description="任务创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="任务最后更新时间")

    class Meta:
        table = "image_generation_tasks"
        description = "AI图片生成任务"

    def __str__(self):
        return f"Image Generation Task {self.id}"