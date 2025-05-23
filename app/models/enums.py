from enum import Enum, StrEnum


class EnumBase(Enum):
    @classmethod
    def get_member_values(cls):
        return [item.value for item in cls._member_map_.values()]

    @classmethod
    def get_member_names(cls):
        return [name for name in cls._member_names_]


class MethodType(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class UserType(str, Enum):
    SUPER_ADMIN = "super_admin"  # 超级管理员
    TENANT_ADMIN = "tenant_admin"  # 租户管理员
    NORMAL_USER = "normal_user"  # 普通用户


class TenantStatus(str, Enum):
    ACTIVE = "active"  # 激活
    INACTIVE = "inactive"  # 未激活
    SUSPENDED = "suspended"  # 已暂停
