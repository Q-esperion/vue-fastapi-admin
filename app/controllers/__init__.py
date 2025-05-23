from .role import role_controller as role_controller
from .user import user_controller as user_controller
from app.controllers.tenant_management import TenantManagementController, TenantUserController, TenantPermissionController
from app.controllers.tenant_business import TenantDeptController, TenantRoleController, TenantMenuController, TenantApiController

__all__ = [
    'TenantManagementController',
    'TenantUserController',
    'TenantPermissionController',
    'TenantDeptController',
    'TenantRoleController',
    'TenantMenuController',
    'TenantApiController'
]
