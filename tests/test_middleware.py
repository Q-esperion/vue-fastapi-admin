import pytest
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
import jwt
from datetime import datetime, timezone, timedelta
from tortoise import Tortoise
import logging
import os
import asyncio
import sys
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from app.core.ctx import CTX_USER_ID, CTX_TENANT_ID
from app.settings import settings
from app.models.admin import User
from app.models.tenant import Tenant, TenantUser
from app.api.v1.base.base import router as base_router
from app.core.middlewares import TenantMiddleware, HttpAuditLogMiddleware
from app.utils.jwt import create_access_token
from app.schemas.login import JWTPayload

# 配置 pytest-asyncio
pytestmark = pytest.mark.asyncio

# 配置日志
logger = logging.getLogger(__name__)

# 创建测试应用
app = FastAPI()

# 添加中间件
app.add_middleware(TenantMiddleware)
app.add_middleware(HttpAuditLogMiddleware, methods=["GET", "POST", "PUT", "DELETE"], exclude_paths=["/docs", "/redoc", "/openapi.json"])

# 添加测试路由
@app.get("/api/v1/base/userinfo")
async def get_user_info():
    """获取用户信息"""
    return {"message": "User info"}

@app.get("/api/v1/role/list")
async def get_role_list():
    """获取角色列表"""
    return {"message": "Role list"}

# 添加公共API路由
@app.get("/api/public/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}

@app.get("/api/auth/login")
async def login():
    """登录接口"""
    return {"message": "Login"}

@app.get("/api/system/info")
async def system_info():
    """系统信息"""
    return {"message": "System info"}

# 数据库配置
DB_URL = os.getenv("TEST_DATABASE_URL", "postgres://postgres:postgres@localhost:5432/test_db")

# 测试数据存储类
class TestData:
    def __init__(self):
        self.test_user = None
        self.test_tenant = None
        self.test_tenant_user = None

test_data = TestData()

@asynccontextmanager
async def get_db_connection():
    """获取数据库连接的上下文管理器"""
    try:
        await Tortoise.init(
            db_url=DB_URL,
            modules={'models': ['app.models']}
        )
        yield
    finally:
        await Tortoise.close_connections()

async def init_db():
    """初始化数据库"""
    logger.info("开始初始化数据库...")
    
    async with get_db_connection():
        # 创建 public schema
        current_connection = Tortoise.get_connection("default")
        await current_connection.execute_script('CREATE SCHEMA IF NOT EXISTS public')
        logger.info("public schema 创建成功")
        
        # 创建测试 schema
        await current_connection.execute_script('CREATE SCHEMA IF NOT EXISTS test_schema')
        logger.info("test_schema 创建成功")
        
        # 设置搜索路径
        await current_connection.execute_script('SET search_path TO public')
        
        # 手动创建表
        await current_connection.execute_script("""
            -- 创建用户表
            CREATE TABLE IF NOT EXISTS public.user (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                username VARCHAR(20) UNIQUE,
                alias VARCHAR(30),
                email VARCHAR(255) UNIQUE,
                phone VARCHAR(20),
                password VARCHAR(128),
                is_active BOOLEAN DEFAULT TRUE,
                user_type VARCHAR(20) DEFAULT 'normal_user',
                is_superuser BOOLEAN DEFAULT FALSE,
                last_login TIMESTAMP WITH TIME ZONE,
                dept_id INTEGER,
                tenant_id INTEGER,
                is_tenant_admin BOOLEAN DEFAULT FALSE
            );

            -- 创建租户表
            CREATE TABLE IF NOT EXISTS public.tenant (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                name VARCHAR(100),
                schema_name VARCHAR(100) UNIQUE,
                status VARCHAR(20) DEFAULT 'inactive',
                description VARCHAR(500),
                contact_email VARCHAR(255),
                contact_phone VARCHAR(20),
                max_users INTEGER DEFAULT 10,
                expire_date DATE
            );

            -- 创建租户用户关联表
            CREATE TABLE IF NOT EXISTS public.tenant_user (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                tenant_id INTEGER REFERENCES public.tenant(id),
                user_id INTEGER REFERENCES public.user(id),
                is_admin BOOLEAN DEFAULT FALSE,
                department_id INTEGER,
                position VARCHAR(50),
                employee_id VARCHAR(50),
                UNIQUE(tenant_id, user_id)
            );
        """)
        logger.info("数据库表创建成功")

@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """设置数据库连接"""
    await init_db()
    yield
    await Tortoise.close_connections()

@pytest.fixture(autouse=True)
async def initialize_tests(caplog):
    """初始化测试环境"""
    caplog.set_level(logging.INFO)
    logger.info("开始初始化测试环境...")
    logger.info(f"使用数据库URL: {DB_URL}")
    
    async with get_db_connection():
        try:
            # 清理测试数据
            logger.info("清理测试数据...")
            await TenantUser.all().delete()
            await User.all().delete()
            await Tenant.all().delete()
            logger.info("测试数据清理完成")
            
            # 创建测试用户
            logger.info("创建测试用户...")
            test_data.test_user = await User.create(
                username="test_user",
                password="test_password",
                email="test@example.com"
            )
            logger.info(f"测试用户创建成功 - ID: {test_data.test_user.id}, 用户名: {test_data.test_user.username}")
            
            # 创建测试租户
            logger.info("创建测试租户...")
            test_data.test_tenant = await Tenant.create(
                name="test_tenant",
                schema_name="test_schema"
            )
            logger.info(f"测试租户创建成功 - ID: {test_data.test_tenant.id}, 名称: {test_data.test_tenant.name}, Schema: {test_data.test_tenant.schema_name}")
            
            # 创建租户用户关联
            logger.info("创建租户用户关联...")
            test_data.test_tenant_user = await TenantUser.create(
                user_id=test_data.test_user.id,
                tenant_id=test_data.test_tenant.id,
                is_admin=True
            )
            logger.info(f"租户用户关联创建成功 - 用户ID: {test_data.test_tenant_user.user_id}, 租户ID: {test_data.test_tenant_user.tenant_id}")
            
            yield
            
        except Exception as e:
            logger.error(f"数据库操作出错: {str(e)}")
            raise

def create_test_token(user_id: int, tenant_id: int = None, is_superuser: bool = False):
    """创建测试用的JWT token"""
    payload = JWTPayload(
        user_id=user_id,
        username="test_user",
        is_superuser=is_superuser,
        tenant_id=tenant_id,
        exp=datetime.now(timezone.utc) + timedelta(minutes=30)
    )
    token = create_access_token(data=payload)
    logger.info(f"创建测试Token - 用户ID: {user_id}, 租户ID: {tenant_id}, 超级用户: {is_superuser}")
    logger.info(f"Token payload: {payload.model_dump()}")
    return token

@pytest.mark.asyncio
async def test_auth_middleware(caplog):
    """测试认证中间件"""
    caplog.set_level(logging.INFO)
    logger.info("开始测试认证中间件...")
    
    async with get_db_connection():
        try:
            # 创建测试客户端
            client = TestClient(app)
            
            # 测试公共API访问
            logger.info("\n测试场景1: 访问公共API")
            response = client.get("/api/public/health")
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {response.json()}")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"
            
            # 测试带租户信息的token访问
            logger.info("\n测试场景2: 带租户信息的token访问")
            token = create_test_token(test_data.test_user.id, test_data.test_tenant.id)
            response = client.get(
                "/api/v1/base/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {response.json()}")
            assert response.status_code == 200
            assert response.json()["message"] == "User info"
            
            # 测试无效token
            logger.info("\n测试场景3: 无效token")
            response = client.get(
                "/api/v1/base/userinfo",
                headers={"Authorization": "Bearer invalid_token"}
            )
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {response.json()}")
            assert response.status_code == 200  # 中间件不会阻止请求，只会记录警告
            
            # 测试不带租户信息的token
            logger.info("\n测试场景4: 不带租户信息的token")
            token = create_test_token(test_data.test_user.id)
            response = client.get(
                "/api/v1/base/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {response.json()}")
            assert response.status_code == 200
            assert response.json()["message"] == "User info"
            
            logger.info("认证中间件测试完成")
        except Exception as e:
            logger.error(f"测试过程中出错: {str(e)}")
            raise

@pytest.mark.asyncio
async def test_permission_middleware(caplog):
    """测试权限中间件"""
    caplog.set_level(logging.INFO)
    logger.info("开始测试权限中间件...")
    
    async with get_db_connection():
        try:
            # 创建测试客户端
            client = TestClient(app)
            
            # 测试带租户信息的token访问
            logger.info("\n测试场景1: 带租户信息的token访问")
            token = create_test_token(test_data.test_user.id, test_data.test_tenant.id)
            response = client.get(
                "/api/v1/role/list",
                headers={"Authorization": f"Bearer {token}"}
            )
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {response.json()}")
            assert response.status_code == 200
            assert response.json()["message"] == "Role list"
            
            # 测试跨租户访问
            logger.info("\n测试场景2: 跨租户访问")
            other_tenant = await Tenant.create(
                name="other_tenant",
                schema_name="other_schema"
            )
            token = create_test_token(test_data.test_user.id, other_tenant.id)
            response = client.get(
                "/api/v1/role/list",
                headers={"Authorization": f"Bearer {token}"}
            )
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {response.json()}")
            assert response.status_code == 200
            assert response.json()["message"] == "Role list"
            
            # 测试系统API访问
            logger.info("\n测试场景3: 系统API访问")
            response = client.get("/api/system/info")
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {response.json()}")
            assert response.status_code == 200
            assert response.json()["message"] == "System info"
            
            logger.info("权限中间件测试完成")
        except Exception as e:
            logger.error(f"测试过程中出错: {str(e)}")
            raise 