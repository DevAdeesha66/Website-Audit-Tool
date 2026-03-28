# Website Audit Tool

An AI-powered single-page website analysis tool that extracts factual metrics and generates structured insights using Google Gemini.

Built for the **EIGHT25MEDIA AI-Native Software Engineer** assessment.

---

## Quick Start

### Prerequisites
- Python 3.10+
- - An OpenRouter API key ([get one here](https://openrouter.ai/keys))

### Setup
```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/website-audit-tool.git
cd website-audit-tool

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
copy .env.example .env
# Then edit .env and paste your OPENROUTER_API_KEY

# 5. Run the server
python -m uvicorn api.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Architecture Overview
```
Frontend (templates/index.html)
        │
        ▼ POST /analyze {url}
API Layer (api/main.py) — FastAPI, thin routing only
        │
   ┌────┴────┐
   ▼         ▼
Scraper    AI Engine
scraper/   ai_engine/
           prompts.py + analyzer.py
           Gemini API
                │
                ▼
          Prompt Logs (logs/*.json)
```

### Key Principle: Clean Separation

- **Scraper** (`scraper/extractor.py`): Takes a URL, returns a PageMetrics dataclass. Has zero knowledge of AI.
- **AI Engine** (`ai_engine/`): Takes a metrics dictionary, returns structured insights. Has zero knowledge of HTML parsing.
- **API Layer** (`api/main.py`): Thin glue that calls scraper then AI engine. Contains no business logic.

---

## AI Design Decisions

### Prompt Architecture
- System prompt establishes a "senior web strategist" persona
- Enforces strict JSON output schema directly in the prompt
- Rules like "every insight must reference specific numbers" prevent generic outputs

### Grounding AI in Factual Data
- System prompt requires every finding to cite specific numbers
- Metrics are presented in structured, labelled format
- Recommendations must include a metric_reference field

### Prompt Logging
Every API call saves a complete trace to logs/ including system prompt, user prompt, raw response, parsed output, and timing.

---

## Trade-offs

| Decision | Trade-off |
|---|---|
| httpx over Playwright | Faster but can't handle JS-rendered SPAs |
| BeautifulSoup over lxml | Slower but more forgiving with malformed HTML |
| Single API call | Simpler but multi-call could produce deeper analysis |
| Prompt-based JSON | Relies on Gemini following schema, includes fallback |
| Content truncation at 3000 words | Prevents token limits but may miss bottom content |

---

## What I'd Improve With More Time

1. Playwright fallback for JavaScript-heavy SPAs
2. Multipass AI analysis with specialized prompts per category
4. Competitive benchmarking against industry averages
5. Historical tracking to show improvement over time
6. Export to PDF for shareable audit reports


---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Backend | FastAPI (Python) | Async, auto-docs, fast development |
| Scraping | BeautifulSoup + httpx | Lightweight, handles most marketing sites |
| AI | Google Gemini API | Free tier, fast responses, reliable structured output |
| Frontend | Vanilla HTML/CSS/JS | Zero build step, instant setup |

