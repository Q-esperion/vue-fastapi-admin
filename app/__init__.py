from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise

from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_data,
    make_middlewares,
    register_exceptions,
    register_routers,
)

try:
    from app.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化 Tortoise ORM
    await Tortoise.init(config=settings.TORTOISE_ORM)
    # 生成数据库表
    await Tortoise.generate_schemas()
    
    # 初始化其他数据
    await init_data()
    yield
    
    # 关闭数据库连接
    await Tortoise.close_connections()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        lifespan=lifespan,
    )
    app.middleware = make_middlewares()
    register_exceptions(app)
    register_routers(app)
    return app


app = create_app()
