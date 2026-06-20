"""
MedBot API — runs as a Vercel Python serverless function.

Vercel serves every request matching /api/* to this single FastAPI app
(see the rewrite in vercel.json). Because the original path is preserved,
all routes are defined with the /api prefix.

Self-contained on purpose: Vercel treats each top-level file in /api as its
own function entry point, so helper modules are inlined here to avoid
accidental extra endpoints.
"""
import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from supabase import Client, create_client

# ── Config (from Vercel environment variables) ─────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(title="MedBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

_client: Client | None = None


def get_db() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )
    return {"id": user_id, "email": payload.get("email", "")}


# ── Public ─────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Protected ──────────────────────────────────────────────────────────────
@app.get("/api/me")
def get_me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"]}


class ReportCreate(BaseModel):
    file_name: str
    source_type: str = "upload"


@app.post("/api/reports")
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


@app.get("/api/reports")
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
