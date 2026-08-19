from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from models import AppConfig


@dataclass
class OssConfig:
    endpoint: str
    access_key_id: str
    access_key_secret: str
    bucket_name: str


# 简单进程内缓存，避免每次请求都查库；可通过 invalidate_oss_config() 刷新
_oss_cache: Optional[OssConfig] = None

OSS_KEYS = ("oss.endpoint", "oss.accessKeyId", "oss.accessKeySecret", "oss.bucketName")


def load_oss_config(db: Session) -> OssConfig:
    """从 MySQL 的 config 表读取 OSS 配置，带内存缓存。"""
    global _oss_cache
    if _oss_cache is not None:
        return _oss_cache

    rows = db.query(AppConfig).filter(AppConfig.configKey.in_(OSS_KEYS)).all()
    kv = {r.configKey: r.configValue for r in rows}

    missing = [k for k in OSS_KEYS if not kv.get(k)]
    if missing:
        raise RuntimeError(
            f"MySQL config 表缺少 OSS 配置: {missing}. "
            "请在 config 表里插入 oss.endpoint / oss.accessKeyId / "
            "oss.accessKeySecret / oss.bucketName 四条记录。"
        )

    _oss_cache = OssConfig(
        endpoint=kv["oss.endpoint"].strip(),
        access_key_id=kv["oss.accessKeyId"].strip(),
        access_key_secret=kv["oss.accessKeySecret"].strip(),
        bucket_name=kv["oss.bucketName"].strip(),
    )
    return _oss_cache


def get_oss_config_from_new_session() -> OssConfig:
    """方便独立模块（storage.py）使用：用独立 Session 读取一次 config 表。"""
    from database import SessionLocal

    db = SessionLocal()
    try:
        return load_oss_config(db)
    finally:
        db.close()


def invalidate_oss_config() -> None:
    """清空缓存，下一次读取会重新查库（修改 config 表后调用）。"""
    global _oss_cache
    _oss_cache = None
