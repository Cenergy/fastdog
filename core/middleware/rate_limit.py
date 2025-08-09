from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from typing import Dict, Tuple
from collections import defaultdict

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_history: Dict[str, list] = defaultdict(list)
        # 流式下载路径豁免列表
        self.exempt_paths = [
            "/api/v1/resources/models/uuid/",  # 流式下载UUID路径
            "/api/v1/resources/models/",       # 普通模型下载路径
        ]

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = datetime.now()
        
        # 检查是否为豁免路径
        request_path = str(request.url.path)
        is_exempt = any(exempt_path in request_path for exempt_path in self.exempt_paths)
        
        if not is_exempt:
            # 清理过期的请求记录
            self.request_history[client_ip] = [
                req_time for req_time in self.request_history[client_ip]
                if now - req_time < timedelta(minutes=1)
            ]

            # 检查请求频率
            if len(self.request_history[client_ip]) >= self.requests_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "请求过于频繁，请稍后再试",
                        "retry_after": "60秒"
                    }
                )

            # 记录新的请求
            self.request_history[client_ip].append(now)

        # 处理请求
        response = await call_next(request)
        return response