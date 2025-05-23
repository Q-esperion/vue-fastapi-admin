import contextvars

from starlette.background import BackgroundTasks
from contextvars import ContextVar

CTX_USER_ID = ContextVar("user_id", default=None)
CTX_BG_TASKS: contextvars.ContextVar[BackgroundTasks] = contextvars.ContextVar("bg_task", default=None)
CTX_TENANT_ID = ContextVar("tenant_id", default=None)
