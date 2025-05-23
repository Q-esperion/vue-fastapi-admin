from tortoise import fields, models

from app.models.base import BaseModel, TimestampMixin
from app.models.enums import TenantStatus

class Tenant(BaseModel):
    """租户模型"""
    name = fields.CharField(max_length=100, description="租户名称")
    schema_name = fields.CharField(max_length=100, unique=True, description="数据库schema名称")
    status = fields.CharField(max_length=20, default="inactive", description="租户状态")
    description = fields.CharField(max_length=500, null=True, description="租户描述")
    contact_email = fields.CharField(max_length=255, null=True, description="联系邮箱")
    contact_phone = fields.CharField(max_length=20, null=True, description="联系电话")
    max_users = fields.IntField(default=10, description="最大用户数")
    expire_date = fields.DateField(null=True, description="过期时间")

    class Meta:
        table = "tenant"
        schema = "public"
        table_description = "租户表"

class TenantPermission(BaseModel, TimestampMixin):
    """租户权限配置表"""
    tenant = fields.ForeignKeyField('models.Tenant', related_name='permissions', description="租户")
    api = fields.ForeignKeyField('models.Api', related_name='tenant_permissions', description="API")
    menu = fields.ForeignKeyField('models.Menu', related_name='tenant_permissions', description="菜单")
    is_enabled = fields.BooleanField(default=True, description="是否启用")

    class Meta:
        table = "tenant_permission"
        table_description = "租户权限配置表"
        schema = "public"
        unique_together = (("tenant", "api", "menu"),)

class TenantUser(BaseModel):
    """租户用户关联模型"""
    tenant = fields.ForeignKeyField("models.Tenant", related_name="users", description="租户")
    user = fields.ForeignKeyField("models.User", related_name="tenants", description="用户")
    is_admin = fields.BooleanField(default=False, description="是否为租户管理员")
    department_id = fields.IntField(null=True, description="部门ID")
    position = fields.CharField(max_length=50, null=True, description="职位")
    employee_id = fields.CharField(max_length=50, null=True, description="员工编号")

    class Meta:
        table = "tenant_user"
        table_description = "租户用户关联表"
        unique_together = (("tenant", "user"),) 