from __future__ import annotations

import json
import logging

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from typing import List, Optional

from openai import OpenAI

from backend.auth import AuthUser, get_current_user
from backend.config import CORS_ORIGINS, OPENAI_API_KEY, SUPABASE_ANON_KEY, SUPABASE_URL
from backend.convex_client import (
    create_job,
    get_analysis,
    get_job,
    list_analyses,
    upsert_user_profile,
)
from backend.pipeline.orchestrator import run_pipeline
from backend.pipeline.pdf_export import generate_pdf
from backend.pipeline.revenue_simulation import run_simulation

logger = logging.getLogger(__name__)


def _user_or_ip_key(request: Request) -> str:
    """Rate-limit key: prefer authenticated user id, fall back to client IP."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer ") and len(auth) > 10:
        try:
            user: AuthUser = get_current_user(auth)
            return f"user:{user.user_id}"
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_user_or_ip_key)

app = FastAPI(
    title="Business Idea Analyzer",
    description="Analyze any business idea with web research, social sentiment, and AI-powered insights.",
    version="0.3.0",
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return Response(
        content=json.dumps({"detail": "Rate limit exceeded. Please try again later."}),
        status_code=429,
        media_type="application/json",
        headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class AnalyzeRequest(BaseModel):
    idea: str = Field(
        ...,
        min_length=3,
        max_length=500,
        examples=["An app for tracking freelance invoices"],
    )


async def _run_pipeline_bg(idea: str, job_id: str, user_id: str) -> None:
    """Background wrapper — exceptions are caught by the orchestrator and sent to Convex."""
    try:
        await run_pipeline(idea, job_id=job_id, user_id=user_id)
    except Exception:
        pass


def _sync_user_profile_best_effort(user: AuthUser) -> None:
    try:
        upsert_user_profile(
            user_id=user.user_id,
            email=(user.email or "").strip(),
        )
    except Exception:
        pass


@app.post("/analyze")
@limiter.limit("5/minute")
async def analyze(request: Request, req: AnalyzeRequest, bg: BackgroundTasks, user: AuthUser = Depends(get_current_user)):
    _sync_user_profile_best_effort(user)
    try:
        job_id = create_job(req.idea, user.user_id)
    except Exception as exc:
        logger.error("Convex create_job failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to start analysis. Please try again.")

    bg.add_task(_run_pipeline_bg, req.idea, job_id, user.user_id)
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
@limiter.limit("30/minute")
async def job_status(request: Request, job_id: str, user: AuthUser = Depends(get_current_user)):
    try:
        job = get_job(job_id, user.user_id)
    except Exception as exc:
        logger.error("Convex get_job failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to fetch job status.")
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job.get("status", "running")
    resp = {
        "status": status,
        "progress": job.get("progress", 0),
        "label": job.get("stage_label", ""),
    }

    if status == "completed":
        resp["status"] = "complete"
        try:
            record = get_analysis(job_id, user.user_id)
            if record and record.get("result"):
                result = record["result"]
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except json.JSONDecodeError:
                        pass
                resp["result"] = result
        except Exception:
            pass

    if status == "failed":
        resp["error"] = job.get("error", "Unknown error")

    return resp


@app.get("/history")
@limiter.limit("20/minute")
async def history(request: Request, user: AuthUser = Depends(get_current_user)):
    _sync_user_profile_best_effort(user)
    try:
        items = list_analyses(user.user_id)
    except Exception as exc:
        logger.error("Convex list_analyses failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to load history.")

    for item in items:
        if isinstance(item.get("result"), str):
            try:
                item["result"] = json.loads(item["result"])
            except json.JSONDecodeError:
                pass
    return items


@app.get("/history/{job_id}")
@limiter.limit("20/minute")
async def history_detail(request: Request, job_id: str, user: AuthUser = Depends(get_current_user)):
    _sync_user_profile_best_effort(user)
    try:
        record = get_analysis(job_id, user.user_id)
    except Exception as exc:
        logger.error("Convex get_analysis failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to load analysis.")
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if isinstance(record.get("result"), str):
        try:
            record["result"] = json.loads(record["result"])
        except json.JSONDecodeError:
            pass
    return record


@app.get("/export/{job_id}/pdf")
@limiter.limit("10/minute")
async def export_pdf(request: Request, job_id: str, user: AuthUser = Depends(get_current_user)):
    try:
        record = get_analysis(job_id, user.user_id)
    except Exception as exc:
        logger.error("Convex get_analysis (PDF) failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to load analysis for export.")
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    result_data = record.get("result", record)
    if isinstance(result_data, str):
        try:
            result_data = json.loads(result_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Corrupt analysis data")

    pdf_bytes = generate_pdf(result_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=forma_{job_id}.pdf"},
    )


class SimulationRequest(BaseModel):
    """User-tweakable revenue simulation parameters.

    All fields are optional — omitted fields fall back to the AI-generated
    defaults stored in the analysis (when job_id is provided) or to
    conservative built-in defaults.
    """
    job_id: Optional[str] = Field(None, description="Load AI-generated defaults from this analysis")
    price_per_user_monthly: Optional[float] = Field(None, gt=0, description="Monthly price per user (USD)")
    initial_users: Optional[int] = Field(None, gt=0, description="Paying users in month 1")
    monthly_growth_rate: Optional[float] = Field(None, ge=0, le=1, description="MoM growth rate (0-1)")
    churn_rate: Optional[float] = Field(None, ge=0, lt=1, description="Monthly churn rate (0-1)")
    fixed_monthly_cost: Optional[float] = Field(None, ge=0, description="Fixed monthly operating cost (USD)")
    variable_cost_per_user: Optional[float] = Field(None, ge=0, description="Variable cost per user (USD)")
    projection_months: Optional[int] = Field(None, ge=1, le=120, description="How many months to project")


@app.post("/simulate/revenue")
@limiter.limit("15/minute")
async def simulate_revenue(request: Request, req: SimulationRequest, user: AuthUser = Depends(get_current_user)):
    """Run a revenue simulation with tweakable parameters."""
    base_params: dict = {}

    if req.job_id:
        try:
            record = get_analysis(req.job_id, user.user_id)
        except Exception as exc:
            logger.error("Convex get_analysis (sim) failed: %s", exc)
            raise HTTPException(status_code=502, detail="Failed to load analysis data.")
        if record is None:
            raise HTTPException(status_code=404, detail="Analysis not found")

        result_data = record.get("result", record)
        if isinstance(result_data, str):
            try:
                result_data = json.loads(result_data)
            except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail="Corrupt analysis data")

        rev_sim = result_data.get("revenue_simulation", {})
        base_params = rev_sim.get("defaults", {})

    overrides = req.model_dump(exclude={"job_id"}, exclude_none=True)
    params = {**base_params, **overrides}
    simulation = run_simulation(params)
    return simulation


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    job_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    history: List[ChatMessage] = Field(default_factory=list)


@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, req: ChatRequest, user: AuthUser = Depends(get_current_user)):
    try:
        record = get_analysis(req.job_id, user.user_id)
    except Exception:
        record = None

    report_json = ""
    if record and record.get("result"):
        result_data = record["result"]
        if isinstance(result_data, str):
            report_json = result_data
        else:
            report_json = json.dumps(result_data, indent=2)

    system_prompt = (
        "You are Forma AI, a sharp startup advisor. The user has just "
        "received a business-idea analysis report. Use it as context to "
        "answer follow-up questions with specificity and nuance.\n\n"
        f"FULL REPORT:\n{report_json}\n\n"
        "Be concise, practical, and data-driven. If the report doesn't "
        "cover something, say so honestly."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for m in req.history[-20:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": req.message})

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.5,
        max_tokens=800,
    )
    return {"reply": response.choices[0].message.content}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/config/public")
async def public_config():
    return {
        "supabase_url": SUPABASE_URL,
        "supabase_anon_key": SUPABASE_ANON_KEY,
    }
