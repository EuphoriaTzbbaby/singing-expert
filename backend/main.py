from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from config import settings
from database import Base, engine, get_db
from models import Group, PdfFile
from schemas import (
    FileMoveIn,
    GroupCreate,
    GroupOut,
    HealthOut,
    PdfFileOut,
    SignedUrlOut,
)
from storage import (
    delete_from_oss,
    gen_download_url,
    gen_oss_key,
    gen_view_url,
    get_object_stream,
    upload_bytes_to_oss,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) 启动时把本地模型对应的表建好（pdf_files, groups, config）
    Base.metadata.create_all(bind=engine)

    # 1.5) 自动迁移：给已有的 pdf_files 表加 group_id 列（create_all 不会 ALTER 已有表）
    with engine.connect() as conn:
        result = conn.execute(text("SHOW COLUMNS FROM pdf_files LIKE 'group_id'"))
        if not result.fetchone():
            conn.execute(
                text(
                    "ALTER TABLE pdf_files ADD COLUMN group_id BIGINT NULL, "
                    "ADD INDEX idx_pdf_group_id (group_id)"
                )
            )
            conn.commit()
            print("[migrate] pdf_files 表已加 group_id 列")

    # 2) 预热：从 config 表读一次 OSS 配置
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
    version="0.2.0",
    description="PDF 上传 / 在线查看 / 下载 / 分组管理（OSS 存储 + MySQL 元数据）",
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


# ==================== 健康检查 ====================


@app.get("/api/health", response_model=HealthOut)
def health():
    return {"status": "ok"}


# ==================== 分组管理 ====================


@app.get("/api/groups", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db)):
    """列出所有分组，带每个分组的文件数"""
    groups = db.query(Group).order_by(desc(Group.created_at)).all()
    result = []
    for g in groups:
        count = db.query(func.count(PdfFile.id)).filter(PdfFile.group_id == g.id).scalar() or 0
        result.append(GroupOut(id=g.id, name=g.name, created_at=g.created_at, file_count=count))
    return result


@app.post("/api/groups", response_model=GroupOut, status_code=201)
def create_group(body: GroupCreate, db: Session = Depends(get_db)):
    """创建分组"""
    existing = db.query(Group).filter(Group.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="分组名已存在")
    record = Group(name=body.name)
    db.add(record)
    db.commit()
    db.refresh(record)
    return GroupOut(id=record.id, name=record.name, created_at=record.created_at, file_count=0)


@app.delete("/api/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    """删除分组（文件不会被删，group_id 被置 NULL = 移到未分组）"""
    record = db.query(Group).filter(Group.id == group_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="分组不存在")
    name = record.name
    db.delete(record)
    db.commit()
    return {"ok": True, "id": group_id, "name": name}


# ==================== PDF 文件管理 ====================


@app.post("/api/files/upload", response_model=PdfFileOut)
async def upload_pdf(
    file: UploadFile = File(...),
    group_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """上传 PDF：服务端转发到 OSS，元数据写 MySQL（可选分组）"""
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

    # 如果指定了分组，校验分组存在
    if group_id is not None:
        grp = db.query(Group).filter(Group.id == group_id).first()
        if not grp:
            raise HTTPException(status_code=400, detail="指定的分组不存在")

    record = PdfFile(
        original_name=original_name,
        oss_key=oss_key,
        file_size=len(content),
        mime_type="application/pdf",
        group_id=group_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/files", response_model=list[PdfFileOut])
def list_pdfs(group_id: int | None = None, db: Session = Depends(get_db)):
    """列出 PDF 文件（按上传时间倒序）。group_id 过滤：不传=全部，0=未分组，>0=指定分组"""
    q = db.query(PdfFile)
    if group_id is not None:
        if group_id == 0:
            q = q.filter(PdfFile.group_id.is_(None))
        else:
            q = q.filter(PdfFile.group_id == group_id)
    return q.order_by(desc(PdfFile.created_at)).all()


@app.get("/api/files/{file_id}/view-url", response_model=SignedUrlOut)
def get_view_url(file_id: int, db: Session = Depends(get_db)):
    """获取在线查看的 OSS 签名 URL"""
    record = db.query(PdfFile).filter(PdfFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"url": gen_view_url(record.oss_key)}


@app.get("/api/files/{file_id}/view")
def stream_pdf_view(file_id: int, db: Session = Depends(get_db)):
    """在线查看：后端同源代理 OSS PDF 字节流，强制 inline"""
    record = db.query(PdfFile).filter(PdfFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        total_bytes, body_iter = get_object_stream(record.oss_key)  # noqa: F841
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"从 OSS 拉取文件失败: {e}")

    disposition = f"inline; filename*=UTF-8''{quote(record.original_name)}"
    return StreamingResponse(
        body_iter,
        media_type="application/pdf",
        status_code=200,
        headers={"Content-Disposition": disposition},
    )


@app.get("/api/files/{file_id}/download-url", response_model=SignedUrlOut)
def get_download_url_route(file_id: int, db: Session = Depends(get_db)):
    """获取下载用的 OSS 签名 URL（attachment）"""
    record = db.query(PdfFile).filter(PdfFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"url": gen_download_url(record.oss_key, record.original_name)}


@app.patch("/api/files/{file_id}", response_model=PdfFileOut)
def move_file(file_id: int, body: FileMoveIn, db: Session = Depends(get_db)):
    """移动文件到分组（group_id=null = 移到未分组）"""
    record = db.query(PdfFile).filter(PdfFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    if body.group_id is not None:
        grp = db.query(Group).filter(Group.id == body.group_id).first()
        if not grp:
            raise HTTPException(status_code=400, detail="目标分组不存在")
    record.group_id = body.group_id
    db.commit()
    db.refresh(record)
    return record


@app.delete("/api/files/{file_id}")
def delete_pdf(file_id: int, db: Session = Depends(get_db)):
    """删除 PDF = 先删 OSS + 再删 MySQL"""
    record = db.query(PdfFile).filter(PdfFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")

    oss_key = record.oss_key
    original_name = record.original_name

    try:
        delete_from_oss(oss_key)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"OSS 对象删除失败: {e}")

    try:
        db.delete(record)
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库记录删除失败: {e}")

    return {"ok": True, "id": file_id, "original_name": original_name, "deleted_oss_key": oss_key}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
