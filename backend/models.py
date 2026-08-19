from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String

from database import Base


class AppConfig(Base):
    """
    通用 KV 配置表（和已有 MySQL 里的 `config` 表对齐）。
    configKey 字段带 oss. 前缀的 4 行用于存 OSS 凭证：
      - oss.endpoint          例如 oss-cn-beijing.aliyuncs.com
      - oss.accessKeyId
      - oss.accessKeySecret
      - oss.bucketName
    """

    __tablename__ = "config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    configKey = Column(String(100), unique=True, nullable=False)
    configValue = Column(String(1000), nullable=False)


class PdfFile(Base):
    """PDF 文件元数据表（文件本身存在 OSS，这里只存链接/元数据）"""

    __tablename__ = "pdf_files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    original_name = Column(String(255), nullable=False, comment="用户上传时的原始文件名")
    oss_key = Column(String(512), nullable=False, comment="OSS 中的对象 key，如 pdfs/2026/08/xxx.pdf")
    file_size = Column(BigInteger, nullable=False, comment="文件大小（字节）")
    mime_type = Column(String(100), default="application/pdf", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_pdf_created_at", "created_at"),
        Index("idx_pdf_oss_key", "oss_key"),
    )
