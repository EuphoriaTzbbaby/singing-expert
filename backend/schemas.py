from datetime import datetime, timezone, timedelta
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

# 北京时间时区（统一用于「响应序列化」层）
CST = timezone(timedelta(hours=8))


def _serialize_cst(v: datetime) -> str:
    """序列化为 ISO-8601，结尾固定带 +08:00，前端不会误读。"""
    if v.tzinfo is None:
        v = v.replace(tzinfo=CST)
    else:
        v = v.astimezone(CST)
    return v.isoformat()


class PdfFileOut(BaseModel):
    """PDF 文件元数据响应"""

    id: int
    original_name: str
    file_size: int
    mime_type: str
    created_at: datetime
    group_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_tz(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=CST)
        return v

    @field_serializer("created_at")
    def _ser_created(self, v: datetime) -> str:
        return _serialize_cst(v)


class GroupCreate(BaseModel):
    """创建分组请求"""

    name: str = Field(..., min_length=1, max_length=100)


class GroupOut(BaseModel):
    """分组响应（带文件数）"""

    id: int
    name: str
    created_at: datetime
    file_count: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_tz(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=CST)
        return v

    @field_serializer("created_at")
    def _ser_created(self, v: datetime) -> str:
        return _serialize_cst(v)


class FileUpdateIn(BaseModel):
    """更新文件（移动分组 + 重命名）"""

    group_id: Optional[int] = None  # None = 移到未分组
    original_name: Optional[str] = None  # 重命名


class SignedUrlOut(BaseModel):
    """OSS 临时签名 URL"""

    url: str


class HealthOut(BaseModel):
    status: str


# ==================== 认证 ====================


class LoginIn(BaseModel):
    """登录请求"""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class RegisterIn(BaseModel):
    """注册请求"""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class TokenOut(BaseModel):
    """登录成功返回的 token"""

    access_token: str
    token_type: str = "bearer"
    username: str


class UserOut(BaseModel):
    """用户信息"""

    id: int
    username: str
    is_admin: bool = False

    model_config = ConfigDict(from_attributes=True)


# ==================== 管理端 ====================


class UserAdminOut(BaseModel):
    """管理员视角的用户列表项"""

    id: int
    username: str
    is_admin: bool
    created_at: datetime
    file_count: int = 0
    storage_bytes: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_tz(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=CST)
        return v

    @field_serializer("created_at")
    def _ser_created(self, v: datetime) -> str:
        return _serialize_cst(v)


class PdfFileAdminOut(BaseModel):
    """管理员视角的文件列表项（带 owner username + group name）"""

    id: int
    original_name: str
    file_size: int
    mime_type: str
    created_at: datetime
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    user_id: Optional[int] = None
    owner_username: Optional[str] = None  # NULL=公共

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_tz(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=CST)
        return v

    @field_serializer("created_at")
    def _ser_created(self, v: datetime) -> str:
        return _serialize_cst(v)


class GroupAdminOut(BaseModel):
    """管理员视角的分组列表项"""

    id: int
    name: str
    created_at: datetime
    user_id: Optional[int] = None
    owner_username: Optional[str] = None  # NULL=公共
    file_count: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_tz(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=CST)
        return v

    @field_serializer("created_at")
    def _ser_created(self, v: datetime) -> str:
        return _serialize_cst(v)


class StatsOut(BaseModel):
    """系统总览统计"""

    user_count: int
    file_count: int
    total_storage_bytes: int
    group_count: int
    public_file_count: int
    recent_uploads: list[PdfFileAdminOut]


class ResetPasswordIn(BaseModel):
    """管理员重置用户密码请求"""

    new_password: str = Field(..., min_length=6, max_length=128)


class SetAdminIn(BaseModel):
    """修改管理员标志请求"""

    is_admin: bool
