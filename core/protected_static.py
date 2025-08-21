from fastapi import HTTPException, Request
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope, Receive, Send
import os
from typing import List

class ProtectedStaticFiles(StaticFiles):
    """
    自定义静态文件处理器，用于限制特定文件类型的直接访问
    """
    
    def __init__(self, directory: str, protected_extensions: List[str] = None, protected_paths: List[str] = None, **kwargs):
        """
        初始化受保护的静态文件处理器
        
        Args:
            directory: 静态文件目录
            protected_extensions: 受保护的文件扩展名列表（如 ['.gltf', '.fastdog']）
            protected_paths: 受保护的路径列表（如 ['/uploads/models/']）
        """
        super().__init__(directory=directory, **kwargs)
        self.protected_extensions = protected_extensions or []
        self.protected_paths = protected_paths or ["/uploads/models/"]
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        处理请求，检查是否为受保护的文件类型
        """
        if scope["type"] == "http":
            path = scope["path"]
            
            # 检查是否访问受保护的文件类型
            if self._is_protected_file(path):
                # 返回 403 Forbidden
                response = Response(
                    content="Access to this file type is forbidden",
                    status_code=403,
                    media_type="text/plain"
                )
                await response(scope, receive, send)
                return
        
        # 如果不是受保护的文件，继续正常处理
        await super().__call__(scope, receive, send)
    
    def _is_protected_file(self, path: str) -> bool:
        """
        检查文件路径是否为受保护的文件类型
        
        Args:
            path: 请求的文件路径
            
        Returns:
            bool: 如果是受保护的文件类型返回 True
        """
        # 检查路径是否包含受保护的路径
        for protected_path in self.protected_paths:
            if protected_path in path:
                # 获取文件扩展名
                _, ext = os.path.splitext(path)
                return ext.lower() in self.protected_extensions
        
        return False