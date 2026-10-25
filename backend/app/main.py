import hashlib
import hmac
import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import PurePath
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, engine, get_db
from app.models import Folder, SessionToken, StoredFile, User, utcnow
from app.storage import storage

settings = get_settings()
password_hasher = PasswordHasher()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
        with Session(bind=engine) as db:
            email = settings.bootstrap_admin_email.lower().strip()
            if db.scalar(select(User).where(User.email == email)) is None:
                db.add(
                    User(
                        name="Administrator",
                        email=email,
                        password_hash=password_hasher.hash(settings.bootstrap_admin_password),
                        role="admin",
                        quota_bytes=settings.default_quota_bytes,
                    )
                )
                db.commit()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


class RegisterInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class FolderInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: int | None = None


class ProfileInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str = Field(default="", max_length=32)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _csrf_cookie(response: Response, csrf: str) -> None:
    response.set_cookie(
        "csrf_token",
        csrf,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_ttl_hours * 3600,
    )


def _issue_session(db: Session, response: Response, user: User) -> None:
    raw_token = secrets.token_urlsafe(32)
    db.add(
        SessionToken(
            token_hash=_token_hash(raw_token),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=settings.session_ttl_hours),
        )
    )
    db.commit()
    response.set_cookie(
        "session",
        raw_token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    _csrf_cookie(response, secrets.token_urlsafe(24))


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    record = db.scalar(select(SessionToken).where(SessionToken.token_hash == _token_hash(token)))
    now = datetime.now(timezone.utc)
    if not record or record.expires_at.replace(tzinfo=timezone.utc) <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account unavailable")
    return user


def require_csrf(request: Request) -> None:
    cookie = request.cookies.get("csrf_token", "")
    header = request.headers.get("X-CSRF-Token", "")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


def _clean_name(name: str) -> str:
    value = PurePath(name.replace("\\", "/")).name.strip()
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)
    if not value or value in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid name")
    return value[:255]


def _file_json(item: StoredFile) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "mime_type": item.mime_type,
        "size_bytes": item.size_bytes,
        "folder_id": item.folder_id,
        "created_at": item.created_at,
        "modified_at": item.modified_at,
        "deleted": item.deleted_at is not None,
    }


def _user_json(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone or "",
        "role": user.role,
        "avatar_url": "/api/v1/profile/avatar" if user.avatar_key else None,
    }


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/api/v1/auth/register", status_code=201)
def register(data: RegisterInput, db: Session = Depends(get_db)) -> dict:
    email = str(data.email).lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        name=data.name.strip(),
        email=email,
        password_hash=password_hasher.hash(data.password),
        quota_bytes=settings.default_quota_bytes,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from exc
    return {"id": user.id, "name": user.name, "email": user.email}


@app.post("/api/v1/auth/login")
def login(data: LoginInput, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == str(data.email).lower().strip()))
    try:
        valid = user is not None and password_hasher.verify(user.password_hash, data.password)
    except VerifyMismatchError:
        valid = False
    if not valid or not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    _issue_session(db, response, user)
    return _user_json(user)


@app.post("/api/v1/auth/logout")
def logout(
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request)
    token = request.cookies.get("session", "")
    record = db.scalar(select(SessionToken).where(SessionToken.token_hash == _token_hash(token)))
    if record:
        db.delete(record)
        db.commit()
    response.delete_cookie(
        "session",
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )
    response.delete_cookie(
        "csrf_token",
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    return {"status": "signed_out"}


@app.get("/api/v1/auth/me")
def me(user: User = Depends(current_user)) -> dict:
    return _user_json(user)


@app.patch("/api/v1/profile")
def update_profile(
    data: ProfileInput,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request)
    email = str(data.email).lower().strip()
    existing = db.scalar(select(User).where(User.email == email, User.id != user.id))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user.name = data.name.strip()
    user.email = email
    user.phone = data.phone.strip()
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from exc
    db.refresh(user)
    return _user_json(user)


@app.post("/api/v1/profile/avatar", status_code=200)
async def update_avatar(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request)
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Profile photo must be 5 MB or smaller")
    if content.startswith(b"\xff\xd8\xff"):
        mime_type = "image/jpeg"
        extension = "jpg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        mime_type = "image/png"
        extension = "png"
    elif len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        mime_type = "image/webp"
        extension = "webp"
    else:
        raise HTTPException(status_code=415, detail="Choose a valid JPEG, PNG, or WebP image")

    old_key = user.avatar_key
    new_key = f"avatars/{uuid4().hex}.{extension}"
    storage.put(new_key, content, mime_type)
    user.avatar_key = new_key
    user.avatar_mime_type = mime_type
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(new_key)
        raise
    if old_key:
        storage.delete(old_key)
    db.refresh(user)
    return _user_json(user)


@app.get("/api/v1/profile/avatar")
def get_avatar(user: User = Depends(current_user)):
    if not user.avatar_key or not user.avatar_mime_type:
        raise HTTPException(status_code=404, detail="Profile photo not found")
    return StreamingResponse(
        storage.stream(user.avatar_key),
        media_type=user.avatar_mime_type,
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "private, max-age=300",
        },
    )


@app.delete("/api/v1/profile/avatar")
def delete_avatar(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request)
    if not user.avatar_key:
        return _user_json(user)
    old_key = user.avatar_key
    user.avatar_key = None
    user.avatar_mime_type = None
    db.commit()
    storage.delete(old_key)
    db.refresh(user)
    return _user_json(user)


@app.get("/api/v1/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    used = db.scalar(
        select(func.coalesce(func.sum(StoredFile.size_bytes), 0)).where(
            StoredFile.owner_id == user.id, StoredFile.deleted_at.is_(None)
        )
    )
    count = db.scalar(
        select(func.count(StoredFile.id)).where(
            StoredFile.owner_id == user.id, StoredFile.deleted_at.is_(None)
        )
    )
    return {
        "used_bytes": used,
        "quota_bytes": user.quota_bytes,
        "remaining_bytes": max(0, user.quota_bytes - used),
        "file_count": count,
        "folder_count": db.scalar(select(func.count(Folder.id)).where(Folder.owner_id == user.id)),
    }


@app.get("/api/v1/files")
def list_files(
    folder_id: int | None = None,
    search: str = "",
    include_trash: bool = False,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(StoredFile).where(StoredFile.owner_id == user.id)
    query = query.where(StoredFile.deleted_at.is_not(None) if include_trash else StoredFile.deleted_at.is_(None))
    if not include_trash:
        query = query.where(StoredFile.folder_id == folder_id)
    if search:
        query = query.where(StoredFile.name.ilike(f"%{search[:120]}%"))
    return [_file_json(item) for item in db.scalars(query.order_by(StoredFile.modified_at.desc()).limit(500))]


@app.post("/api/v1/files", status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    folder_id: int | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request)
    if folder_id is not None and not db.scalar(
        select(Folder.id).where(Folder.id == folder_id, Folder.owner_id == user.id, Folder.deleted_at.is_(None))
    ):
        raise HTTPException(status_code=404, detail="Folder not found")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds the configured upload limit")
    locked_user = db.scalar(select(User).where(User.id == user.id).with_for_update())
    if not locked_user:
        raise HTTPException(status_code=401, detail="Account unavailable")
    used = db.scalar(
        select(func.coalesce(func.sum(StoredFile.size_bytes), 0)).where(
            StoredFile.owner_id == locked_user.id, StoredFile.deleted_at.is_(None)
        )
    )
    if used + len(content) > locked_user.quota_bytes:
        raise HTTPException(status_code=413, detail="Storage quota exceeded")
    name = _clean_name(file.filename or "")
    item = StoredFile(
        owner_id=user.id,
        folder_id=folder_id,
        object_key=uuid4().hex,
        name=name,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
    )
    storage.put(item.object_key, content, item.mime_type)
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        storage.delete(item.object_key)
        raise HTTPException(status_code=409, detail="An item with this name already exists in the folder") from exc
    except Exception:
        db.rollback()
        storage.delete(item.object_key)
        raise
    return _file_json(item)


@app.get("/api/v1/files/{file_id}/download")
def download_file(file_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(
        select(StoredFile).where(
            StoredFile.id == file_id,
            StoredFile.owner_id == user.id,
            StoredFile.deleted_at.is_(None),
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="File not found")
    return StreamingResponse(
        storage.stream(item.object_key),
        media_type=item.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{item.name.replace(chr(34), "")}"'},
    )


@app.patch("/api/v1/files/{file_id}")
def rename_file(
    file_id: int,
    request: Request,
    name: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request)
    item = db.scalar(select(StoredFile).where(StoredFile.id == file_id, StoredFile.owner_id == user.id))
    if not item:
        raise HTTPException(status_code=404, detail="File not found")
    item.name = _clean_name(name)
    item.modified_at = utcnow()
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An item with this name already exists in the folder") from exc
    return _file_json(item)


@app.delete("/api/v1/files/{file_id}")
def trash_file(
    file_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request)
    item = db.scalar(
        select(StoredFile).where(
            StoredFile.id == file_id, StoredFile.owner_id == user.id, StoredFile.deleted_at.is_(None)
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="File not found")
    item.deleted_at = utcnow()
    db.commit()
    return {"status": "trashed"}


@app.post("/api/v1/files/{file_id}/restore")
def restore_file(
    file_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request)
    item = db.scalar(
        select(StoredFile).where(
            StoredFile.id == file_id, StoredFile.owner_id == user.id, StoredFile.deleted_at.is_not(None)
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="Trashed file not found")
    item.deleted_at = None
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Rename the existing item before restoring this file") from exc
    return {"status": "restored"}


@app.delete("/api/v1/files/{file_id}/permanent")
def permanently_delete_file(
    file_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request)
    item = db.scalar(
        select(StoredFile).where(
            StoredFile.id == file_id, StoredFile.owner_id == user.id, StoredFile.deleted_at.is_not(None)
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="Trashed file not found")
    storage.delete(item.object_key)
    db.delete(item)
    db.commit()
    return {"status": "deleted"}


@app.get("/api/v1/folders")
def list_folders(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    return [
        {"id": f.id, "name": f.name, "parent_id": f.parent_id}
        for f in db.scalars(
            select(Folder).where(Folder.owner_id == user.id, Folder.deleted_at.is_(None)).order_by(Folder.name)
        )
    ]


@app.post("/api/v1/folders", status_code=201)
def create_folder(
    data: FolderInput,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request)
    if data.parent_id is not None and not db.scalar(
        select(Folder.id).where(
            Folder.id == data.parent_id, Folder.owner_id == user.id, Folder.deleted_at.is_(None)
        )
    ):
        raise HTTPException(status_code=404, detail="Parent folder not found")
    folder = Folder(owner_id=user.id, parent_id=data.parent_id, name=_clean_name(data.name))
    db.add(folder)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A folder with this name already exists") from exc
    return {"id": folder.id, "name": folder.name, "parent_id": folder.parent_id}


@app.get("/api/v1/admin/users")
def admin_users(
    admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[dict]:
    users = db.scalars(select(User).order_by(User.created_at.desc()).limit(500))
    results = []
    for user in users:
        used = db.scalar(
            select(func.coalesce(func.sum(StoredFile.size_bytes), 0)).where(
                StoredFile.owner_id == user.id, StoredFile.deleted_at.is_(None)
            )
        )
        results.append(
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "used_bytes": used,
                "quota_bytes": user.quota_bytes,
            }
        )
    return results
