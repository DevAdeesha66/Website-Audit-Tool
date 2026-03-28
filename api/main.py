
#Website Audit Tool


import os
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Fix paths for Vercel serverless environment
BASE_DIR = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(BASE_DIR))

from scraper.extractor import extract_metrics
from ai_engine.analyzer import analyze_page

app = FastAPI(
    title="Website Audit Tool",
    description="AI-powered single-page website analysis tool",
    version="1.0.0",
)

static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(templates_dir))


class AuditRequest(BaseModel):
    url: str

class PromptTrace(BaseModel):
    system_prompt: str
    user_prompt: str
    raw_model_output: str

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class AuditResponse(BaseModel):
    success: bool
    url: str
    metrics: dict
    ai_insights: dict
    prompt_log_path: str
    prompt_trace: PromptTrace
    token_usage: TokenUsage


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/analyze", response_model=AuditResponse)
async def analyze(req: AuditRequest):
    try:
        page_metrics = await extract_metrics(req.url)
        metrics_dict = page_metrics.to_dict()
        
        ai_result = await analyze_page(metrics_dict)
        
        return AuditResponse(
            success=True,
            url=page_metrics.url,
            metrics=metrics_dict,
            ai_insights=ai_result["ai_insights"],
            prompt_log_path=ai_result["prompt_log_path"],
            prompt_trace=ai_result["prompt_trace"],
            token_usage=ai_result["token_usage"],
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Audit failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
