from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import NonNegativeInt, PositiveInt
from sqlalchemy import desc, func, or_, text
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from config import settings
from database import Base, engine, get_db
from models import Group, PdfFile, User, VocabCard, VocabReview, _now_cst
from schemas import (
    ChangePasswordIn,
    DeleteSelfIn,
    FileUpdateIn,
    GroupAdminOut,
    GroupCreate,
    GroupOut,
    HealthOut,
    LoginIn,
    PdfFileAdminOut,
    PdfFileOut,
    ProfileOut,
    RegisterIn,
    ResetPasswordIn,
    SetAdminIn,
    SignedUrlOut,
    StatsOut,
    TokenOut,
    UserAdminOut,
    UserOut,
    VocabCreateIn,
    VocabOut,
    VocabPageOut,
    VocabReviewIn,
    VocabStatsOut,
    VocabUpdateIn,
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
    # 1) 启动时把本地模型对应的表建好（users, pdf_files, groups, config）
    Base.metadata.create_all(bind=engine)

    # 1.5) 自动迁移：给已有表加新列（create_all 不会 ALTER 已有表）
    # 注意：表名一律加反引号，groups 是 MySQL 8.0 保留字（窗口函数），
    #       不加反引号会 1064 语法错。
    with engine.connect() as conn:
        # pdf_files 加 group_id
        if not conn.execute(text("SHOW COLUMNS FROM `pdf_files` LIKE 'group_id'")).fetchone():
            conn.execute(text("ALTER TABLE `pdf_files` ADD COLUMN group_id BIGINT NULL, ADD INDEX idx_pdf_group_id (group_id)"))
            print("[migrate] pdf_files +group_id")

        # pdf_files 加 user_id
        if not conn.execute(text("SHOW COLUMNS FROM `pdf_files` LIKE 'user_id'")).fetchone():
            conn.execute(text("ALTER TABLE `pdf_files` ADD COLUMN user_id BIGINT NULL, ADD INDEX idx_pdf_user_id (user_id)"))
            print("[migrate] pdf_files +user_id")

        # groups 加 user_id
        if not conn.execute(text("SHOW COLUMNS FROM `groups` LIKE 'user_id'")).fetchone():
            conn.execute(text("ALTER TABLE `groups` ADD COLUMN user_id BIGINT NULL, ADD INDEX idx_group_user_id (user_id)"))
            print("[migrate] groups +user_id")

        # users 加 is_admin
        if not conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'is_admin'")).fetchone():
            conn.execute(text("ALTER TABLE `users` ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
            print("[migrate] users +is_admin")

        # vocab_cards 加 category / box_level / next_review_at
        if not conn.execute(text("SHOW COLUMNS FROM `vocab_cards` LIKE 'category'")).fetchone():
            conn.execute(text("ALTER TABLE `vocab_cards` ADD COLUMN category VARCHAR(20) NOT NULL DEFAULT '单词'"))
            print("[migrate] vocab_cards +category")
        if not conn.execute(text("SHOW COLUMNS FROM `vocab_cards` LIKE 'box_level'")).fetchone():
            conn.execute(text("ALTER TABLE `vocab_cards` ADD COLUMN box_level INT NOT NULL DEFAULT 0"))
            print("[migrate] vocab_cards +box_level")
        if not conn.execute(text("SHOW COLUMNS FROM `vocab_cards` LIKE 'next_review_at'")).fetchone():
            conn.execute(text("ALTER TABLE `vocab_cards` ADD COLUMN next_review_at DATETIME NULL"))
            print("[migrate] vocab_cards +next_review_at")
        # vocab_cards 加 last_reviewed_at / ai_mnemonic
        if not conn.execute(text("SHOW COLUMNS FROM `vocab_cards` LIKE 'last_reviewed_at'")).fetchone():
            conn.execute(text("ALTER TABLE `vocab_cards` ADD COLUMN last_reviewed_at DATETIME NULL"))
            print("[migrate] vocab_cards +last_reviewed_at")
        if not conn.execute(text("SHOW COLUMNS FROM `vocab_cards` LIKE 'ai_mnemonic'")).fetchone():
            conn.execute(text("ALTER TABLE `vocab_cards` ADD COLUMN ai_mnemonic TEXT NULL"))
            print("[migrate] vocab_cards +ai_mnemonic")

        conn.commit()

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


@app.get("/health")
def health_check():
    return {"status": "ok"}


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


# ==================== 认证 ====================


@app.post("/api/auth/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    """注册新用户"""
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.username)
    return TokenOut(access_token=token, username=user.username)


@app.post("/api/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    """登录"""
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(user.id, user.username)
    return TokenOut(access_token=token, username=user.username)


@app.get("/api/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user


@app.get("/api/auth/profile", response_model=ProfileOut)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户个人资料（含文件数 + 存储大小）"""
    file_count = (
        db.query(func.count(PdfFile.id)).filter(PdfFile.user_id == current_user.id).scalar() or 0
    )
    storage = (
        db.query(func.coalesce(func.sum(PdfFile.file_size), 0))
        .filter(PdfFile.user_id == current_user.id)
        .scalar()
        or 0
    )
    return ProfileOut(
        id=current_user.id,
        username=current_user.username,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        file_count=file_count,
        storage_bytes=storage,
    )


@app.post("/api/auth/change-password")
def change_password(
    body: ChangePasswordIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户自己修改密码：必须验证旧密码"""
    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")
    if body.old_password == body.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")
    current_user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}


@app.post("/api/auth/delete-self")
def delete_self(
    body: DeleteSelfIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户注销账号：必须输入当前密码确认。
    流程：验证密码 → 循环删该用户所有 OSS 对象 → db.delete(user)（CASCADE 带走 PdfFile/Group 行）。
    OSS 删除失败不阻塞，返回 failed_oss_keys 供运维跟进。
    """
    if not verify_password(body.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="密码错误，注销失败")

    pdfs = db.query(PdfFile).filter(PdfFile.user_id == current_user.id).all()
    failed_oss_keys = []
    for p in pdfs:
        try:
            delete_from_oss(p.oss_key)
        except Exception:  # noqa: BLE001
            failed_oss_keys.append(p.oss_key)

    db.delete(current_user)
    db.commit()
    return {"ok": True, "id": current_user.id, "failed_oss_keys": failed_oss_keys}


# ==================== 分组管理 ====================


@app.get("/api/groups", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """列出当前用户的分组（含公共分组），带每个分组的文件数"""
    groups = (
        db.query(Group)
        .filter(or_(Group.user_id == current_user.id, Group.user_id.is_(None)))
        .order_by(desc(Group.created_at))
        .all()
    )
    result = []
    for g in groups:
        count = (
            db.query(func.count(PdfFile.id))
            .filter(PdfFile.group_id == g.id)
            .filter(_pdf_visible_filter(current_user))
            .scalar()
            or 0
        )
        result.append(GroupOut(id=g.id, name=g.name, created_at=g.created_at, file_count=count))
    return result


@app.post("/api/groups", response_model=GroupOut, status_code=201)
def create_group(body: GroupCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """创建分组（绑定当前用户）"""
    existing = db.query(Group).filter(Group.name == body.name, Group.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="分组名已存在")
    record = Group(name=body.name, user_id=current_user.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return GroupOut(id=record.id, name=record.name, created_at=record.created_at, file_count=0)


@app.delete("/api/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """删除分组（只能删自己的，公共分组只有管理员能删）"""
    record = db.query(Group).filter(Group.id == group_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="分组不存在")
    # 公共分组（user_id=NULL）只有管理员能删；私有分组只有主人能删
    if record.user_id is None and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权删除公共分组")
    if record.user_id is not None and record.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权删除他人的分组")
    name = record.name
    db.delete(record)
    db.commit()
    return {"ok": True, "id": group_id, "name": name}


# ==================== PDF 文件管理 ====================


def _pdf_visible_filter(current_user: User):
    """返回 PDF 可见性过滤条件：
    - 管理员：无过滤（看所有）
    - 普通用户：自己的 + 管理员上传的 + 公共的（NULL）
    """
    if current_user.is_admin:
        return text("1=1")
    admin_ids = text(f"(SELECT id FROM users WHERE is_admin = 1)")
    return or_(
        PdfFile.user_id == current_user.id,
        PdfFile.user_id.in_(admin_ids),
        PdfFile.user_id.is_(None),
    )


@app.post("/api/files/upload", response_model=PdfFileOut)
async def upload_pdf(
    file: UploadFile = File(...),
    group_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    # 如果指定了分组，校验分组存在且属于当前用户
    if group_id is not None:
        grp = db.query(Group).filter(Group.id == group_id).first()
        if not grp:
            raise HTTPException(status_code=400, detail="指定的分组不存在")
        if grp.user_id is not None and grp.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="无权使用他人的分组")

    record = PdfFile(
        original_name=original_name,
        oss_key=oss_key,
        file_size=len(content),
        mime_type="application/pdf",
        group_id=group_id,
        user_id=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/files", response_model=list[PdfFileOut])
def list_pdfs(
    group_id: int | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出当前用户可见的 PDF 文件（按上传时间倒序）。
    group_id 过滤：不传=全部，0=未分组，>0=指定分组
    keyword: 按文件名模糊搜索（不区分大小写）
    """
    q = db.query(PdfFile).filter(_pdf_visible_filter(current_user))
    if group_id is not None:
        if group_id == 0:
            q = q.filter(PdfFile.group_id.is_(None))
        else:
            q = q.filter(PdfFile.group_id == group_id)
    if keyword:
        q = q.filter(PdfFile.original_name.ilike(f"%{keyword}%"))
    return q.order_by(desc(PdfFile.created_at)).all()


def _get_visible_pdf(file_id: int, current_user: User, db: Session) -> PdfFile:
    """获取当前用户可见的 PDF，不可见则 404"""
    record = db.query(PdfFile).filter(PdfFile.id == file_id, _pdf_visible_filter(current_user)).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    return record


def _check_owner_or_admin(record: PdfFile, current_user: User):
    """检查当前用户是否是文件主人或管理员"""
    if record.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权操作他人的文件")


@app.get("/api/files/{file_id}/view-url", response_model=SignedUrlOut)
def get_view_url(file_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取在线查看的 OSS 签名 URL"""
    record = _get_visible_pdf(file_id, current_user, db)
    return {"url": gen_view_url(record.oss_key)}


@app.get("/api/files/{file_id}/view")
def stream_pdf_view(file_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """在线查看：后端同源代理 OSS PDF 字节流，强制 inline"""
    record = _get_visible_pdf(file_id, current_user, db)

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
def get_download_url_route(file_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取下载用的 OSS 签名 URL（attachment）"""
    record = _get_visible_pdf(file_id, current_user, db)
    return {"url": gen_download_url(record.oss_key, record.original_name)}


@app.patch("/api/files/{file_id}", response_model=PdfFileOut)
def update_file(file_id: int, body: FileUpdateIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """更新文件（移动分组 + 重命名）"""
    record = _get_visible_pdf(file_id, current_user, db)
    _check_owner_or_admin(record, current_user)

    # 移动分组
    if body.group_id is not None:
        grp = db.query(Group).filter(Group.id == body.group_id).first()
        if not grp:
            raise HTTPException(status_code=400, detail="目标分组不存在")
        if grp.user_id is not None and grp.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="无权移动到他人的分组")
        record.group_id = body.group_id

    # 重命名
    if body.original_name is not None:
        name = body.original_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        record.original_name = name

    db.commit()
    db.refresh(record)
    return record


@app.delete("/api/files/{file_id}")
def delete_pdf(file_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """删除 PDF = 先删 OSS + 再删 MySQL"""
    record = _get_visible_pdf(file_id, current_user, db)
    _check_owner_or_admin(record, current_user)

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


# ==================== 词汇记忆 ====================


@app.get("/api/vocab", response_model=VocabPageOut)
def list_vocab(
    page: PositiveInt = 1,
    page_size: PositiveInt = 10,
    keyword: str = "",
    category: str = "",
    only_due: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出当前用户的词汇卡片（分页，按创建时间倒序，支持搜索/分类/仅到期过滤）"""
    if page_size > 100:
        page_size = 100
    now = _now_cst()
    q = db.query(VocabCard).filter(VocabCard.user_id == current_user.id)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.filter(
            or_(
                VocabCard.front.like(kw),
                VocabCard.back.like(kw),
                func.coalesce(VocabCard.note, "").like(kw),
            )
        )
    if category:
        q = q.filter(VocabCard.category == category)
    if only_due:
        q = q.filter(or_(VocabCard.next_review_at.is_(None), VocabCard.next_review_at <= now))
    total = q.count()
    items = (
        q.order_by(desc(VocabCard.created_at))
        .limit(page_size)
        .offset((page - 1) * page_size)
        .all()
    )
    return VocabPageOut(total=total, page=page, page_size=page_size, items=items)


@app.get("/api/vocab/due", response_model=list[VocabOut])
def list_vocab_due(
    category: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有到期/新卡片（不分页，供复习模式一次性拉取）"""
    now = _now_cst()
    q = db.query(VocabCard).filter(
        VocabCard.user_id == current_user.id,
        or_(VocabCard.next_review_at.is_(None), VocabCard.next_review_at <= now),
    )
    if category:
        q = q.filter(VocabCard.category == category)
    return q.order_by(desc(VocabCard.created_at)).all()


@app.post("/api/vocab", response_model=VocabOut, status_code=201)
def create_vocab(
    body: VocabCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新增词汇卡片。若正面已存在且 force_create=False，返回 409 附带已有卡片信息。"""
    front = body.front.strip()
    back = body.back.strip()
    if not front:
        raise HTTPException(status_code=400, detail="正面内容不能为空")
    if not back:
        raise HTTPException(status_code=400, detail="背面内容不能为空")

    if not body.force_create:
        existing = (
            db.query(VocabCard)
            .filter(
                VocabCard.user_id == current_user.id,
                VocabCard.front == front,
            )
            .order_by(desc(VocabCard.created_at))
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "正面内容已存在相同卡片",
                    "existing": {
                        "id": existing.id,
                        "front": existing.front,
                        "back": existing.back,
                        "note": existing.note,
                        "category": existing.category,
                        "box_level": existing.box_level,
                    },
                },
            )

    record = VocabCard(
        user_id=current_user.id,
        front=front,
        back=back,
        note=(body.note or "").strip() or None,
        category=body.category,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _get_own_vocab(card_id: int, current_user: User, db: Session) -> VocabCard:
    """获取当前用户自己的卡片，不存在/不是自己的则 404"""
    record = (
        db.query(VocabCard)
        .filter(VocabCard.id == card_id, VocabCard.user_id == current_user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return record


@app.patch("/api/vocab/{card_id}", response_model=VocabOut)
def update_vocab(
    card_id: int,
    body: VocabUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新词汇卡片（只能改自己的）"""
    record = _get_own_vocab(card_id, current_user, db)
    if body.front is not None:
        front = body.front.strip()
        if not front:
            raise HTTPException(status_code=400, detail="正面内容不能为空")
        record.front = front
    if body.back is not None:
        back = body.back.strip()
        if not back:
            raise HTTPException(status_code=400, detail="背面内容不能为空")
        record.back = back
    if body.note is not None:
        record.note = body.note.strip() or None
    if body.category is not None:
        record.category = body.category
    db.commit()
    db.refresh(record)
    return record


# 莱特纳盒子间隔（天）：答对升 1 级，按新等级取间隔
REVIEW_INTERVALS_DAYS = {1: 1, 2: 2, 3: 4, 4: 7, 5: 15, 6: 30}
MAX_BOX_LEVEL = 6


@app.post("/api/vocab/{card_id}/review", response_model=VocabOut)
def review_vocab(
    card_id: int,
    body: VocabReviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """背诵评分：认识→升盒（间隔拉长），不认识→回 0 级（明天再见），并写入复习日志。"""
    record = _get_own_vocab(card_id, current_user, db)
    now = _now_cst()
    if body.known:
        new_level = min(record.box_level + 1, MAX_BOX_LEVEL)
        record.box_level = new_level
        record.next_review_at = now + timedelta(days=REVIEW_INTERVALS_DAYS[new_level])
    else:
        record.box_level = 0
        record.next_review_at = now + timedelta(days=1)
    record.last_reviewed_at = now

    # 写入复习日志
    mode = body.mode if body.mode in ("flash", "type", "dictation") else "flash"
    db.add(VocabReview(user_id=current_user.id, card_id=card_id, known=bool(body.known), mode=mode, reviewed_at=now))

    db.commit()
    db.refresh(record)
    return record


def _beijing_date(d: datetime) -> str:
    """把带时区/不带时区的时间转成北京时间 YYYY-MM-DD。"""
    from datetime import timezone as tz
    import zoneinfo  # Python 3.9+
    bj = zoneinfo.ZoneInfo("Asia/Shanghai")
    if d.tzinfo is None:
        d = d.replace(tzinfo=tz.utc)
    bj_time = d.astimezone(bj)
    return bj_time.strftime("%Y-%m-%d")


@app.get("/api/vocab/stats", response_model=VocabStatsOut)
def get_vocab_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学习统计仪表盘：今日待复习/已掌握/连续打卡/7天复习曲线/正确率。"""
    now = _now_cst()
    uid = current_user.id

    # 总卡片 / 已掌握（box_level >= 4 → 至少 7 天记得）
    total_q = db.query(VocabCard).filter(VocabCard.user_id == uid)
    total_cards = total_q.count()
    mastered = total_q.filter(VocabCard.box_level >= 4).count()

    # 今日待复习
    today_due = total_q.filter(
        or_(VocabCard.next_review_at.is_(None), VocabCard.next_review_at <= now)
    ).count()

    # 近 7 天 北京时间日期数组（含今天，从 6 天前 → 今天）
    import zoneinfo
    from datetime import timezone as tz
    bj = zoneinfo.ZoneInfo("Asia/Shanghai")
    now_bj = now.astimezone(bj) if now.tzinfo else now.replace(tzinfo=tz.utc).astimezone(bj)
    days = []
    daily_rows = []
    for i in range(6, -1, -1):
        day_bj = now_bj.date() - timedelta(days=i)
        days.append(day_bj.strftime("%Y-%m-%d"))
        # reviewed_at（CST，无时区，等价 UTC+8）落在 [day 00:00, day+1 00:00)
        day_start = datetime.combine(day_bj, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        agg = (
            db.query(
                func.count(VocabReview.id).label("n"),
                func.sum(func.if_(VocabReview.known, 1, 0)).label("c"),
            )
            .filter(
                VocabReview.user_id == uid,
                VocabReview.reviewed_at >= day_start,
                VocabReview.reviewed_at < day_end,
            )
            .first()
        )
        reviewed = int(agg.n or 0)
        correct = int(agg.c or 0)
        daily_rows.append({"date": day_bj.strftime("%Y-%m-%d"), "reviewed": reviewed, "correct": correct})

    today_reviewed = daily_rows[-1]["reviewed"]
    today_correct = daily_rows[-1]["correct"]
    # 近 7 日正确率
    weekly_reviewed = sum(d["reviewed"] for d in daily_rows)
    weekly_correct = sum(d["correct"] for d in daily_rows)
    weekly_accuracy = (weekly_correct / weekly_reviewed) if weekly_reviewed else 0.0

    # 连续打卡天数：从今天往前算，每天 reviewed>0 则 +1，遇 0 则中断；今天没复习则看昨天开始
    streak = 0
    # 从今天开始倒推
    for d in reversed(range(7)):
        r = daily_rows[d]["reviewed"]
        if r > 0:
            streak += 1
        else:
            # 如果是今天为 0，允许从昨天开始算；否则直接断
            if d == 6:
                continue
            break
    # 如果连续超过 7 天，继续往更久扫描
    if streak >= 7 or (streak == 0 and False):
        # 往更早再扫 60 天上限（避免过重）
        probe_day = now_bj.date() - timedelta(days=7 if daily_rows[-1]["reviewed"] > 0 else 7)
        # 仅当 7 天满才继续
        if streak >= 7:
            for _ in range(60):
                probe_day = probe_day - timedelta(days=1)
                day_start = datetime.combine(probe_day, datetime.min.time())
                day_end = day_start + timedelta(days=1)
                cnt = (
                    db.query(func.count(VocabReview.id))
                    .filter(
                        VocabReview.user_id == uid,
                        VocabReview.reviewed_at >= day_start,
                        VocabReview.reviewed_at < day_end,
                    )
                    .scalar()
                    or 0
                )
                if cnt > 0:
                    streak += 1
                else:
                    break

    return VocabStatsOut(
        today_due=today_due,
        today_reviewed=today_reviewed,
        today_correct=today_correct,
        mastered=mastered,
        total_cards=total_cards,
        streak_days=streak,
        daily=daily_rows,
        weekly_accuracy=round(weekly_accuracy, 4),
    )


@app.post("/api/vocab/{card_id}/ai-mnemonic", response_model=VocabOut)
def ai_mnemonic(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """调大模型生成：助记小故事 + 词根词缀拆解 + 记忆技巧。生成后写入卡片 ai_mnemonic。"""
    import json

    card = _get_own_vocab(card_id, current_user, db)

    # 1. 找模型配置（沿用项目里现有方式：优先从 config 表取，兼容环境变量）
    from app_config import get_config_value  # 复用 PDF 里的读 config 表工具

    api_url = None
    api_key = None
    model = None
    try:
        api_url = (get_config_value("ai_api_url") or "").strip() or None
        api_key = (get_config_value("ai_api_key") or "").strip() or None
        model = (get_config_value("ai_model") or "").strip() or None
    except Exception:
        pass
    if not api_url or not api_key:
        # 回退：允许从环境变量（.env）里配
        import os
        api_url = api_url or os.getenv("AI_API_URL")
        api_key = api_key or os.getenv("AI_API_KEY")
        model = model or os.getenv("AI_MODEL") or "deepseek-chat"
    if not api_url or not api_key:
        raise HTTPException(
            status_code=503,
            detail="未配置 AI 模型，请先在数据库 config 表写入 ai_api_url / ai_api_key，或在 .env 配置。（推荐 DeepSeek：api_url=https://api.deepseek.com/v1/chat/completions）",
        )

    # 2. 组装提示词
    card_cat = card.category or "其他"
    system_prompt = (
        "你是一个精通英语记忆法的辅导老师。用户给你一张卡片（正面/背面/分类/备注），"
        "请你输出结构化的助记内容，包含 3 个必选模块，用 Markdown 分 3 段：\n"
        "1. **词根词缀拆解**（若不是单词类，就分析短语结构或句子语法成分）\n"
        "2. **助记小故事**（生动联想，2~4 句，方便记忆）\n"
        "3. **记忆技巧**（1~3 条具体可操作的方法）\n"
        "最后可选：若有和其它常见词的关联（同音、近义、反义、同根），再追加 1 段「4. 相关联想」。\n"
        "回答必须为中文，简洁不啰嗦，只输出 Markdown 正文。"
    )
    user_prompt = (
        f"卡片分类：{card_cat}\n"
        f"正面：{card.front}\n"
        f"背面（释义）：{card.back}\n"
        f"备注：{card.note or '(无)'}\n"
    )

    # 3. 调模型（兼容 OpenAI 协议 / DeepSeek 协议）
    import urllib.request
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "stream": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 接口调用失败: {e}")

    # 兼容：choices[0].message.content / choices[0].delta.content
    content = ""
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        try:
            content = data["choices"][0]["delta"]["content"]
        except Exception:
            raise HTTPException(status_code=502, detail="AI 返回格式无法解析")
    content = (content or "").strip()
    if not content:
        raise HTTPException(status_code=502, detail="AI 返回空内容")

    card.ai_mnemonic = content
    db.commit()
    db.refresh(card)
    return card


@app.delete("/api/vocab/{card_id}")
def delete_vocab(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除词汇卡片（只能删自己的）"""
    record = _get_own_vocab(card_id, current_user, db)
    db.delete(record)
    db.commit()
    return {"ok": True, "id": card_id}


# ==================== 管理端 ====================


@app.get("/api/admin/stats", response_model=StatsOut)
def admin_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """系统总览统计：用户数、文件数、存储大小、分组数、公共文件数、最近 10 条上传"""
    user_count = db.query(func.count(User.id)).scalar() or 0
    file_count = db.query(func.count(PdfFile.id)).scalar() or 0
    total_storage = db.query(func.coalesce(func.sum(PdfFile.file_size), 0)).scalar() or 0
    group_count = db.query(func.count(Group.id)).scalar() or 0
    public_file_count = (
        db.query(func.count(PdfFile.id)).filter(PdfFile.user_id.is_(None)).scalar() or 0
    )

    recent_q = (
        db.query(PdfFile, User.username.label("owner_username"), Group.name.label("group_name"))
        .outerjoin(User, User.id == PdfFile.user_id)
        .outerjoin(Group, Group.id == PdfFile.group_id)
        .order_by(desc(PdfFile.created_at))
        .limit(10)
    )
    recent = [
        PdfFileAdminOut(
            id=p.id,
            original_name=p.original_name,
            file_size=p.file_size,
            mime_type=p.mime_type,
            created_at=p.created_at,
            group_id=p.group_id,
            group_name=gname,
            user_id=p.user_id,
            owner_username=owner,
        )
        for p, owner, gname in recent_q.all()
    ]
    return StatsOut(
        user_count=user_count,
        file_count=file_count,
        total_storage_bytes=total_storage,
        group_count=group_count,
        public_file_count=public_file_count,
        recent_uploads=recent,
    )


@app.get("/api/admin/users", response_model=list[UserAdminOut])
def admin_list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """列出全部用户，带文件数 + 存储大小"""
    rows = (
        db.query(
            User,
            func.count(PdfFile.id).label("file_count"),
            func.coalesce(func.sum(PdfFile.file_size), 0).label("storage_bytes"),
        )
        .outerjoin(PdfFile, PdfFile.user_id == User.id)
        .group_by(User.id)
        .order_by(desc(User.created_at))
        .all()
    )
    return [
        UserAdminOut(
            id=u.id,
            username=u.username,
            is_admin=u.is_admin,
            created_at=u.created_at,
            file_count=fc or 0,
            storage_bytes=sb or 0,
        )
        for u, fc, sb in rows
    ]


@app.patch("/api/admin/users/{user_id}/admin")
def admin_set_admin(
    user_id: int,
    body: SetAdminIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """修改用户管理员标志。安全约束：不能改自己（防锁死）"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的管理员状态")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_admin = body.is_admin
    db.commit()
    return {"ok": True, "id": user_id, "is_admin": user.is_admin}


@app.post("/api/admin/users/{user_id}/reset-password")
def admin_reset_password(
    user_id: int,
    body: ResetPasswordIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """管理员重置用户密码。安全约束：不能重置自己（用户改密应走另一套流程）"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能重置自己的密码")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "id": user_id}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """删除用户。安全约束：不能删自己。
    流程：先循环删该用户所有 OSS 对象，再 db.delete(user)（CASCADE 带走 PdfFile/Group 行）。
    OSS 删除失败不阻塞，返回 failed_oss_keys 供运维跟进。
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    pdfs = db.query(PdfFile).filter(PdfFile.user_id == user_id).all()
    failed_oss_keys = []
    for p in pdfs:
        try:
            delete_from_oss(p.oss_key)
        except Exception:  # noqa: BLE001
            failed_oss_keys.append(p.oss_key)

    db.delete(user)
    db.commit()
    return {"ok": True, "id": user_id, "failed_oss_keys": failed_oss_keys}


@app.get("/api/admin/files", response_model=list[PdfFileAdminOut])
def admin_list_files(
    user_id: int | None = None,
    group_id: int | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """列出所有文件（带 owner username + group name）"""
    q = (
        db.query(
            PdfFile,
            User.username.label("owner_username"),
            Group.name.label("group_name"),
        )
        .outerjoin(User, User.id == PdfFile.user_id)
        .outerjoin(Group, Group.id == PdfFile.group_id)
    )
    if user_id is not None:
        q = q.filter(PdfFile.user_id == user_id)
    if group_id is not None:
        if group_id == 0:
            q = q.filter(PdfFile.group_id.is_(None))
        else:
            q = q.filter(PdfFile.group_id == group_id)
    if keyword:
        q = q.filter(PdfFile.original_name.ilike(f"%{keyword}%"))
    q = q.order_by(desc(PdfFile.created_at))
    return [
        PdfFileAdminOut(
            id=p.id,
            original_name=p.original_name,
            file_size=p.file_size,
            mime_type=p.mime_type,
            created_at=p.created_at,
            group_id=p.group_id,
            group_name=gname,
            user_id=p.user_id,
            owner_username=owner,
        )
        for p, owner, gname in q.all()
    ]


@app.get("/api/admin/groups", response_model=list[GroupAdminOut])
def admin_list_groups(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """列出全部分组（带 owner username + 文件数）"""
    rows = (
        db.query(
            Group,
            User.username.label("owner_username"),
            func.count(PdfFile.id).label("file_count"),
        )
        .outerjoin(User, User.id == Group.user_id)
        .outerjoin(PdfFile, PdfFile.group_id == Group.id)
        .group_by(Group.id)
        .order_by(desc(Group.created_at))
        .all()
    )
    return [
        GroupAdminOut(
            id=g.id,
            name=g.name,
            created_at=g.created_at,
            user_id=g.user_id,
            owner_username=owner,
            file_count=fc or 0,
        )
        for g, owner, fc in rows
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
