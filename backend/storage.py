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


def get_object_stream(oss_key: str):
    """
    从 OSS 下载对象并返回一个「(总字节数, 按 chunk 迭代 body)」二元组，
    用于后端代理流式返回给前端（绕开 OSS bucket 级的 force-download / response
    header override 策略）。
    """
    bucket = _get_bucket()
    result = bucket.get_object(oss_key)
    content_length = int(result.headers.get("Content-Length", 0))

    def _iter(chunk_size: int = 64 * 1024):
        with result as r:
            while True:
                buf = r.read(chunk_size)
                if not buf:
                    break
                yield buf

    return content_length, _iter()


def gen_view_url(oss_key: str, expires: int = 3600) -> str:
    """生成在线查看用的签名 URL。
    显式加上 response-content-disposition=inline 覆盖桶级的「默认强制下载」配置，
    否则浏览器/OSS 会返回 attachment，iframe 里不会内嵌 PDF 阅读器而是直接下载。

    注意：cwwdka 这个 bucket 不允许在签名 URL 里 override response-content-type
    （会报 OSS InvalidRequest: Can not override response header on content-type），
    所以这里只传 disposition；Content-Type 由对象本身的元数据保证（上传时已设为
    application/pdf）。
    """
    params = {
        "response-content-disposition": "inline",
    }
    return _get_bucket().sign_url("GET", oss_key, expires, params=params)


def gen_download_url(oss_key: str, filename: str, expires: int = 3600) -> str:
    """生成下载用的签名 URL（强制 attachment，并用 RFC 5987 编码中文文件名）。
    同上，不传 response-content-type，避免 bucket 拒绝 override。
    """
    encoded = quote(filename)
    params = {
        "response-content-disposition": f"attachment; filename*=UTF-8''{encoded}",
    }
    return _get_bucket().sign_url("GET", oss_key, expires, params=params)
