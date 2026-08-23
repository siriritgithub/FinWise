from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import get_current_user, hash_password, verify_password
from app.models.user import User
from app.schemas.schemas import UserOut, UserUpdate, AppLockSet, AppLockVerify

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/app-lock")
def set_app_lock(
    body: AppLockSet,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.app_lock_hash = hash_password(body.pin)
    db.commit()
    return {"message": "App lock PIN set successfully"}


@router.post("/me/verify-app-lock")
def verify_app_lock(
    body: AppLockVerify,
    current_user: User = Depends(get_current_user),
):
    if not current_user.app_lock_hash:
        raise HTTPException(status_code=400, detail="App lock not set")
    if not verify_password(body.pin, current_user.app_lock_hash):
        raise HTTPException(status_code=401, detail="Incorrect PIN")
    return {"message": "PIN verified"}

@router.post("/me/profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import os, uuid
    from fastapi import UploadFile
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Profile photo must be JPG, PNG or WebP")
    upload_dir = os.path.join(get_settings().UPLOAD_DIR, str(current_user.id), "profile")
    os.makedirs(upload_dir, exist_ok=True)
    ext = ".jpg" if file.content_type == "image/jpeg" else ".png" if file.content_type == "image/png" else ".webp"
    filename = f"avatar-{uuid.uuid4().hex}{ext}"
    path = os.path.join(upload_dir, filename)
    with open(path, "wb") as out:
        out.write(await file.read())
    current_user.profile_photo_path = path.replace("\\", "/")
    db.commit(); db.refresh(current_user)
    return UserOut.model_validate(current_user)


@router.delete("/me/profile-photo", response_model=UserOut)
def delete_profile_photo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import os
    if current_user.profile_photo_path and os.path.exists(current_user.profile_photo_path):
        os.remove(current_user.profile_photo_path)
    current_user.profile_photo_path = None
    db.commit(); db.refresh(current_user)
    return current_user
