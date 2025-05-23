from typing import List, Tuple

from tortoise import Tortoise
from tortoise.expressions import Q

from app.core.crud import CRUDBase, ModelType, UpdateSchemaType
from app.models.tenant import Tenant
from app.models.admin import User
from app.schemas.tenants import TenantCreate, TenantUpdate
from app.settings.config import settings # 导入 settings


class TenantController(CRUDBase[Tenant, TenantCreate, TenantUpdate]):
    def __init__(self):
        super().__init__(Tenant)

    async def create(self, obj_in: TenantCreate) -> Tenant:
        """创建租户，并在public schema中记录，然后创建租户专属schema和表"""
        # 确保在 public schema 中操作 Tenant 表
        current_connection = Tortoise.get_connection("default")
        await current_connection.execute_script('SET search_path TO public')

        tenant_dict = obj_in.model_dump()
        # 1. 在 public.tenant 表中创建租户记录
        # Tortoise ORM 对于指定了 Meta.schema 的模型会自动使用对应 schema
        tenant = await self.model.create(**tenant_dict)

        try:
            # 2. 创建租户专属的 PostgreSQL schema
            await current_connection.execute_script(f'CREATE SCHEMA IF NOT EXISTS "{tenant.schema_name}"')

            # 3. 在新创建的租户 schema 中生成所有业务表
            # 设置 search_path 以确保 generate_schemas 在正确的 schema 中操作
            await current_connection.execute_script(f'SET search_path TO "{tenant.schema_name}", public')
            
            # 获取所有注册的应用模型 (除了 Tenant 本身，因为它在 public)
            # Tortoise.apps 包含所有通过 TORTOISE_ORM 配置注册的应用
            # 我们需要确保 app.models.admin 中的其他模型也被正确生成
            
            await Tortoise.generate_schemas(safe=True) # safe=True 避免删除已存在表

        except Exception as e:
            # 如果 schema 或表创建失败，回滚 public.tenant 中的记录
            await tenant.delete() # 假设 Tenant 模型有 delete 方法
            # 恢复 search_path
            await current_connection.execute_script('SET search_path TO public')
            raise e # 重新抛出异常，让上层处理
        
        # 恢复 search_path 到 public，或让中间件处理后续请求的 search_path
        await current_connection.execute_script('SET search_path TO public')
        
        return tenant

    async def get_by_schema_name(self, schema_name: str) -> Tenant:
        # 确保从 public.tenant 查询
        current_connection = Tortoise.get_connection("default")
        await current_connection.execute_script('SET search_path TO public')
        tenant = await self.model.get_or_none(schema_name=schema_name)
        await current_connection.execute_script('SET search_path TO public') # 恢复
        return tenant

    async def get_by_owner(self, owner_id: int) -> List[Tenant]:
        # 确保从 public.tenant 查询
        current_connection = Tortoise.get_connection("default")
        await current_connection.execute_script('SET search_path TO public')
        tenants = await self.model.filter(owner_id=owner_id).all()
        await current_connection.execute_script('SET search_path TO public') # 恢复
        return tenants

    async def list_with_owner(
        self, page: int, page_size: int, search: Q = Q(), order: list = []
    ) -> Tuple[int, List[Tenant]]:
        # 确保从 public.tenant 查询
        current_connection = Tortoise.get_connection("default")
        await current_connection.execute_script('SET search_path TO public')
        query = self.model.filter(search).prefetch_related("owner")
        count = await query.count()
        items = await query.offset((page - 1) * page_size).limit(page_size).order_by(*order).all()
        await current_connection.execute_script('SET search_path TO public') # 恢复
        return count, items

    async def set_owner(self, tenant_id: int, user_id: int) -> Tenant:
        """设置租户负责人"""
        current_connection = Tortoise.get_connection("default")
        await current_connection.execute_script('SET search_path TO public')
        tenant = await self.get(tenant_id) # self.get 内部应该也处理 search_path
        user = await User.get(id=user_id) # User 表应该在租户 schema 或 public (取决于User是否共享)
        tenant.owner = user
        await tenant.save()
        await current_connection.execute_script('SET search_path TO public') # 恢复
        return tenant
    
    async def get(self, id: int) -> Tenant: # 重写 get 以确保从 public schema 获取 Tenant
        current_connection = Tortoise.get_connection("default")
        await current_connection.execute_script('SET search_path TO public')
        instance = await super().get(id)
        await current_connection.execute_script('SET search_path TO public')
        return instance

    async def update(self, id: int, obj_in: UpdateSchemaType) -> ModelType:
        current_connection = Tortoise.get_connection("default")
        await current_connection.execute_script('SET search_path TO public')
        instance = await super().update(id, obj_in)
        await current_connection.execute_script('SET search_path TO public')
        return instance

    async def remove(self, id: int) -> None:
        # 删除租户时，还需要考虑删除其 schema
        current_connection = Tortoise.get_connection("default")
        await current_connection.execute_script('SET search_path TO public')
        tenant = await self.get(id)
        if tenant:
            # 1. 删除 public.tenant 中的记录
            await super().remove(id)
            # 2. 删除租户的 schema
            try:
                await current_connection.execute_script(f'DROP SCHEMA IF EXISTS "{tenant.schema_name}" CASCADE')
            except Exception as e:
                # 记录 schema 删除失败的错误，但继续，因为元数据已删除
                print(f"Error dropping schema {tenant.schema_name}: {e}")
        await current_connection.execute_script('SET search_path TO public')

tenant_controller = TenantController() 