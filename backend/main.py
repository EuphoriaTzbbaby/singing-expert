from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from config import settings
from database import Base, engine, get_db
from models import PdfFile
from schemas import HealthOut, PdfFileOut, SignedUrlOut
from storage import (
    gen_download_url,
    gen_oss_key,
    gen_view_url,
    get_object_stream,
    upload_bytes_to_oss,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) 启动时把本地模型对应的表建好（pdf_files，config 表用户已建好会跳过）
    #    生产请用 Alembic 迁移
    Base.metadata.create_all(bind=engine)

    # 2) 预热：从 config 表读一次 OSS 配置 —— 读不出来启动就直接报错，
    #    避免请求进来时才失败
    from app_config import load_oss_config
    from database import SessionLocal

    db = SessionLocal()
    try:
        cfg = load_oss_config(db)
        print(
            f"[startup] 从 config 表加载 OSS 配置 OK: "
            f"endpoint={cfg.endpoint}, bucket={cfg.bucket_name}"
        )
    finally:
        db.close()

    yield


app = FastAPI(
    title="Singing Expert - PDF 工具",
    version="0.1.0",
    description="PDF 上传 / 在线查看 / 下载（OSS 存储 + MySQL 元数据）",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_pdf(file: UploadFile) -> None:
    """校验上传的是不是 PDF"""
    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="只允许上传 PDF 文件")
    name = (file.filename or "").lower()
    if not name.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="文件扩展名必须为 .pdf")


@app.get("/api/health", response_model=HealthOut)
def health():
    return {"status": "ok"}


@app.post("/api/files/upload", response_model=PdfFileOut)
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传 PDF：服务端转发到 OSS，元数据写 MySQL"""
    _validate_pdf(file)

    content = await file.read()
    if len(content) > settings.max_pdf_size:
        raise HTTPException(status_code=413, detail="文件超过大小上限")

    original_name = file.filename or "untitled.pdf"
    oss_key = gen_oss_key(original_name)

    try:
        upload_bytes_to_oss(content, oss_key)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"上传到 OSS 失败: {e}")

    record = PdfFile(
        original_name=original_name,
        oss_key=oss_key,
        file_size=len(content),
        mime_type="application/pdf",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/files", response_model=list[PdfFileOut])
def list_pdfs(db: Session = Depends(get_db)):
    """列出所有已上传的 PDF（按上传时间倒序）"""
    return db.query(PdfFile).order_by(desc(PdfFile.created_at)).all()


@app.get("/api/files/{file_id}/view-url", response_model=SignedUrlOut)
def get_view_url(file_id: int, db: Session = Depends(get_db)):
    """获取在线查看的 OSS 签名 URL（保留兼容，但 iframe 推荐走 /view 同源代理）"""
    record = db.query(PdfFile).filter(PdfFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"url": gen_view_url(record.oss_key)}


@app.get("/api/files/{file_id}/view")
def stream_pdf_view(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    在线查看：后端把 OSS 的 PDF 字节流代理回来，**同源**返回给前端 iframe。
    这么做主要是绕开当前 OSS bucket cwwdka 的两条限制：
      1) bucket 开启了「默认强制下载」= Content-Disposition: attachment
      2) bucket 不允许通过签名 URL 的 response-content-type 参数覆盖
         （InvalidRequest: Can not override response header on content-type）
    流式读取不会把整份文件加载进内存，100MB PDF 也能稳定处理。
    """
    record = db.query(PdfFile).filter(PdfFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        total_bytes, body_iter = get_object_stream(record.oss_key)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"从 OSS 拉取文件失败: {e}")

    disposition = f"inline; filename*=UTF-8''{quote(record.original_name)}"
    headers = {
        "Content-Disposition": disposition,
        # 显式 no-store 也行；但 Content-Length 给浏览器能更友好显示
    }
    return StreamingResponse(
        body_iter,
        media_type="application/pdf",
        status_code=200,
        headers=headers,
    )


@app.get("/api/files/{file_id}/download-url", response_model=SignedUrlOut)
def get_download_url_route(file_id: int, db: Session = Depends(get_db)):
    """获取下载用的 OSS 签名 URL（attachment，文件名走 RFC 5987 编码）"""
    record = db.query(PdfFile).filter(PdfFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"url": gen_download_url(record.oss_key, record.original_name)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
