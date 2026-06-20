from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth import get_current_user
from config import settings
from database import get_db

app = FastAPI(title="MedBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Public ────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── Protected ─────────────────────────────────────────────────────────────

@app.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"]}


class ReportCreate(BaseModel):
    file_name: str
    source_type: str = "upload"


@app.post("/reports")
def create_report(body: ReportCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    result = (
        db.table("reports")
        .insert({
            "patient_id": user["id"],
            "file_name": body.file_name,
            "source_type": body.source_type,
        })
        .execute()
    )
    return {"report": result.data[0] if result.data else None}


@app.get("/reports")
def list_reports(user: dict = Depends(get_current_user)):
    db = get_db()
    result = (
        db.table("reports")
        .select("*")
        .eq("patient_id", user["id"])
        .order("uploaded_at", desc=True)
        .execute()
    )
    return {"reports": result.data}
