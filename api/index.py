"""
MedBot API — Vercel Python serverless function.
Email + password authentication via Supabase Auth.
"""
import os
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from supabase import Client, create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

app = FastAPI(title="MedBot API", version="2.0.0")

_client: Client | None = None


def get_db() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY or SUPABASE_ANON_KEY)
    return _client


def _get_user(request: Request) -> dict:
    token = request.cookies.get("medbot_token")
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="Token missing user ID")
    return {"id": uid, "email": payload.get("email", "")}


# ── Auth Models ──────────────────────────────────────────────────────────

class SignUpRequest(BaseModel):
    email: str
    password: str


class SignInRequest(BaseModel):
    email: str
    password: str


# ── Auth Endpoints ───────────────────────────────────────────────────────

@app.post("/api/auth/signup")
async def auth_signup(body: SignUpRequest):
    """Create new user account with email + password."""
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    db = get_db()
    try:
        result = db.auth.sign_up(email=body.email, password=body.password)
        return {"user": {"id": result.user.id, "email": result.user.email}}
    except Exception as e:
        detail = str(e)
        if "already registered" in detail.lower():
            detail = "Email already registered"
        elif "invalid" in detail.lower():
            detail = "Invalid email format"
        raise HTTPException(status_code=400, detail=detail)


@app.post("/api/auth/login")
async def auth_login(body: SignInRequest):
    """Sign in with email + password, set httpOnly cookie."""
    db = get_db()
    try:
        result = db.auth.sign_in_with_password(email=body.email, password=body.password)
    except Exception as e:
        detail = str(e)
        if "invalid" in detail.lower() or "credentials" in detail.lower():
            detail = "Invalid email or password"
        raise HTTPException(status_code=401, detail=detail)

    access_token = result.session.access_token if result.session else None
    if not access_token:
        raise HTTPException(status_code=500, detail="Failed to get access token")

    user = result.user
    exp = result.session.expires_in if result.session else 3600
    max_age = max(int(exp), 60)

    response = JSONResponse({"user": {"id": user.id, "email": user.email}})
    response.set_cookie(
        "medbot_token",
        access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    return response


@app.post("/api/auth/logout")
async def auth_logout():
    """Clear session cookie."""
    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("medbot_token", path="/")
    return response


# ── Public ───────────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Protected ────────────────────────────────────────────────────────────

@app.get("/api/me")
def get_me(request: Request):
    user = _get_user(request)
    return {"id": user["id"], "email": user["email"]}


class ReportCreate(BaseModel):
    file_name: str
    source_type: str = "upload"


@app.post("/api/reports")
def create_report(body: ReportCreate, request: Request):
    user = _get_user(request)
    db = get_db()
    result = (
        db.table("reports")
        .insert(
            {
                "patient_id": user["id"],
                "file_name": body.file_name,
                "source_type": body.source_type,
            }
        )
        .execute()
    )
    return {"report": result.data[0] if result.data else None}


@app.get("/api/reports")
def list_reports(request: Request):
    user = _get_user(request)
    db = get_db()
    result = (
        db.table("reports")
        .select("*")
        .eq("patient_id", user["id"])
        .order("uploaded_at", desc=True)
        .execute()
    )
    return {"reports": result.data}
