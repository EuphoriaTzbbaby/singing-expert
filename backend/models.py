from datetime import datetime, timezone, timedelta

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text

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


class User(Base):
    """用户表（账号密码登录）"""

    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="bcrypt 哈希后的密码")
    is_admin = Column(Boolean, default=False, nullable=False, comment="是否管理员")
    created_at = Column(DateTime(timezone=False), default=_now_cst, nullable=False)

    __table_args__ = (Index("idx_user_username", "username"),)


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
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="所属用户ID（NULL=公共）")

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
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="上传者ID（NULL=公共）")

    __table_args__ = (
        Index("idx_pdf_created_at", "created_at"),
        Index("idx_pdf_oss_key", "oss_key"),
        Index("idx_pdf_group_id", "group_id"),
        Index("idx_pdf_user_id", "user_id"),
    )


class VocabCard(Base):
    """词汇记忆卡片（用户自己填写内容，仅本人可见可操作）"""

    __tablename__ = "vocab_cards"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户ID")
    front = Column(String(500), nullable=False, comment="正面：要记忆的内容（单词/短语/问题）")
    back = Column(String(1000), nullable=False, comment="背面：答案/释义")
    note = Column(String(500), nullable=True, comment="备注（可选，如音标/例句）")
    ai_mnemonic = Column(Text, nullable=True, comment="AI 生成的助记：助记故事/词根词缀/记忆技巧")
    category = Column(String(20), nullable=False, default="单词", comment="分类：单词/短语/句子/其他")
    # 莱特纳盒子：0=新卡；每答对升 1 级，答错回 0 级
    box_level = Column(Integer, nullable=False, default=0, comment="记忆盒等级 0~6（0=新卡）")
    # 下次复习时间；NULL = 新卡（视为今日到期）
    next_review_at = Column(DateTime(timezone=False), nullable=True, comment="下次复习时间")
    last_reviewed_at = Column(DateTime(timezone=False), nullable=True, comment="上次复习时间")
    created_at = Column(DateTime(timezone=False), default=_now_cst, nullable=False)

    __table_args__ = (Index("idx_vocab_user_id", "user_id"),)


class VocabReview(Base):
    """词汇复习记录（每日统计/打卡/正确率用）"""

    __tablename__ = "vocab_reviews"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户ID")
    card_id = Column(BigInteger, ForeignKey("vocab_cards.id", ondelete="CASCADE"), nullable=False, comment="卡片ID")
    known = Column(Boolean, nullable=False, comment="true=认识，false=不认识")
    mode = Column(String(20), nullable=False, default="flash", comment="复习模式：flash(翻卡)/type(拼写)/dictation(听写)")
    reviewed_at = Column(DateTime(timezone=False), default=_now_cst, nullable=False, comment="复习时间")

    __table_args__ = (
        Index("idx_review_user_id", "user_id"),
        Index("idx_review_user_time", "user_id", "reviewed_at"),
    )
