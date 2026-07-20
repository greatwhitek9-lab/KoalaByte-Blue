from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

import httpx

DEFAULT_TRACE_DIR = Path("logs/killerkoala/web_research")
DEFAULT_TIMEOUT_SECONDS = 6.0
DEFAULT_MAX_RESULTS = 5
DEFAULT_MAX_CONTEXT_CHARS = 6000

QUESTION_PREFIXES = (
    "who ", "what ", "when ", "where ", "why ", "how ", "which ",
    "is ", "are ", "was ", "were ", "do ", "does ", "did ", "can ",
    "could ", "would ", "should ", "will ", "tell me ", "explain ",
    "look up ", "search for ", "find out ", "give me information ",
)
FRESHNESS_TERMS = (
    "latest", "current", "currently", "today", "tonight", "tomorrow",
    "yesterday", "recent", "newest", "this week", "this month", "this year",
    "price", "weather", "forecast", "score", "schedule", "news", "update",
    "president", "prime minister", "ceo", "release", "version",
)


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str
    snippet: str
    provider: str


@dataclass
class WebResearchResult:
    question: str
    searched: bool
    internet_available: bool
    provider: str = "none"
    sources: list[ResearchSource] = field(default_factory=list)
    context: str = ""
    error: str = ""
    generated_at: float = 0.0
    artifact_path: str = ""


def _mode() -> str:
    return os.getenv("KILLERKOALA_WEB_SEARCH", "auto").strip().lower()


def clean_question(text: str) -> str:
    cleaned = re.sub(r"\bkiller\s*koala\b", " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bkillerkoala\b", " ", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.replace("\n", " ").split()).strip(" ,:;-?")


def looks_like_general_question(text: str) -> bool:
    question = clean_question(text).lower()
    if not question:
        return False
    if text.strip().endswith("?"):
        return True
    return question.startswith(QUESTION_PREFIXES) or any(
        token in question for token in ("look up", "search the web", "search online", "find out")
    )


def question_needs_web(text: str) -> bool:
    mode = _mode()
    if mode in {"0", "off", "false", "disabled", "never"}:
        return False
    if mode in {"1", "on", "true", "always"}:
        return bool(clean_question(text))
    question = clean_question(text).lower()
    if not question:
        return False
    return looks_like_general_question(text) or any(term in question for term in FRESHNESS_TERMS)


def _trim(text: Any, limit: int = 900) -> str:
    cleaned = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
    return cleaned[:limit].rstrip()


def _dedupe(sources: Iterable[ResearchSource], limit: int) -> list[ResearchSource]:
    result: list[ResearchSource] = []
    seen: set[str] = set()
    for source in sources:
        key = (source.url or source.title).strip().lower()
        if not key or key in seen or not source.snippet:
            continue
        seen.add(key)
        result.append(source)
        if len(result) >= limit:
            break
    return result


def _brave_search(client: httpx.Client, query: str, limit: int) -> list[ResearchSource]:
    api_key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not api_key:
        return []
    response = client.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": limit, "search_lang": "en", "safesearch": "moderate"},
        headers={"Accept": "application/json", "X-Subscription-Token": api_key},
    )
    response.raise_for_status()
    rows = response.json().get("web", {}).get("results", [])
    return [
        ResearchSource(
            title=_trim(row.get("title"), 180),
            url=_trim(row.get("url"), 500),
            snippet=_trim(row.get("description"), 1100),
            provider="brave",
        )
        for row in rows
        if isinstance(row, dict)
    ]


def _flatten_related(rows: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return found
    for row in rows:
        if not isinstance(row, dict):
            continue
        if isinstance(row.get("Topics"), list):
            found.extend(_flatten_related(row["Topics"]))
        elif row.get("Text"):
            found.append(row)
    return found


def _duckduckgo_instant(client: httpx.Client, query: str, limit: int) -> list[ResearchSource]:
    response = client.get(
        "https://api.duckduckgo.com/",
        params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1, "skip_disambig": 0},
        headers={"User-Agent": "KoalaByte-Blue/1.0 local-companion"},
    )
    response.raise_for_status()
    data = response.json()
    sources: list[ResearchSource] = []
    abstract = _trim(data.get("AbstractText"), 1200)
    if abstract:
        sources.append(
            ResearchSource(
                title=_trim(data.get("Heading") or "DuckDuckGo Instant Answer", 180),
                url=_trim(data.get("AbstractURL"), 500),
                snippet=abstract,
                provider="duckduckgo",
            )
        )
    answer = _trim(data.get("Answer") or data.get("Definition"), 900)
    if answer:
        sources.append(
            ResearchSource(
                title="DuckDuckGo answer",
                url=_trim(data.get("DefinitionURL") or data.get("AbstractURL"), 500),
                snippet=answer,
                provider="duckduckgo",
            )
        )
    for row in _flatten_related(data.get("RelatedTopics")):
        sources.append(
            ResearchSource(
                title=_trim(row.get("Text"), 180),
                url=_trim(row.get("FirstURL"), 500),
                snippet=_trim(row.get("Text"), 900),
                provider="duckduckgo",
            )
        )
        if len(sources) >= limit:
            break
    return sources


def _wikipedia_search(client: httpx.Client, query: str, limit: int) -> list[ResearchSource]:
    response = client.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": min(limit, 5),
            "prop": "extracts|info",
            "exintro": 1,
            "explaintext": 1,
            "inprop": "url",
            "format": "json",
            "origin": "*",
        },
        headers={"User-Agent": "KoalaByte-Blue/1.0 local-companion"},
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    ordered = sorted(
        (row for row in pages.values() if isinstance(row, dict)),
        key=lambda row: int(row.get("index", 9999)),
    )
    return [
        ResearchSource(
            title=_trim(row.get("title"), 180),
            url=_trim(row.get("fullurl"), 500),
            snippet=_trim(row.get("extract"), 1300),
            provider="wikipedia",
        )
        for row in ordered
        if row.get("extract")
    ]


def _build_context(sources: list[ResearchSource], max_chars: int) -> str:
    blocks: list[str] = []
    for index, source in enumerate(sources, 1):
        blocks.append(f"[{index}] {source.title}\n{source.snippet}\nSource: {source.url}")
    return "\n\n".join(blocks)[:max_chars].rstrip()


def _write_trace(result: WebResearchResult, trace_dir: str | Path) -> str:
    root = Path(trace_dir)
    root.mkdir(parents=True, exist_ok=True)
    payload = asdict(result)
    timestamped = root / f"research_{int(result.generated_at)}.json"
    latest = root / "latest.json"
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    timestamped.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    return str(timestamped)


def research_question(
    text: str,
    *,
    trace_dir: str | Path = DEFAULT_TRACE_DIR,
    max_results: int = DEFAULT_MAX_RESULTS,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> WebResearchResult:
    question = clean_question(text)
    result = WebResearchResult(
        question=question,
        searched=False,
        internet_available=False,
        generated_at=time.time(),
    )
    if not question_needs_web(question):
        result.artifact_path = _write_trace(result, trace_dir)
        return result

    timeout = float(os.getenv("KILLERKOALA_WEB_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    providers: list[str] = []
    sources: list[ResearchSource] = []
    errors: list[str] = []
    result.searched = True

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        if os.getenv("BRAVE_SEARCH_API_KEY", "").strip():
            try:
                brave = _brave_search(client, question, max_results)
                result.internet_available = True
                if brave:
                    providers.append("brave")
                    sources.extend(brave)
            except Exception as exc:
                errors.append(f"brave: {exc}")

        try:
            ddg = _duckduckgo_instant(client, question, max_results)
            result.internet_available = True
            if ddg:
                providers.append("duckduckgo")
                sources.extend(ddg)
        except Exception as exc:
            errors.append(f"duckduckgo: {exc}")

        if len(_dedupe(sources, max_results)) < max_results:
            try:
                wiki = _wikipedia_search(client, question, max_results)
                result.internet_available = True
                if wiki:
                    providers.append("wikipedia")
                    sources.extend(wiki)
            except Exception as exc:
                errors.append(f"wikipedia: {exc}")

    result.sources = _dedupe(sources, max_results)
    result.provider = "+".join(dict.fromkeys(providers)) if providers else "none"
    result.context = _build_context(result.sources, max_context_chars)
    result.error = "; ".join(errors)[:1200]
    result.artifact_path = _write_trace(result, trace_dir)
    return result
