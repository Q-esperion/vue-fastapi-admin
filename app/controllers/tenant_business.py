from typing import List, Optional
from tortoise.expressions import Q

from app.models.tenant_schema import (
    TenantDept, TenantRole, TenantApi, TenantMenu, TenantDeptClosure
)
from app.controllers.base import TenantService

class TenantDeptController:
    """租户部门控制器"""
    
    def __init__(self, schema_name: str):
        self.service = TenantService(schema_name)
    
    async def create_dept(self, data: dict) -> TenantDept:
        """创建部门"""
        return await self.service.execute_in_schema(
            lambda: TenantDept.create(**data)
        )
    
    async def get_dept_tree(self) -> List[dict]:
        """获取部门树"""
        depts = await self.service.execute_in_schema(
            lambda: TenantDept.filter(is_deleted=False).all()
        )
        return await self._build_dept_tree(depts)
    
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

class TenantRoleController:
    """租户角色控制器"""
    
    def __init__(self, schema_name: str):
        self.service = TenantService(schema_name)
    
    async def create_role(self, data: dict) -> TenantRole:
        """创建角色"""
        return await self.service.execute_in_schema(
            lambda: TenantRole.create(**data)
        )
    
    async def assign_permissions(
        self,
        role_id: int,
        menu_ids: List[int],
        api_ids: List[int]
    ) -> None:
        """分配权限"""
        async def update_role_permissions():
            role = await TenantRole.get(id=role_id)
            # 分配菜单权限
            if menu_ids:
                await role.menus.clear()
                await role.menus.add(*menu_ids)
            # 分配API权限
            if api_ids:
                await role.apis.clear()
                await role.apis.add(*api_ids)
        
        await self.service.execute_in_schema(update_role_permissions)
    
    async def get_role_permissions(self, role_id: int) -> dict:
        """获取角色权限"""
        async def fetch_role_permissions():
            role = await TenantRole.get(id=role_id).prefetch_related('menus', 'apis')
            return {
                'menus': await role.menus.all().values(),
                'apis': await role.apis.all().values()
            }
        
        return await self.service.execute_in_schema(fetch_role_permissions)

class TenantMenuController:
    """租户菜单控制器"""
    
    def __init__(self, schema_name: str):
        self.service = TenantService(schema_name)
    
    async def get_menu_tree(self) -> List[dict]:
        """获取菜单树"""
        menus = await self.service.execute_in_schema(
            lambda: TenantMenu.filter(is_enabled=True).all()
        )
        return await self._build_menu_tree(menus)
    
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

class TenantApiController:
    """租户API控制器"""
    
    def __init__(self, schema_name: str):
        self.service = TenantService(schema_name)
    
    async def get_enabled_apis(self) -> List[TenantApi]:
        """获取启用的API列表"""
        return await self.service.execute_in_schema(
            lambda: TenantApi.filter(is_enabled=True).all()
        )
    
    async def update_api_status(self, api_id: int, is_enabled: bool) -> bool:
        """更新API状态"""
        updated = await self.service.execute_in_schema(
            lambda: TenantApi.filter(id=api_id).update(is_enabled=is_enabled)
        )
        return updated > 0 