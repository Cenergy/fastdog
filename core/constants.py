# 系统常量定义

# 用户相关常量
USER_STATUS_ACTIVE = "active"
USER_STATUS_INACTIVE = "inactive"
USER_STATUS_DELETED = "deleted"

# 权限相关常量
ROLE_ADMIN = "admin"
ROLE_USER = "user"
ROLE_GUEST = "guest"

# 分页相关常量
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# 缓存相关常量
CACHE_TTL_SHORT = 300  # 5分钟
CACHE_TTL_MEDIUM = 1800  # 30分钟
CACHE_TTL_LONG = 86400  # 24小时

# API相关常量
API_RATE_LIMIT = 100  # 每分钟请求次数限制
API_TIMEOUT = 30  # API超时时间（秒）

# 图片生成服务类型枚举
class ImageGenerationType(Enum):
    WANX = "wx"
    HUGGINGFACE = "hf"

# 文件上传相关常量
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_FILE_TYPES = [".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"]