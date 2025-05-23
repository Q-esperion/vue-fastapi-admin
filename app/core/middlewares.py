import json
import re
from datetime import datetime
from typing import Any, AsyncGenerator
from functools import lru_cache
import logging
from time import time
from contextvars import ContextVar

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send
from tortoise import Tortoise

from app.core.dependency import AuthControl
from app.models.admin import AuditLog, User
from app.models.tenant import Tenant

from .bgtask import BgTasks

logger = logging.getLogger(__name__)

tenant_context = ContextVar('tenant_context', default=None)


class SimpleBaseMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)

        response = await self.before_request(request) or self.app
        await response(request.scope, request.receive, send)
        await self.after_request(request)

    async def before_request(self, request: Request):
        return self.app

    async def after_request(self, request: Request):
        return None


class BackGroundTaskMiddleware(SimpleBaseMiddleware):
    async def before_request(self, request):
        await BgTasks.init_bg_tasks_obj()

    async def after_request(self, request):
        await BgTasks.execute_tasks()


class HttpAuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, methods: list[str], exclude_paths: list[str]):
        super().__init__(app)
        self.methods = methods
        self.exclude_paths = exclude_paths
        self.audit_log_paths = ["/api/v1/auditlog/list"]
        self.max_body_size = 1024 * 1024  # 1MB 响应体大小限制

    async def get_request_args(self, request: Request) -> dict:
        args = {}
        # 获取查询参数
        for key, value in request.query_params.items():
            args[key] = value

        # 获取请求体
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                args.update(body)
            except json.JSONDecodeError:
                try:
                    body = await request.form()
                    args.update(body)
                except Exception:
                    pass

        return args

    async def get_response_body(self, request: Request, response: Response) -> Any:
        # 检查Content-Length
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return {"code": 0, "msg": "Response too large to log", "data": None}

        if hasattr(response, "body"):
            body = response.body
        else:
            body_chunks = []
            async for chunk in response.body_iterator:
                if not isinstance(chunk, bytes):
                    chunk = chunk.encode(response.charset)
                body_chunks.append(chunk)

            response.body_iterator = self._async_iter(body_chunks)
            body = b"".join(body_chunks)

        if any(request.url.path.startswith(path) for path in self.audit_log_paths):
            try:
                data = self.lenient_json(body)
                # 只保留基本信息，去除详细的响应内容
                if isinstance(data, dict):
                    data.pop("response_body", None)
                    if "data" in data and isinstance(data["data"], list):
                        for item in data["data"]:
                            item.pop("response_body", None)
                return data
            except Exception:
                return None

        return self.lenient_json(body)

    def lenient_json(self, v: Any) -> Any:
        if isinstance(v, (str, bytes)):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                pass
        return v

    async def _async_iter(self, items: list[bytes]) -> AsyncGenerator[bytes, None]:
        for item in items:
            yield item

    async def get_request_log(self, request: Request, response: Response) -> dict:
        """
        根据request和response对象获取对应的日志记录数据
        """
        data: dict = {"path": request.url.path, "status": response.status_code, "method": request.method}
        # 路由信息
        app: FastAPI = request.app
        for route in app.routes:
            if (
                isinstance(route, APIRoute)
                and route.path_regex.match(request.url.path)
                and request.method in route.methods
            ):
                data["module"] = ",".join(route.tags)
                data["summary"] = route.summary
        # 获取用户信息
        try:
            token = request.headers.get("token")
            user_obj = None
            if token:
                user_obj: User = await AuthControl.is_authed(token)
            data["user_id"] = user_obj.id if user_obj else 0
            data["username"] = user_obj.username if user_obj else ""
        except Exception:
            data["user_id"] = 0
            data["username"] = ""
        return data

    async def before_request(self, request: Request):
        request_args = await self.get_request_args(request)
        request.state.request_args = request_args

    async def after_request(self, request: Request, response: Response, process_time: int):
        if request.method in self.methods:
            for path in self.exclude_paths:
                if re.search(path, request.url.path, re.I) is not None:
                    return
            data: dict = await self.get_request_log(request=request, response=response)
            data["response_time"] = process_time

            data["request_args"] = request.state.request_args
            data["response_body"] = await self.get_response_body(request, response)
            await AuditLog.create(**data)

        return response

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time: datetime = datetime.now()
        await self.before_request(request)
        response = await call_next(request)
        end_time: datetime = datetime.now()
        process_time = int((end_time.timestamp() - start_time.timestamp()) * 1000)
        await self.after_request(request, response, process_time)
        return response


class TenantMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
        self._tenant_cache = {}
        # 定义公共API路径前缀
        self.public_paths = [
            "/api/public/",
            "/api/auth/",
            "/api/system/"
        ]

    @lru_cache(maxsize=100)
    async def get_tenant(self, schema_name: str):
        return await Tenant.get_or_none(schema_name=schema_name, is_active=True)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        start_time = time()
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        current_connection = Tortoise.get_connection("default")
        default_search_path = "public"
        
        try:
            # 判断是否为公共API
            path = request.url.path
            is_public_api = any(path.startswith(prefix) for prefix in self.public_paths)
            
            if is_public_api:
                await current_connection.execute_script(f'SET search_path TO public')
                await self.app(scope, receive, send)
                return

            # 从Authorization头中获取token
            auth_header = request.headers.get("Authorization")
            tenant_schema_name = None
            
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    user_obj = await AuthControl.is_authed(token)
                    if user_obj and user_obj.tenant_id:
                        tenant = await Tenant.get_or_none(id=user_obj.tenant_id)
                        if tenant:
                            tenant_schema_name = tenant.schema_name
                            tenant_context.set(tenant)
                except Exception as e:
                    logger.error(f"Error getting tenant from token: {e}")

            if tenant_schema_name:
                try:
                    tenant = await self.get_tenant(tenant_schema_name)
                    if tenant:
                        logger.info(f"Switching to tenant schema: {tenant_schema_name}")
                        await current_connection.execute_script(f'SET search_path TO "{tenant_schema_name}", public')
                    else:
                        logger.warning(f"Tenant not found or not active: {tenant_schema_name}")
                        await current_connection.execute_script(f'SET search_path TO {default_search_path}')
                except Exception as e:
                    logger.error(f"Error setting tenant schema: {e}")
                    await current_connection.execute_script(f'SET search_path TO {default_search_path}')
            else:
                # 如果没有提供租户信息，则默认使用 public schema
                await current_connection.execute_script(f'SET search_path TO {default_search_path}')

            await self.app(scope, receive, send)
        finally:
            end_time = time()
            process_time = (end_time - start_time) * 1000
            if process_time > 1000:  # 超过1秒记录警告
                logger.warning(f"Tenant middleware processing time: {process_time}ms")
            try:
                await current_connection.execute_script(f'SET search_path TO {default_search_path}')
            except Exception as e:
                logger.error(f"Error resetting search path: {e}")
            tenant_context.set(None)
