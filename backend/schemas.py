from datetime import datetime, timezone, timedelta

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

# 北京时间时区（统一用于「响应序列化」层）
CST = timezone(timedelta(hours=8))


class PdfFileOut(BaseModel):
    """PDF 文件元数据响应"""

    id: int
    original_name: str
    file_size: int
    mime_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_tz(cls, v):
        """
        读库出来的 DATETIME 是 naive（无时区）的：
          - 新代码存的是北京时间墙钟 → 补 +08:00
          - 旧数据（datetime.utcnow() 存进 UTC 时区的 MySQL）已经在修复脚本里
            DATE_ADD +8 小时 统一迁移过 → 也是北京时间墙钟，同样补 +08:00
        """
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=CST)
        return v

    @field_serializer("created_at")
    def _serialize_cst(self, v: datetime) -> str:
        """序列化为 ISO-8601，结尾固定带 +08:00，前端不会误读。"""
        if v.tzinfo is None:
            v = v.replace(tzinfo=CST)
        else:
            v = v.astimezone(CST)
        return v.isoformat()


class SignedUrlOut(BaseModel):
    """OSS 临时签名 URL"""

    url: str


class HealthOut(BaseModel):
    status: str
