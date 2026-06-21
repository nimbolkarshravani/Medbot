"""
MedBot API — Vercel Python serverless function.
Handles auth (email OTP via Supabase REST API) and protected endpoints.
All Supabase communication happens server-side — frontend has zero SDK code.
"""
import os
from datetime import datetime, timezone

import httpx
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


# ── Auth ─────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    redirect_to: str = ""


class SessionRequest(BaseModel):
    access_token: str


@app.post("/api/auth/login")
async def auth_login(body: LoginRequest):
    """Send magic link email via Supabase (works on free tier, no template changes)."""
    payload = {"email": body.email, "create_user": True}
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/magiclink",
            json=payload,
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
        )
    if resp.status_code >= 400:
        detail = "Failed to send magic link"
        try:
            detail = resp.json().get("msg", detail)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=detail)
    return {"message": "Check your email for a magic link"}


@app.post("/api/auth/session")
async def auth_session(body: SessionRequest):
    """Receive access_token from frontend (after magic link redirect), verify it, set httpOnly cookie."""
    try:
        payload = jwt.decode(
            body.access_token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = payload.get("sub")
    email = payload.get("email", "")
    if not uid:
        raise HTTPException(status_code=401, detail="Token missing user ID")
    exp = payload.get("exp", 0)
    import time
    max_age = max(int(exp - time.time()), 60)
    response = JSONResponse({"user": {"id": uid, "email": email}})
    response.set_cookie(
        "medbot_token",
        body.access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    return response


@app.post("/api/auth/logout")
async def auth_logout():
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
