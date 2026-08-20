from __future__ import annotations

from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
from models import Group, PdfFile, User
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
