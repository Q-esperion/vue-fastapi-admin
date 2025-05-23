# 新增model需要在这里导入
from app.models.admin import User, Role, Api, Menu, Dept, DeptClosure, AuditLog
from app.models.tenant import Tenant, TenantPermission, TenantUser
from app.models.tenant_schema import (
    TenantDept, TenantRole, TenantApi, TenantMenu, TenantDeptClosure
)

__all__ = [
    "User", "Role", "Api", "Menu", "Dept", "DeptClosure", "AuditLog",
    "Tenant", "TenantPermission", "TenantUser",
    "TenantDept", "TenantRole", "TenantApi", "TenantMenu", "TenantDeptClosure"
]
