from tortoise import fields

from app.models.base import BaseModel, TimestampMixin
from app.models.enums import MethodType
from app.schemas.menus import MenuType

class TenantDept(BaseModel, TimestampMixin):
    """租户部门表"""
    name = fields.CharField(max_length=20, unique=True, description="部门名称", index=True)
    desc = fields.CharField(max_length=500, null=True, description="备注")
    is_deleted = fields.BooleanField(default=False, description="软删除标记", index=True)
    order = fields.IntField(default=0, description="排序", index=True)
    parent_id = fields.IntField(default=0, max_length=10, description="父部门ID", index=True)

    class Meta:
        table = "dept"
        table_description = "租户部门表"

class TenantRole(BaseModel, TimestampMixin):
    """租户角色表"""
    name = fields.CharField(max_length=20, unique=True, description="角色名称", index=True)
    desc = fields.CharField(max_length=500, null=True, description="角色描述")
    menus = fields.ManyToManyField("models.TenantMenu", related_name="role_menus")
    apis = fields.ManyToManyField("models.TenantApi", related_name="role_apis")

    class Meta:
        table = "role"
        table_description = "租户角色表"

class TenantApi(BaseModel, TimestampMixin):
    """租户API表"""
    path = fields.CharField(max_length=100, description="API路径", index=True)
    method = fields.CharEnumField(MethodType, description="请求方法", index=True)
    summary = fields.CharField(max_length=500, null=True, description="请求简介", index=True)
    tags = fields.CharField(max_length=100, description="API标签", index=True)
    is_enabled = fields.BooleanField(default=True, description="是否启用")

    class Meta:
        table = "api"
        table_description = "租户API表"

class TenantMenu(BaseModel, TimestampMixin):
    """租户菜单表"""
    name = fields.CharField(max_length=20, description="菜单名称", index=True)
    remark = fields.JSONField(null=True, description="保留字段")
    menu_type = fields.CharEnumField(MenuType, null=True, description="菜单类型")
    icon = fields.CharField(max_length=100, null=True, description="菜单图标")
    path = fields.CharField(max_length=100, description="菜单路径", index=True)
    order = fields.IntField(default=0, description="排序", index=True)
    parent_id = fields.IntField(default=0, description="父菜单ID", index=True)
    is_hidden = fields.BooleanField(default=False, description="是否隐藏")
    component = fields.CharField(max_length=100, description="组件")
    keepalive = fields.BooleanField(default=True, description="存活")
    redirect = fields.CharField(max_length=100, null=True, description="重定向")
    is_enabled = fields.BooleanField(default=True, description="是否启用")

    class Meta:
        table = "menu"
        table_description = "租户菜单表"

class TenantDeptClosure(BaseModel, TimestampMixin):
    """租户部门闭包表"""
    ancestor = fields.IntField(description="父代", index=True)
    descendant = fields.IntField(description="子代", index=True)
    level = fields.IntField(default=0, description="深度", index=True)

    class Meta:
        table = "dept_closure"
        table_description = "租户部门闭包表" 