import logging
from typing import List

from fastapi import APIRouter, Depends, Query
from tortoise.expressions import Q

from app.controllers.tenant import tenant_controller
from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.tenants import TenantCreate, TenantInDB, TenantUpdate
from app.schemas.base import Success, Fail, SuccessExtra

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tenants")
async def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query(None),
    current_user: User = Depends(AuthControl.is_authed),
):
    """获取租户列表"""
    if not current_user.is_superuser:
        # 非超级管理员只能查看自己负责的租户
        tenants = await tenant_controller.get_by_owner(current_user.id)
        return Success(data=tenants)
    
    # 超级管理员可以查看所有租户
    search_query = Q()
    if search:
        search_query = Q(name__icontains=search) | Q(schema_name__icontains=search)
    
    total, tenants = await tenant_controller.list_with_owner(page, page_size, search_query)
    return SuccessExtra(data=tenants, total=total, page=page, page_size=page_size)


@router.post("/tenants")
async def create_tenant(
    tenant_in: TenantCreate,
):
    """创建租户"""
    tenant = await tenant_controller.create(tenant_in)
    return Success(data=tenant)


@router.get("/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: int,
    current_user: User = Depends(AuthControl.is_authed),
):
    """获取租户详情"""
    tenant = await tenant_controller.get(tenant_id)
    if not current_user.is_superuser and tenant.owner_id != current_user.id:
        return Fail(code=403, msg="权限不足")
    
    return Success(data=tenant)


@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: int,
    tenant_in: TenantUpdate,
    current_user: User = Depends(AuthControl.is_authed),
):
    """更新租户信息"""
    tenant = await tenant_controller.get(tenant_id)
    if not current_user.is_superuser and tenant.owner_id != current_user.id:
        return Fail(code=403, msg="权限不足")
    
    tenant = await tenant_controller.update(tenant_id, tenant_in)
    return Success(data=tenant)


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
):
    """删除租户"""
    await tenant_controller.remove(tenant_id)
    return Success(msg="删除成功")


@router.post("/tenants/{tenant_id}/owner")
async def set_tenant_owner(
    tenant_id: int,
    user_id: int,
):
    """设置租户负责人"""
    try:
        tenant = await tenant_controller.set_owner(tenant_id, user_id)
        return Success(data=tenant)
    except Exception as e:
        return Fail(code=400, msg=f"设置负责人失败: {str(e)}") 