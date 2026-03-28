"""
Prompt Design — Website Audit Tool
====================================
All LLM prompts live here, separate from the API orchestration.
This makes prompts easy to iterate on, review, and log.
"""


SYSTEM_PROMPT = """You are a senior web strategist at a digital agency that builds 
high-performing marketing websites. You specialize in SEO, conversion optimization, 
content strategy, and UX.

You are analyzing a webpage audit report. You will receive:
1. Factual metrics extracted from the page (word count, headings, CTAs, links, images, meta tags)
2. The actual text content of the page

Your job is to produce a structured analysis with actionable insights.

RULES:
- Every insight MUST reference specific numbers from the metrics
- Do NOT give generic advice like "improve your SEO" — be specific
- Compare metrics against industry best practices where relevant
- Be direct and concise — this is for a professional web team
- Focus on what matters most for conversion and SEO performance

You MUST respond with valid JSON only. No markdown, no extra text.
Use this exact structure:

{
  "seo_analysis": {
    "score": "good|needs_work|poor",
    "findings": ["specific finding referencing metrics..."]
  },
  "messaging_clarity": {
    "score": "good|needs_work|poor",
    "findings": ["specific finding..."]
  },
  "cta_analysis": {
    "score": "good|needs_work|poor",
    "findings": ["specific finding..."]
  },
  "content_depth": {
    "score": "good|needs_work|poor",
    "findings": ["specific finding..."]
  },
  "ux_concerns": {
    "score": "good|needs_work|poor",
    "findings": ["specific finding..."]
  },
  "recommendations": [
    {
      "priority": 1,
      "title": "short title",
      "description": "what to do and why",
      "metric_reference": "which metric this is based on"
    }
  ]
}

The recommendations array must contain 3 to 5 items, sorted by priority (1 = most important).
Each recommendation must tie back to a specific metric from the audit data."""


def build_user_prompt(metrics: dict) -> str:
    """Build the user prompt by injecting scraped metrics."""
    
    headings_text = ""
    for h in metrics.get("headings_detail", []):
        headings_text += f"  - [{h['tag'].upper()}] {h['text']}\n"
    
    if not headings_text:
        headings_text = "  (no headings found)\n"
    
    ctas_text = ""
    for cta in metrics.get("cta_details", []):
        ctas_text += f"  - [{cta['type']}] \"{cta['text']}\"\n"
    
    if not ctas_text:
        ctas_text = "  (no CTAs detected)\n"

    prompt = f"""Analyze this webpage and provide your assessment as JSON.

<url>{metrics['url']}</url>

<metrics>
META TITLE: {metrics.get('meta_title') or '(missing)'}
META DESCRIPTION: {metrics.get('meta_description') or '(missing)'}

WORD COUNT: {metrics['word_count']}

HEADING STRUCTURE:
  H1 tags: {metrics['heading_counts']['h1']}
  H2 tags: {metrics['heading_counts']['h2']}
  H3 tags: {metrics['heading_counts']['h3']}

HEADINGS FOUND:
{headings_text}
CALL-TO-ACTION ELEMENTS: {metrics['cta_count']}
{ctas_text}
LINKS:
  Internal links: {metrics['internal_links']}
  External links: {metrics['external_links']}

IMAGES:
  Total images: {metrics['total_images']}
  Missing alt text: {metrics['images_missing_alt']} ({metrics['images_missing_alt_pct']}%)
</metrics>

<page_content>
{metrics.get('content_summary', '(no content extracted)')}
</page_content>

Respond with JSON only. No markdown formatting, no code fences."""

    return prompt