from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PdfFileOut(BaseModel):
    """PDF 文件元数据响应"""

    id: int
    original_name: str
    file_size: int
    mime_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SignedUrlOut(BaseModel):
    """OSS 临时签名 URL"""

    url: str


class HealthOut(BaseModel):
    status: str
