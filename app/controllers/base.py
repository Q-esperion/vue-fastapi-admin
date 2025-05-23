from typing import Any, Callable, Optional
from tortoise import Tortoise

class BaseService:
    """基础服务类"""
    
    def __init__(self, schema_name: str = "public"):
        self.schema_name = schema_name
    
    async def execute_in_schema(self, func: Callable) -> Any:
        """在指定schema中执行函数"""
        # 保存当前schema
        current_schema = await self.get_current_schema()
        
        try:
            # 切换到目标schema
            await self.set_schema(self.schema_name)
            # 执行函数
            return await func()
        finally:
            # 恢复原schema
            await self.set_schema(current_schema)
    
    @staticmethod
    async def get_current_schema() -> str:
        """获取当前schema"""
        connection = Tortoise.get_connection("default")
        result = await connection.execute_query("SELECT current_schema()")
        return result[1][0][0]
    
    @staticmethod
    async def set_schema(schema_name: str) -> None:
        """设置当前schema"""
        connection = Tortoise.get_connection("default")
        await connection.execute_query(f'SET search_path TO {schema_name}')

class TenantService(BaseService):
    """租户服务类"""
    
    def __init__(self, schema_name: str):
        super().__init__(schema_name)
    
    async def get_tenant_data(self, model_class: Any, **filters) -> Any:
        """获取租户数据"""
        return await self.execute_in_schema(
            lambda: model_class.filter(**filters).all()
        )
    
    async def get_public_data(self, model_class: Any, **filters) -> Any:
        """获取公共数据"""
        return await model_class.filter(**filters).all() 