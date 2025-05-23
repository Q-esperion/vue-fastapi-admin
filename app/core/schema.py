# app/core/schema.py
class SchemaManager:
    @staticmethod
    async def set_schema(schema_name: str):
        async with Tortoise.get_connection("default") as conn:
            await conn.execute_query(f'SET search_path TO {schema_name}')
    
    @staticmethod
    async def get_current_schema() -> str:
        async with Tortoise.get_connection("default") as conn:
            result = await conn.execute_query('SHOW search_path')
            return result[1][0][0]