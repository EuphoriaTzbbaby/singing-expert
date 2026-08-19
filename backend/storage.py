"""阿里云 OSS 存储封装：上传 + 生成签名 URL（在线查看 / 下载）

OSS 凭证从 MySQL 的 `config` 表读取（key=oss.endpoint / oss.accessKeyId /
oss.accessKeySecret / oss.bucketName），而不是从环境变量拿。
"""

from datetime import datetime
from typing import Optional
from urllib.parse import quote
from uuid import uuid4

import oss2

from app_config import OssConfig, get_oss_config_from_new_session, invalidate_oss_config

_bucket: Optional[oss2.Bucket] = None


def _get_bucket() -> oss2.Bucket:
    """惰性初始化 OSS Bucket 客户端（单例）；凭证变更时调用 reset_oss() 即可重建。"""
    global _bucket
    if _bucket is None:
        cfg: OssConfig = get_oss_config_from_new_session()
        auth = oss2.Auth(cfg.access_key_id, cfg.access_key_secret)
        _bucket = oss2.Bucket(auth, f"https://{cfg.endpoint}", cfg.bucket_name)
    return _bucket


def reset_oss() -> None:
    """清空 bucket 客户端与 app_config 缓存（修改 config 表后调用）。"""
    global _bucket
    _bucket = None
    invalidate_oss_config()


def gen_oss_key(original_name: str) -> str:
    """根据原始文件名生成 OSS 中的唯一对象 key，按年月分目录"""
    now = datetime.utcnow()
    ext = ".pdf"
    if "." in original_name:
        ext = "." + original_name.rsplit(".", 1)[-1].lower()
    return f"pdfs/{now.strftime('%Y/%m')}/{uuid4().hex}{ext}"


def upload_bytes_to_oss(content: bytes, oss_key: str) -> None:
    """把 PDF 字节内容上传到 OSS（同时强制 Content-Type 为 application/pdf）"""
    bucket = _get_bucket()
    bucket.put_object(oss_key, content, headers={"Content-Type": "application/pdf"})


def delete_from_oss(oss_key: str) -> None:
    """从 OSS 删除对象"""
    _get_bucket().delete_object(oss_key)


def gen_view_url(oss_key: str, expires: int = 3600) -> str:
    """生成在线查看用的签名 URL（inline 显示，浏览器内嵌渲染）"""
    return _get_bucket().sign_url("GET", oss_key, expires)


def gen_download_url(oss_key: str, filename: str, expires: int = 3600) -> str:
    """生成下载用的签名 URL（强制 attachment，并用 RFC 5987 编码中文文件名）"""
    encoded = quote(filename)
    params = {
        "response-content-disposition": f"attachment; filename*=UTF-8''{encoded}",
        "response-content-type": "application/pdf",
    }
    return _get_bucket().sign_url("GET", oss_key, expires, params=params)
