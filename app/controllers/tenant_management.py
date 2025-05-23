from typing import Optional, List
from tortoise import Tortoise

from app.models.tenant import Tenant, TenantPermission, TenantUser
from app.models.tenant_schema import TenantDept, TenantRole, TenantApi, TenantMenu
from app.controllers.base import BaseService

class TenantManagementController:
    """租户管理控制器"""
    
    async def create_tenant_schema(self, tenant: Tenant) -> None:
        """创建租户schema"""
        schema_name = f"tenant_{tenant.id}"
        current_connection = Tortoise.get_connection("default")
        
        # 创建schema
        await current_connection.execute_script(f'CREATE SCHEMA IF NOT EXISTS {schema_name}')
        
        # 复制表结构
        tables = await current_connection.execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('dept', 'role', 'api', 'menu', 'dept_closure')
        """)
        
        for table in tables[1]:
            await current_connection.execute_script(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.{table[0]} 
                (LIKE public.{table[0]} INCLUDING ALL)
            """)

    async def delete_tenant_schema(self, tenant: Tenant) -> None:
        """删除租户schema"""
        schema_name = f"tenant_{tenant.id}"
        current_connection = Tortoise.get_connection("default")
        await current_connection.execute_script(f'DROP SCHEMA IF EXISTS {schema_name} CASCADE')

    async def sync_tenant_permissions(self, tenant: Tenant) -> None:
        """同步租户权限"""
        # 获取租户权限配置
        permissions = await TenantPermission.filter(tenant=tenant, is_enabled=True)
        
        # 在租户schema中更新权限
        schema_name = f"tenant_{tenant.id}"
        service = BaseService(schema_name)
        
        async def update_permissions():
            # 更新API权限
            for permission in permissions:
                if permission.api:
                    await TenantApi.filter(id=permission.api.id).update(is_enabled=True)
            
            # 更新菜单权限
            for permission in permissions:
                if permission.menu:
                    await TenantMenu.filter(id=permission.menu.id).update(is_enabled=True)
        
        await service.execute_in_schema(update_permissions)

class TenantUserController:
    """租户用户控制器"""
    
    async def create_tenant_user(self, tenant_id: int, user_id: int, is_admin: bool = False) -> TenantUser:
        """创建租户用户"""
        return await TenantUser.create(
            tenant_id=tenant_id,
            user_id=user_id,
            is_admin=is_admin
        )
    
    async def get_tenant_users(self, tenant_id: int) -> list[TenantUser]:
        """获取租户用户列表"""
        return await TenantUser.filter(tenant_id=tenant_id).prefetch_related('user')
    
    async def remove_tenant_user(self, tenant_id: int, user_id: int) -> bool:
        """移除租户用户"""
        deleted_count = await TenantUser.filter(
            tenant_id=tenant_id,
            user_id=user_id
        ).delete()
        return deleted_count > 0

class TenantPermissionController:
    """租户权限控制器"""
    
    async def get_tenant_permissions(self, tenant_id: int) -> list[TenantPermission]:
        """获取租户权限配置"""
        return await TenantPermission.filter(tenant_id=tenant_id).prefetch_related('api', 'menu')
    
    async def update_tenant_permissions(
        self,
        tenant_id: int,
        api_ids: list[int],
        menu_ids: list[int]
    ) -> None:
        """更新租户权限配置"""
        # 删除现有权限
        await TenantPermission.filter(tenant_id=tenant_id).delete()
        
        # 创建新权限
        for api_id in api_ids:
            for menu_id in menu_ids:
                await TenantPermission.create(
                    tenant_id=tenant_id,
                    api_id=api_id,
                    menu_id=menu_id
                )
        
        # 同步到租户schema
        tenant = await Tenant.get(id=tenant_id)
        await TenantManagementController().sync_tenant_permissions(tenant)

class TenantDeptController:
    """租户部门控制器"""
    
    async def _build_dept_tree(self, depts: List[TenantDept], parent_id: int = 0) -> List[dict]:
        """构建部门树"""
        tree = []
        for dept in depts:
            if dept.parent_id == parent_id:
                node = await dept.to_dict()
                children = await self._build_dept_tree(depts, dept.id)
                if children:
                    node['children'] = children
                tree.append(node)
        return tree

class TenantMenuController:
    """租户菜单控制器"""
    
    async def _build_menu_tree(self, menus: List[TenantMenu], parent_id: int = 0) -> List[dict]:
        """构建菜单树"""
        tree = []
        for menu in menus:
            if menu.parent_id == parent_id:
                node = await menu.to_dict()
                children = await self._build_menu_tree(menus, menu.id)
                if children:
                    node['children'] = children
                tree.append(node)
        return tree 