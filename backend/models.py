from datetime import datetime, timezone, timedelta

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String

from database import Base

# 北京时间时区 = UTC + 8 小时
CST = timezone(timedelta(hours=8))


def _now_cst() -> datetime:
    """返回「带 +08:00 时区信息」的当前北京时间。

    MySQL 的 DATETIME 列本身不带时区，存的时候会把 wall-clock（墙钟）部分写入；
    但 Pydantic 读出来时会感知这个 tzinfo，响应 JSON 自动序列化成
    '2026-08-19T21:04:17+08:00' —— 前端 JS 就不会把它误解成本地 13:04 了。
    """
    return datetime.now(tz=CST)


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


class Group(Base):
    """文件分组表"""

    __tablename__ = "groups"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="分组名称")
    created_at = Column(DateTime(timezone=False), default=_now_cst, nullable=False)

    __table_args__ = (Index("idx_group_name", "name"),)


class PdfFile(Base):
    """PDF 文件元数据表（文件本身存在 OSS，这里只存链接/元数据）"""

    __tablename__ = "pdf_files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    original_name = Column(String(255), nullable=False, comment="用户上传时的原始文件名")
    oss_key = Column(String(512), nullable=False, comment="OSS 中的对象 key，如 pdfs/2026/08/xxx.pdf")
    file_size = Column(BigInteger, nullable=False, comment="文件大小（字节）")
    mime_type = Column(String(100), default="application/pdf", nullable=False)
    # ↓ 关键修复：从 datetime.utcnow 改为 now_cst（北京时间，含时区信息）
    created_at = Column(DateTime(timezone=False), default=_now_cst, nullable=False)
    # 分组外键（可空 = 未分组）
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, comment="所属分组ID")

    __table_args__ = (
        Index("idx_pdf_created_at", "created_at"),
        Index("idx_pdf_oss_key", "oss_key"),
        Index("idx_pdf_group_id", "group_id"),
    )
