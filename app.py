"""
ResolveIQ - Main Application Entrypoint.
Track 4: GenAI Resolution Assistant for Broadband & Mobile ISPs.
Starts backend and frontend together on http://localhost:8000.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from resolveiq.config import settings, STATIC_DIR
from resolveiq.knowledge import knowledge_base
from resolveiq.accounts import account_repo
from resolveiq.validator import fact_validator, ValidationResult
from resolveiq.resolver import resolution_engine, ResolutionResponse

app = FastAPI(
    title="ResolveIQ - Customer Support Resolution Assistant",
    description="Track 4 Hackathon Submission: AI Resolution Assistant for Broadband & Mobile ISPs",
    version="1.0.0"
)

# Ensure static directory exists
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ResolveRequest(BaseModel):
    conversation_id: Optional[str] = None
    account_id: Optional[str] = None
    custom_message: Optional[str] = None
    force_mode: Optional[str] = None


class ValidateRequest(BaseModel):
    draft_text: str
    account_id: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4


@app.get("/")
async def serve_index():
    """Serve the single-page application frontend."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse({
            "app": settings.app_name,
            "track": settings.track,
            "status": "online",
            "message": "ResolveIQ backend online. Frontend index.html loading."
        })
    return FileResponse(str(index_file))


@app.get("/api/health")
async def get_health():
    """Service health check and configuration telemetry."""
    has_api_key = bool(os.getenv("GEMINI_API_KEY") or settings.gemini_api_key)
    return {
        "status": "healthy",
        "app": settings.app_name,
        "track": settings.track,
        "isp": settings.isp_brand,
        "gemini_api_key_configured": has_api_key,
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
        "total_articles": len(knowledge_base.article_list),
        "total_accounts": len(account_repo.list_accounts()),
        "total_sample_conversations": len(account_repo.list_conversations())
    }


@app.get("/api/scenarios")
async def list_scenarios():
    """List sample conversations with metadata for quick-switching."""
    convs = account_repo.list_conversations()
    scenarios = []
    for c in convs:
        acc = account_repo.get_account(c.get("account_id", ""))
        scenarios.append({
            "conversation_id": c.get("conversation_id"),
            "customer_name": c.get("customer_name"),
            "title": c.get("title"),
            "summary": c.get("summary"),
            "expected_mode": c.get("expected_mode"),
            "account_id": c.get("account_id"),
            "service_plan": acc.get("service_plan") if acc else "Unknown",
            "target_kb": c.get("target_kb")
        })
    return scenarios


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Retrieve full conversation and matched account record."""
    conv = account_repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    acc = account_repo.get_account(conv.get("account_id", ""))
    return {
        "conversation": conv,
        "account": acc
    }


@app.get("/api/accounts")
async def list_accounts():
    """List all customer account records."""
    return account_repo.list_accounts()


@app.get("/api/accounts/{account_id}")
async def get_account(account_id: str):
    """Retrieve single customer account record."""
    acc = account_repo.get_account(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found")
    return acc


@app.get("/api/articles")
async def list_articles():
    """List all support articles with citable IDs."""
    return knowledge_base.list_all_articles()


@app.get("/api/articles/{article_id}")
async def get_article(article_id: str):
    """Retrieve single support article by ID."""
    art = knowledge_base.get_article(article_id)
    if not art:
        raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found")
    return art


@app.post("/api/search")
async def search_articles(req: SearchRequest):
    """Semantic vector search across knowledge base articles."""
    results = knowledge_base.search(req.query, top_k=req.top_k)
    return {
        "query": req.query,
        "results": results
    }


@app.post("/api/resolve")
async def resolve_issue(req: ResolveRequest):
    """Draft resolution or handover summary, citing articles and validating facts."""
    conversation = None
    account_record = None

    if req.conversation_id:
        conversation = account_repo.get_conversation(req.conversation_id)
        if conversation:
            acc_id = req.account_id or conversation.get("account_id")
            account_record = account_repo.get_account(acc_id)

    if not account_record and req.account_id:
        account_record = account_repo.get_account(req.account_id)

    if not account_record:
        # Default to first account if unspecified
        accounts = account_repo.list_accounts()
        account_record = accounts[0] if accounts else {}

    if not conversation:
        # Build ad-hoc conversation from custom_message
        msg = req.custom_message or "I have an issue with my service."
        conversation = {
            "conversation_id": "CUSTOM-CONV",
            "account_id": account_record.get("account_id", ""),
            "customer_name": account_record.get("customer_name", "Customer"),
            "title": "Ad-hoc Support Request",
            "messages": [
                {
                    "sender": "customer",
                    "content": msg,
                    "timestamp": "2026-09-05T12:00:00+05:30"
                }
            ]
        }
    elif req.custom_message:
        # Append additional custom message if provided
        conversation = dict(conversation)
        msgs = list(conversation.get("messages", []))
        msgs.append({
            "sender": "customer",
            "content": req.custom_message,
            "timestamp": "2026-09-05T12:00:00+05:30"
        })
        conversation["messages"] = msgs

    response = resolution_engine.resolve(
        conversation=conversation,
        account_record=account_record,
        force_mode=req.force_mode
    )

    return {
        "conversation_id": conversation.get("conversation_id"),
        "account_id": account_record.get("account_id"),
        "resolution": response.model_dump()
    }


@app.post("/api/validate")
async def validate_draft(req: ValidateRequest):
    """Standalone endpoint for running the Fact Validation Engine on draft text."""
    acc = account_repo.get_account(req.account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=f"Account '{req.account_id}' not found")

    result = fact_validator.validate(req.draft_text, acc)
    return result.model_dump()


if __name__ == "__main__":
    print(f"Starting {settings.app_name} on http://localhost:{settings.port} ...")
    uvicorn.run(app, host="0.0.0.0", port=settings.port, log_level="info")
