import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

from .prompts import SYSTEM_PROMPT, build_user_prompt

load_dotenv()


def _log_prompt_trace(
    url: str,
    system_prompt: str,
    user_prompt: str,
    raw_response: str,
    parsed_response: dict | None,
    model: str,
    duration_ms: float,
) -> str:
    """Save a complete prompt trace. Uses /tmp on serverless platforms."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url_analyzed": url,
        "model": model,
        "duration_ms": round(duration_ms, 2),
        "prompts": {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        },
        "raw_model_output": raw_response,
        "parsed_output": parsed_response,
    }

    try:
        # Try /tmp first (works on Vercel), then local logs/
        for log_dir in [Path("/tmp/logs"), Path("logs")]:
            try:
                log_dir.mkdir(exist_ok=True)
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_")[:50]
                filename = f"{timestamp}_{safe_url}.json"
                log_path = log_dir / filename
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(log_entry, f, indent=2, ensure_ascii=False)
                return str(log_path)
            except OSError:
                continue
    except Exception:
        pass

    return "logs unavailable (read-only filesystem)"


async def analyze_page(metrics: dict) -> dict:
    """Run AI analysis on the scraped metrics."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not found. "
            "Create a .env file with your key. "
            "Get one at https://openrouter.ai/keys"
        )

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    user_prompt = build_user_prompt(metrics)
    model_name = "google/gemini-2.0-flash-001"

    start_time = time.time()

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    duration_ms = (time.time() - start_time) * 1000

    raw_response = response.choices[0].message.content

    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = {
            "error": "Failed to parse AI response as JSON",
            "raw_text": raw_response
        }

    log_path = _log_prompt_trace(
        url=metrics["url"],
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        raw_response=raw_response,
        parsed_response=parsed,
        model=model_name,
        duration_ms=duration_ms,
    )

    usage = response.usage
    token_usage = {
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
        "total_tokens": usage.total_tokens if usage else 0,
    }

    return {
        "ai_insights": parsed,
        "prompt_log_path": log_path,
        "prompt_trace": {
            "system_prompt": SYSTEM_PROMPT,
            "user_prompt": user_prompt,
            "raw_model_output": raw_response,
        },
        "token_usage": token_usage,
    }