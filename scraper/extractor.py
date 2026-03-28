import re
import asyncio
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass, asdict
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Comment



@dataclass
class PageMetrics:

    url: str
    meta_title: Optional[str]
    meta_description: Optional[str]
    word_count: int
    heading_counts: dict
    headings_detail: list
    cta_count: int
    cta_details: list
    internal_links: int
    external_links: int
    total_images: int
    images_missing_alt: int
    images_missing_alt_pct: float
    content_summary: str

    def to_dict(self) -> dict:
        return asdict(self)




async def fetch_page(url: str) -> str:

    try:
        html = await _fetch_with_httpx(url)
        return html
    except (httpx.HTTPStatusError, httpx.ConnectError):
        pass

    return await _fetch_with_playwright(url)


async def _fetch_with_httpx(url: str) -> str:
 
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
    }

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=15.0,
        verify=False,
    ) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.text


def _playwright_sync_fetch(url: str) -> str:
  
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()
        return html


async def _fetch_with_playwright(url: str) -> str:

    loop = asyncio.get_event_loop()
    html = await loop.run_in_executor(None, _playwright_sync_fetch, url)
    return html



def _get_visible_text(soup: BeautifulSoup) -> str:

    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_meta(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:

    title_tag = soup.find("title")
    meta_title_tag = soup.find("meta", attrs={"name": "title"})
    og_title_tag = soup.find("meta", attrs={"property": "og:title"})

    title = None
    if title_tag and title_tag.string:
        title = title_tag.string.strip()
    elif meta_title_tag:
        title = meta_title_tag.get("content", "").strip()
    elif og_title_tag:
        title = og_title_tag.get("content", "").strip()

    desc_tag = soup.find("meta", attrs={"name": "description"})
    og_desc_tag = soup.find("meta", attrs={"property": "og:description"})

    description = None
    if desc_tag:
        description = desc_tag.get("content", "").strip()
    elif og_desc_tag:
        description = og_desc_tag.get("content", "").strip()

    return title, description


def _extract_headings(soup: BeautifulSoup) -> tuple[dict, list]:

    counts = {"h1": 0, "h2": 0, "h3": 0}
    details = []

    for level in ["h1", "h2", "h3"]:
        headings = soup.find_all(level)
        counts[level] = len(headings)
        for h in headings:
            text = h.get_text(strip=True)
            if text:
                details.append({"tag": level, "text": text})

    return counts, details


def _extract_ctas(soup: BeautifulSoup) -> tuple[int, list]:

    ctas = []
    seen_texts = set()

    for btn in soup.find_all("button"):
        text = btn.get_text(strip=True)
        if text and text.lower() not in seen_texts:
            seen_texts.add(text.lower())
            ctas.append({"type": "button", "text": text})

    cta_patterns = re.compile(r"btn|button|cta|action|hero", re.I)
    for link in soup.find_all("a"):
        classes = " ".join(link.get("class", []))
        link_id = link.get("id", "")
        role = link.get("role", "")

        if (cta_patterns.search(classes) or
            cta_patterns.search(link_id) or
            role == "button"):
            text = link.get_text(strip=True)
            if text and text.lower() not in seen_texts:
                seen_texts.add(text.lower())
                ctas.append({"type": "link_button", "text": text})

    action_phrases = [
        "get started", "sign up", "try", "start", "buy",
        "subscribe", "download", "contact", "request",
        "book", "schedule", "demo", "free trial", "learn more",
        "join", "register", "apply", "shop now", "order"
    ]
    for link in soup.find_all("a"):
        text = link.get_text(strip=True).lower()
        if text and text not in seen_texts:
            if any(phrase in text for phrase in action_phrases):
                seen_texts.add(text)
                ctas.append({"type": "action_link", "text": link.get_text(strip=True)})

    return len(ctas), ctas


def _extract_links(soup: BeautifulSoup, base_url: str) -> tuple[int, int]:
    
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc.lower()

    internal = 0
    external = 0

    for link in soup.find_all("a", href=True):
        href = link["href"].strip()

        if href.startswith(("#", "javascript:", "data:")):
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        if parsed.netloc.lower() == base_domain:
            internal += 1
        else:
            external += 1

    return internal, external


def _extract_images(soup: BeautifulSoup) -> tuple[int, int, float]:

    images = soup.find_all("img")
    total = len(images)

    missing_alt = 0
    for img in images:
        alt = img.get("alt")
        if alt is None or alt.strip() == "":
            missing_alt += 1

    pct = (missing_alt / total * 100) if total > 0 else 0.0
    return total, missing_alt, round(pct, 1)




async def extract_metrics(url: str) -> PageMetrics:
    #fetch a page and extract all metrics
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    html = await fetch_page(url)
    soup = BeautifulSoup(html, "html.parser")

    meta_title, meta_description = _extract_meta(soup)
    heading_counts, headings_detail = _extract_headings(soup)
    cta_count, cta_details = _extract_ctas(soup)
    internal_links, external_links = _extract_links(soup, url)
    total_images, images_missing_alt, pct = _extract_images(soup)

    visible_text = _get_visible_text(soup)
    word_count = len(visible_text.split())

    words = visible_text.split()
    content_summary = " ".join(words[:3000])
    if len(words) > 3000:
        content_summary += " [TRUNCATED]"

    return PageMetrics(
        url=url,
        meta_title=meta_title,
        meta_description=meta_description,
        word_count=word_count,
        heading_counts=heading_counts,
        headings_detail=headings_detail,
        cta_count=cta_count,
        cta_details=cta_details,
        internal_links=internal_links,
        external_links=external_links,
        total_images=total_images,
        images_missing_alt=images_missing_alt,
        images_missing_alt_pct=pct,
        content_summary=content_summary,
    )