"""
MedBot API — Vercel Python serverless function.
Email + password authentication via Supabase Auth.
RAG pipeline: upload, chunk, embed, analyze, chat.
"""
import os
import re
import time
import json
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import Client, create_client
import google.generativeai as genai

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(title="MedBot API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://medbot-hazel.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_client: Client | None = None
_admin_client: Client | None = None


def get_db() -> Client:
    """Anon client — used only for auth verification (get_user)."""
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY or SUPABASE_KEY)
    return _client


def get_admin_db() -> Client:
    """Service role client — bypasses RLS for all DB reads/writes."""
    global _admin_client
    if _admin_client is None:
        key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY or SUPABASE_ANON_KEY
        _admin_client = create_client(SUPABASE_URL, key)
    return _admin_client


def _get_user(request: Request) -> dict:
    token = request.cookies.get("medbot_token")
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(
            status_code=401,
            detail=f"Not authenticated (cookies: {list(request.cookies.keys())}, has_auth_header: {'authorization' in request.headers})"
        )
    # Delegate verification to Supabase — avoids JWT algorithm/secret issues
    # (newer Supabase projects sign with ES256, not the HS256 legacy secret).
    db = get_db()
    try:
        result = db.auth.get_user(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")
    user = getattr(result, "user", None)
    if not user or not getattr(user, "id", None):
        raise HTTPException(status_code=401, detail="Token did not resolve to a user")
    return {"id": user.id, "email": getattr(user, "email", "") or ""}


# ── PII Redaction ───────────────────────────────────────────────────────

PII_PATTERNS = [
    (r'\b(Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+', '[NAME]'),
    (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b(?=\s*,?\s*(?:MD|DO|RN|PhD|NP|PA))', '[PROVIDER]'),
    (r'\b(?:SSN|Social Security(?:\s+Number)?)[\s:#]*\d{3}[-\s]?\d{2}[-\s]?\d{4}', '[SSN]'),
    (r'\b\d{3}[- ]?\d{2}[- ]?\d{4}\b(?!\d)', '[SSN]'),
    (r'\bMRN[\s:#]*[A-Z0-9\-]+', '[MRN]'),
    (r'\bPatient\s+(?:ID|Number)[\s:#]*[A-Z0-9\-]+', '[PATIENT-ID]'),
    (r'\b(?:\+1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', '[PHONE]'),
    (r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b', '[EMAIL]'),
    (r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl)\b(?:[^,\n]{0,40})?', '[ADDRESS]'),
    (r'\b(?:DOB|Date of Birth|Birth Date|Born(?:\s+on)?)[\s:]*(?:\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})', '[DOB]'),
    (r'\b(?:0[1-9]|1[0-2])[\/\-](?:0[1-9]|[12]\d|3[01])[\/\-](?:19|20)\d{2}\b', '[DOB]'),
    (r'\b(?:Memorial|General|Community|Regional|University|St\.?\s+[A-Z][a-z]+|[A-Z][a-z]+ Medical|[A-Z][a-z]+ Health(?:care)?)\s+(?:Hospital|Clinic|Medical Center|Health System|Health Center|Centre)\b', '[FACILITY]'),
]


def redact_pii(text: str) -> str:
    out = text
    for pattern, replacement in PII_PATTERNS:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE if replacement in ('[ADDRESS]', '[DOB]', '[FACILITY]', '[MRN]', '[PATIENT-ID]', '[SSN]') else 0)
    return out


# ── Text Chunking ───────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_at = max(last_period, last_newline)
            if break_at > chunk_size * 0.4:
                chunk = text[start:start + break_at + 1]
                end = start + break_at + 1
        chunks.append(chunk.strip())
        start = end - overlap
    return [c for c in chunks if c]


# ── Embeddings ──────────────────────────────────────────────────────────

EMBED_MODEL = "models/gemini-embedding-001"
EMBED_DIMS = 768


def get_embeddings(texts: List[str]) -> List[List[float]]:
    result = genai.embed_content(
        model=EMBED_MODEL,
        content=texts,
        task_type="retrieval_document",
        output_dimensionality=EMBED_DIMS,
    )
    return result['embedding']


def get_query_embedding(text: str) -> List[float]:
    result = genai.embed_content(
        model=EMBED_MODEL,
        content=text,
        task_type="retrieval_query",
        output_dimensionality=EMBED_DIMS,
    )
    return result['embedding']


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
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    db = get_db()
    try:
        result = db.auth.sign_up({"email": body.email, "password": body.password})
        user = result.user
        if not user:
            raise HTTPException(status_code=400, detail="Signup failed — no user returned")
        return {"user": {"id": user.id, "email": user.email}}
    except HTTPException:
        raise
    except AttributeError as e:
        raise HTTPException(status_code=500, detail=f"Auth method error: {str(e)}")
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(status_code=400, detail=error_msg if error_msg else "Signup failed")


@app.post("/api/auth/login")
async def auth_login(body: SignInRequest):
    db = get_db()
    try:
        result = db.auth.sign_in_with_password({"email": body.email, "password": body.password})
    except AttributeError as e:
        raise HTTPException(status_code=500, detail=f"Auth method error: {str(e)}")
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(status_code=401, detail=error_msg if error_msg else "Login failed")

    if not result or not result.session:
        raise HTTPException(status_code=500, detail="No session returned")

    session = result.session
    if not session.access_token:
        raise HTTPException(status_code=500, detail="No access token in session")

    user = result.user
    max_age = max(int(session.expires_in or 3600), 60)

    response = JSONResponse({
        "user": {"id": user.id, "email": user.email},
        "access_token": session.access_token,
    })
    response.set_cookie(
        "medbot_token",
        session.access_token,
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
    try:
        db = get_db()
        if not db:
            return {"status": "error", "detail": "Supabase client not initialized"}
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "supabase": "connected",
            "gemini": "configured" if GEMINI_API_KEY else "not configured",
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@app.get("/api/diagnostics/embedding-models")
def list_embedding_models():
    """List all available embedding models on the configured Gemini API key."""
    try:
        available = []
        for model in genai.list_models():
            if "embedContent" in model.supported_generation_methods:
                available.append({
                    "name": model.name,
                    "display_name": model.display_name,
                })
        return {"embedding_models": available}
    except Exception as e:
        return {"error": str(e)}


# ── Protected ────────────────────────────────────────────────────────────

@app.get("/api/me")
def get_me(request: Request):
    user = _get_user(request)
    return {"id": user["id"], "email": user["email"]}


# ── Reports: Upload ─────────────────────────────────────────────────────

class ReportUpload(BaseModel):
    file_name: str
    text: str
    original_file: str = ""
    source_type: str = "upload"


@app.post("/api/reports/upload")
def upload_report(body: ReportUpload, request: Request):
    user = _get_user(request)
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Report text is empty")

    db = get_admin_db()

    redacted = redact_pii(body.text)
    chunks = chunk_text(redacted)

    report_result = (
        db.table("reports")
        .insert({
            "patient_id": user["id"],
            "file_name": body.file_name,
            "source_type": body.source_type,
            "status": "processing",
            "chunk_count": len(chunks),
            "original_file": body.original_file,
        })
        .execute()
    )
    report = report_result.data[0]
    report_id = report["id"]

    try:
        embeddings = get_embeddings(chunks)

        chunk_rows = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_rows.append({
                "patient_id": user["id"],
                "report_id": report_id,
                "chunk_text": chunk,
                "embedding": embedding,
                "metadata": {"index": i, "file_name": body.file_name},
            })

        db.table("chunks").insert(chunk_rows).execute()

        db.table("reports").update({"status": "ready"}).eq("id", report_id).execute()

        return {
            "report_id": report_id,
            "file_name": body.file_name,
            "chunk_count": len(chunks),
            "status": "ready",
        }
    except Exception as e:
        db.table("reports").update({"status": "error"}).eq("id", report_id).execute()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# ── Reports: Analyze ────────────────────────────────────────────────────

@app.post("/api/reports/{report_id}/analyze")
def analyze_report(report_id: str, request: Request):
    user = _get_user(request)
    db = get_admin_db()

    report_result = (
        db.table("reports")
        .select("*")
        .eq("id", report_id)
        .eq("patient_id", user["id"])
        .execute()
    )
    if not report_result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    report = report_result.data[0]

    if report.get("analysis"):
        return {"analysis": report["analysis"], "cached": True}

    chunks_result = (
        db.table("chunks")
        .select("chunk_text")
        .eq("report_id", report_id)
        .order("id")
        .execute()
    )
    if not chunks_result.data:
        raise HTTPException(status_code=400, detail="No chunks found for this report")

    full_text = "\n".join(c["chunk_text"] for c in chunks_result.data)

    prompt = f"""You are a warm, friendly doctor explaining medical results in simple language. Analyze this medical report.
Reply ONLY with valid JSON (no markdown, no extra text) matching this exact structure:
{{
  "reportType": "short report type label",
  "healthScore": <integer 1-10>,
  "summary": "One sentence overall health picture in plain English",
  "findings": [
    {{ "category": "critical|warning|normal", "title": "...", "description": "Max 2 short plain-English sentences" }}
  ],
  "actions": ["Action 1", "Action 2", "Action 3"],
  "drAidenNote": "Warm, reassuring 1-sentence note"
}}

CRITICAL: healthScore must be an integer from 1 to 10 (NOT a percentage, NOT out of 100).
- 10 = perfect health, everything normal
- 7-9 = mostly healthy, minor concerns
- 4-6 = moderate concerns, needs attention
- 1-3 = urgent issues requiring immediate care

Keep descriptions short. Max 6 findings. Prioritize critical first.

Medical Report:
{full_text[:8000]}"""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.25,
                "max_output_tokens": 4096,
                "response_mime_type": "application/json",
            },
        )
        raw = response.text
    except Exception as e:
        db.table("reports").update({"status": "error"}).eq("id", report_id).execute()
        raise HTTPException(status_code=500, detail=f"Gemini error: {type(e).__name__}: {str(e)}")

    try:
        analysis = json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if not match:
            raise HTTPException(status_code=500, detail=f"AI did not return valid JSON: {raw[:200]}")
        try:
            analysis = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {raw[:200]}")

    # Clamp healthScore to 1-10 range (guard against strings/percentages)
    try:
        score = int(float(analysis.get("healthScore", 5)))
        if score > 10:
            score = round(score / 10)
        analysis["healthScore"] = max(1, min(10, score))
    except (TypeError, ValueError):
        analysis["healthScore"] = 5

    db.table("reports").update({"analysis": analysis}).eq("id", report_id).execute()

    return {"analysis": analysis, "cached": False}


# ── Chat (RAG) ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    report_id: str
    question: str
    history: list = []


@app.post("/api/chat")
def chat_rag(body: ChatRequest, request: Request):
    user = _get_user(request)
    db = get_admin_db()

    # Verify the current report belongs to this user
    report_result = (
        db.table("reports")
        .select("*")
        .eq("id", body.report_id)
        .eq("patient_id", user["id"])
        .execute()
    )
    if not report_result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    current_report = report_result.data[0]

    # Retrieve across ALL user reports (the core RAG value)
    query_embedding = get_query_embedding(body.question)

    try:
        match_result = db.rpc("match_chunks", {
            "query_embedding": query_embedding,
            "match_count": 8,
            "patient_id_filter": user["id"],
        }).execute()
        retrieved = match_result.data if match_result.data else []
    except Exception:
        # Fallback: fetch from all user's chunks without vector search
        chunks_result = (
            db.table("chunks")
            .select("chunk_text, report_id")
            .eq("patient_id", user["id"])
            .order("id")
            .limit(8)
            .execute()
        )
        retrieved = [{"chunk_text": c["chunk_text"], "report_id": c["report_id"], "uploaded_at": None} for c in chunks_result.data] if chunks_result.data else []

    # Build context with report dates so the LLM can reference trends
    context_parts = []
    for chunk in retrieved:
        date_label = ""
        if chunk.get("uploaded_at"):
            date_label = chunk["uploaded_at"][:10]
        elif chunk.get("report_id") == body.report_id:
            date_label = (current_report.get("uploaded_at") or "")[:10]
        prefix = f"[Report {date_label}]" if date_label else "[Report]"
        context_parts.append(f"{prefix}: {chunk['chunk_text']}")

    context_text = "\n---\n".join(context_parts)

    # Include current report's analysis summary
    analysis_summary = ""
    if current_report.get("analysis"):
        a = current_report["analysis"]
        findings_str = "\n".join(
            f"  - [{f['category'].upper()}] {f['title']}: {f['description']}"
            for f in a.get("findings", [])
        )
        analysis_summary = f"""
Current Report Type: {a.get('reportType', 'Unknown')}
Health Score: {a.get('healthScore', '?')}/10
Summary: {a.get('summary', '')}
Findings:
{findings_str}
Actions: {'; '.join(a.get('actions', []))}"""

    system_prompt = f"""You are a warm, friendly doctor helping a patient understand their medical reports.
You have access to the patient's medical history across multiple reports.
When answering questions, reference the report dates to show trends or comparisons.
If asked about changes over time, compare values across the retrieved report chunks.
Always cite which report (by date) a value came from.
Answer in plain English. Keep answers concise. Be reassuring but honest.
Never diagnose or prescribe — always recommend seeing a real doctor for serious concerns.

CURRENT REPORT ANALYSIS:{analysis_summary}

RETRIEVED SECTIONS FROM PATIENT'S REPORTS:
{context_text}"""

    contents = [
        {"role": "user", "parts": [{"text": system_prompt + "\n\nThe patient will now ask follow-up questions."}]},
        {"role": "model", "parts": [{"text": "I've reviewed your reports. I can see data across your medical history — feel free to ask anything, including comparisons over time."}]},
    ]

    for msg in body.history[-10:]:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.get("text", "")}]})

    contents.append({"role": "user", "parts": [{"text": body.question}]})

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(
        contents,
        generation_config=genai.GenerationConfig(temperature=0.7, max_output_tokens=512),
    )

    reply = response.text.strip()

    # Save user message and assistant response to DB
    try:
        db.table("chat_messages").insert({
            "patient_id": user["id"],
            "role": "user",
            "content": body.question,
            "referenced_report_ids": [body.report_id],
        }).execute()
        db.table("chat_messages").insert({
            "patient_id": user["id"],
            "role": "assistant",
            "content": reply,
        }).execute()
    except Exception as e:
        pass  # Non-critical; still return the response

    return {"reply": reply}


@app.get("/api/chat/history")
def get_chat_history(request: Request):
    """Get last 50 chat messages for the user."""
    user = _get_user(request)
    db = get_admin_db()
    try:
        result = (
            db.table("chat_messages")
            .select("*")
            .eq("patient_id", user["id"])
            .order("created_at", desc=False)
            .limit(50)
            .execute()
        )
        return {"messages": result.data or []}
    except Exception:
        return {"messages": []}


# ── Reports: Get single report with text ────────────────────────────────

@app.get("/api/reports/{report_id}")
def get_report(report_id: str, request: Request):
    user = _get_user(request)
    db = get_admin_db()
    report_result = (
        db.table("reports")
        .select("*")
        .eq("id", report_id)
        .eq("patient_id", user["id"])
        .execute()
    )
    if not report_result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    report = report_result.data[0]

    chunks_result = (
        db.table("chunks")
        .select("chunk_text")
        .eq("report_id", report_id)
        .order("id")
        .execute()
    )
    report["full_text"] = "\n".join(c["chunk_text"] for c in chunks_result.data) if chunks_result.data else ""

    return {"report": report}



# ── Reports: List ───────────────────────────────────────────────────────

@app.get("/api/reports")
def list_reports(request: Request):
    user = _get_user(request)
    db = get_admin_db()
    result = (
        db.table("reports")
        .select("*")
        .eq("patient_id", user["id"])
        .order("uploaded_at", desc=True)
        .execute()
    )
    return {"reports": result.data}


# ── Reports: Delete ─────────────────────────────────────────────────────

@app.delete("/api/reports/{report_id}")
def delete_report(report_id: str, request: Request):
    user = _get_user(request)
    db = get_admin_db()

    db.table("chunks").delete().eq("report_id", report_id).eq("patient_id", user["id"]).execute()
    db.table("reports").delete().eq("id", report_id).eq("patient_id", user["id"]).execute()

    return {"message": "Report deleted"}
