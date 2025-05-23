from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request

from app.core.ctx import CTX_USER_ID, CTX_TENANT_ID
from app.models import Role, User, Tenant, TenantUser
from app.settings import settings
from app.controllers.base import BaseService


class AuthControl:
    @classmethod
    async def is_authed(cls, token: str = Header(..., description="token验证")) -> Optional["User"]:
        try:
            if token == "dev":
                user = await User.filter().first()
                user_id = user.id
                tenant_id = None
            else:
                decode_data = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
                user_id = decode_data.get("user_id")
                tenant_id = decode_data.get("tenant_id")
            
            user = await User.filter(id=user_id).first()
            if not user:
                raise HTTPException(status_code=401, detail="Authentication failed")
            
            # 设置上下文变量
            CTX_USER_ID.set(int(user_id))
            if tenant_id:
                CTX_TENANT_ID.set(int(tenant_id))
                # 验证用户是否属于该租户
                tenant_user = await TenantUser.filter(user_id=user_id, tenant_id=tenant_id).first()
                if not tenant_user:
                    raise HTTPException(status_code=403, detail="User does not belong to this tenant")
            
            return user
        except jwt.DecodeError:
            raise HTTPException(status_code=401, detail="无效的Token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="登录已过期")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{repr(e)}")


class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        if current_user.is_superuser:
            return
        
        # 获取当前租户ID
        tenant_id = CTX_TENANT_ID.get()
        if not tenant_id:
            raise HTTPException(status_code=403, detail="Tenant context not found")
        
        method = request.method
        path = request.url.path
        
        # 在租户schema中验证权限
        schema_name = f"tenant_{tenant_id}"
        service = BaseService(schema_name)
        
        async def check_permission():
            roles: list[Role] = await current_user.roles
            if not roles:
                raise HTTPException(status_code=403, detail="The user is not bound to a role")
            
            apis = [await role.apis for role in roles]
            permission_apis = list(set((api.method, api.path) for api in sum(apis, [])))
            
            if (method, path) not in permission_apis:
                raise HTTPException(status_code=403, detail=f"Permission denied method:{method} path:{path}")
        
        await service.execute_in_schema(check_permission)


DependAuth = Depends(AuthControl.is_authed)
DependPermisson = Depends(PermissionControl.has_permission)
