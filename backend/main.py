from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
import asyncio

import models
import auth
from database import engine, get_db
from classifier import classify_audio, classify_live_tick

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SonicSense AI")

# Allow the frontend (served from a different port/file) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Schemas ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = ""
    admin_code: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    organization: Optional[str] = None


ADMIN_SIGNUP_CODE = "SONIC-ADMIN-2026"  # change this to your own secret

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Auth Routes ----------
@app.post("/auth/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    role = "admin" if user.admin_code == ADMIN_SIGNUP_CODE else "user"

    new_user = models.User(
        email=user.email,
        hashed_password=auth.hash_password(user.password),
        full_name=user.full_name or "",
        role=role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = auth.create_access_token({"sub": new_user.email})
    return {"access_token": token}

@app.post("/auth/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = auth.create_access_token({"sub": db_user.email})
    return {"access_token": token}


# ---------- Profile ----------
@app.get("/auth/me")
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return {
        "email": current_user.email,
        "full_name": current_user.full_name,
        "organization": current_user.organization,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat(),
    }


@app.put("/auth/me")
def update_me(
    update: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if update.full_name is not None:
        current_user.full_name = update.full_name
    if update.organization is not None:
        current_user.organization = update.organization
    db.commit()
    db.refresh(current_user)
    return {
        "email": current_user.email,
        "full_name": current_user.full_name,
        "organization": current_user.organization,
        "role": current_user.role,
    }


# ---------- Admin ----------
@app.get("/admin/users")
def list_all_users(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(auth.require_admin),
):
    users = db.query(models.User).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "organization": u.organization,
            "role": u.role,
            "created_at": u.created_at.isoformat(),
            "prediction_count": len(u.predictions),
        }
        for u in users
    ]


@app.get("/admin/stats")
def admin_stats(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(auth.require_admin),
):
    total_users = db.query(models.User).count()
    total_predictions = db.query(models.Prediction).count()
    total_admins = db.query(models.User).filter(models.User.role == "admin").count()
    return {
        "total_users": total_users,
        "total_predictions": total_predictions,
        "total_admins": total_admins,
    }

# ---------- Upload / Predict ----------
import os
import tempfile

@app.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    suffix = os.path.splitext(file.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        predictions = classify_audio(filename=file.filename, file_path=tmp_path)
    finally:
        os.remove(tmp_path)

    for p in predictions:
        record = models.Prediction(
            owner_id=current_user.id,
            label=p["label"],
            confidence=p["confidence"],
            source="upload",
            filename=file.filename,
        )
        db.add(record)
    db.commit()

    return {"filename": file.filename, "predictions": predictions}
# ---------- History ----------
@app.get("/history")
def get_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    records = (
        db.query(models.Prediction)
        .filter(models.Prediction.owner_id == current_user.id)
        .order_by(models.Prediction.timestamp.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "label": r.label,
            "confidence": r.confidence,
            "source": r.source,
            "filename": r.filename,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in records
    ]


# ---------- Live Detection (WebSocket) ----------
@app.websocket("/ws/live")
async def live_detection(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(3600)  # idle — real live mic inference not yet implemented
    except WebSocketDisconnect:
        pass