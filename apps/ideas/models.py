from tortoise import fields, models
from enum import Enum
from apps.tasks.models import TaskStatus
from .genImage import ImageGenerationType


class ImageSize(str, Enum):
    """图片尺寸枚举
    
    支持常见的图片尺寸格式，包括正方形、纵向和横向三种类型
    每个枚举值格式为"宽度*高度"的字符串
    """
    square_large="1024*1024"
    portrait_medium= "720*1280"
    portrait_large= "1280*720"
    landscape_medium= "768*1152"
    
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
    
    def __str__(self) -> str:
        """返回枚举值的字符串表示"""
        return self.value
    
    @classmethod
    def _missing_(cls, value):
        """处理未找到的枚举值
        
        当尝试通过值获取枚举但值不存在时调用此方法
        可以实现自定义的值转换逻辑
        """
        if isinstance(value, str):
            # 尝试查找匹配的尺寸
            for size in cls:
                if size.value == value:
                    return size
        return None
        
    def __eq__(self, other):
        """自定义相等比较方法
        
        支持与字符串直接比较
        """
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)



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
    id = fields.IntField(pk=True)
    prompt = fields.TextField(description="图片生成的提示词描述")
    negative_prompt = fields.TextField(null=True, description="图片生成的负面提示词，指定不希望出现的元素")
    model_type = fields.CharEnumField(ImageGenerationType, description="生成模型类型", default=ImageGenerationType.WANX)
    model_params = fields.JSONField(null=True, description="模型参数配置，如图片大小、生成数量等",default={})
    size = fields.CharEnumField(ImageSize, description="图片大小", default=ImageSize.landscape_medium)
    num_images = fields.IntField(default=1, description="生成图片的数量",max_length=4)
    style_preset = fields.CharField(max_length=100, null=True, description="风格预设，如写实、动漫、油画等")
    result_path = fields.CharField(max_length=255, null=True, description="生成图片的存储路径")
    result_urls = fields.JSONField(null=False, description="生成图片的URL列表", default=[])
    task_id = fields.UUIDField(null=True, description="关联的后台任务ID")
    status = fields.CharEnumField(TaskStatus, default=TaskStatus.PENDING, description="任务状态")
    error_message = fields.TextField(null=True, description="如果任务失败，记录错误信息")
    created_at = fields.DatetimeField(auto_now_add=True, description="任务创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="任务最后更新时间")
     # 结果和状态

    class Meta:
        table = "image_generation_tasks"
        description = "AI图片生成任务"

    def __str__(self):
        return f"Image Generation Task {self.id}"