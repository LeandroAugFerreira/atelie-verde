"""Tavily first, evidence-aware paid escalation and local contextual synthesis."""

import logging
import re
import time
from dataclasses import asdict
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha256

from . import assistant_installation as installation
from . import assistant_provider as local
from .assistant_budget import Budget
from .assistant_research import cache_get, cache_put
from .assistant_search_providers import (
    AUTHORITIES,
    OpenAIWebSearchProvider,
    SearchBundle,
    SearchResult,
    TavilyProvider,
)
from .assistant_state import SemanticReply
from .business import normalized
from .clock import today

logger = logging.getLogger("rafinha.hybrid")
ATTEMPTED_STATUSES = {
    "found",
    "empty",
    "authentication",
    "quota",
    "timeout",
    "http_error",
    "unavailable",
    "invalid_response",
    "incomplete",
    "response_limit",
}


def authoritative(host):
    return host.endswith((".edu", ".gov", ".gov.br")) or any(
        host == domain or host.endswith("." + domain) for domain in AUTHORITIES
    )


def publisher(host):
    parts = host.split(".")
    return ".".join(parts[-3:] if host.endswith((".gov.br", ".edu.br", ".co.uk")) else parts[-2:])


def deduplicate(bundles):
    results, images = {}, {}
    for bundle in bundles:
        for item in bundle.results:
            if item.url not in results:
                results[item.url] = item
            elif len(item.content) > len(results[item.url].content):
                results[item.url] = item
        for item in bundle.images:
            images.setdefault(item["image_url"], item)
    return list(results.values())[:8], list(images.values())[:3]


def recent_source(row):
    if not row.published_date:
        return False
    try:
        stamp = datetime.fromisoformat(row.published_date.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        try:
            stamp = parsedate_to_datetime(row.published_date)
        except (ValueError, TypeError):
            return False
    return today() - timedelta(days=31) <= stamp.date() <= today()


def quality(results, assessment, identification=False, current=False):
    trusted = {
        publisher(r.domain) for r in results if authoritative(r.domain) and r.content.strip()
    }
    relevant = [r for r in results if r.content.strip() and (r.score is None or r.score >= 0.5)]
    if current and not any(recent_source(row) for row in relevant):
        return "low"
    if not relevant or (assessment and assessment.get("conflicting")):
        return "low"
    if assessment and assessment.get("confidence") == "low":
        return "low"
    if (
        not identification
        and len(trusted) >= 2
        and assessment
        and assessment.get("agrees")
        and assessment.get("sufficient")
        and assessment.get("confidence") == "high"
    ):
        return "high"
    return "medium" if trusted or len(relevant) >= 2 else "low"


def search_query(question, memory, topic):
    from .assistant_routing import public_query

    text = public_query(question)
    if not text:
        return None
    identity = memory.plant_name or memory.identity_hypothesis.get("label", "")
    clues = memory.slots.get("description", "")
    pieces = [public_query(identity) or "", public_query(clues) or "", text]
    # Names and descriptions are reported clues, never an automatic identification.
    return " ".join(dict.fromkeys(p for p in pieces if p))[:450]


def synthesize(question, facts, history, bundles, budget, identification):
    results, images = deduplicate(bundles)
    material = [
        {**asdict(row), "content": row.content[:1500], "snippet": row.snippet[:600]}
        for row in results
    ]
    if not material and not any(bundle.summary for bundle in bundles):
        return None, None, results, images, "low"
    reply, assessment = local.evidence_answer(
        question, facts, history, material, [b.summary[:3500] for b in bundles if b.summary], budget
    )
    confidence = quality(results, assessment, identification, facts["_topic"] == "current")
    return reply, assessment, results, images, confidence


def research_reply(db, question, facts, history, memory, budget, cancelled, progress):
    config = installation.settings()
    query = search_query(question, memory, facts["_topic"])
    if (
        not query
        or not config["search_enabled"]
        or (config["mode"] == "on_request" and not facts["_force_web"])
    ):
        return None, {
            "status": "disabled",
            "reason": "administrator_search_policy",
            "sources": [],
            "images": [],
            "providers": [],
            "confidence": "low",
        }
    identification = bool(facts.get("_identification_lookup"))
    logger.info(
        "[RAF_WEB_QUERY] intent=%s topic=%s query=%s", memory.intent, facts["_topic"], query
    )
    key = sha256(("hybrid-v2|" + normalized(query) + "|" + facts["_topic"]).encode()).hexdigest()
    cached = cache_get(db, key)
    bundles = []
    if cached:
        bundles = [
            SearchBundle(**{**row, "results": [SearchResult(**r) for r in row["results"]]})
            for row in cached.get("bundles", [])
        ]
        for bundle in bundles:
            bundle.cache = "hit"
    else:
        progress("research")
        tavily = TavilyProvider()
        bundle = tavily.search(
            query,
            facts["_topic"],
            Budget(min(8, max(0.1, budget.remaining() - 7)), time.monotonic()),
            config["images"] and identification,
            cancelled,
        )
        bundles.append(bundle)
    if cancelled():
        return None, {
            "status": "cancelled",
            "sources": [],
            "images": [],
            "providers": [],
            "confidence": "low",
        }
    paid = OpenAIWebSearchProvider()
    progress("model")
    local_seconds = (
        min(9, max(0.1, budget.remaining() - 9))
        if paid.available() and not cached
        else budget.remaining()
    )
    reply, assessment, results, images, confidence = synthesize(
        question, facts, history, bundles, Budget(local_seconds, time.monotonic()), identification
    )
    topic = facts["_topic"]
    risk = topic in {"toxicity", "pesticides", "current"}
    explicit_verify = bool(
        re.search(
            r"\b(?:confirme|confirmar|verifique|cruze|contraditor\w*|discord\w*)\b",
            normalized(question),
        )
    )
    weak = not any(r.content.strip() and (r.score is None or r.score >= 0.45) for r in results)
    needs_more = (
        weak
        or bool(assessment and not assessment.get("sufficient"))
        or bool(assessment and assessment.get("conflicting"))
    )
    verify = (
        config["mode"] == "important_double" and risk and confidence != "high"
    ) or explicit_verify
    reason = (
        "no_primary_evidence"
        if weak
        else "conflicting_sources"
        if assessment and assessment.get("conflicting")
        else "important_verification"
        if verify
        else "insufficient_evidence"
    )
    if (
        not any(b.provider == "openai" and b.status in ATTEMPTED_STATUSES for b in bundles)
        and paid.available()
        and (needs_more or verify)
        and confidence != "high"
        and budget.remaining() > 3
        and not cancelled()
    ):
        logger.info("[RAF_ESCALATION] reason=%s confidence=%s", reason, confidence)
        progress("research")
        extra = paid.search(
            query,
            topic,
            Budget(min(12, max(0.1, budget.remaining() - 3)), time.monotonic()),
            config["images"] and identification,
            cancelled,
        )
        bundles.append(extra)
        if extra.status == "found" and not cancelled():
            progress("model")
            candidate_reply, candidate_assessment, results, images, confidence = synthesize(
                question,
                facts,
                history,
                bundles,
                Budget(max(0.1, budget.remaining()), time.monotonic()),
                identification,
            )
            reply = candidate_reply or reply
            assessment = candidate_assessment or assessment
    sources = [
        {
            "title": r.title,
            "url": r.url,
            "domain": r.domain,
            "snippet": r.snippet[:600],
            "provider": r.provider,
            "score": r.score,
        }
        for r in results
    ]
    searched = any(bundle.status == "found" for bundle in bundles) and bool(results)
    status = (
        "found"
        if searched
        else "not_configured"
        if all(b.status in {"not_configured", "paid_not_authorized"} for b in bundles)
        else "unavailable"
    )
    attempted = [bundle for bundle in bundles if bundle.status in ATTEMPTED_STATUSES]
    if attempted and (not cached or len(bundles) > len(cached.get("bundles", []))):
        paid_failed = any(
            bundle.provider == "openai" and bundle.status != "found" for bundle in attempted
        )
        cache_put(
            db,
            key,
            {"bundles": [b.data() for b in attempted]},
            300 if paid_failed or not searched else 900 if topic == "current" else 86400,
        )
    if not reply and searched:
        # A local outage never turns snippets into an unqualified copied answer.
        reply = SemanticReply(
            text="Encontrei referências relacionadas à sua dúvida, mas ainda não consegui concluir uma orientação segura a partir delas. Vou manter essas fontes para continuarmos com o que você relatou. Como a planta está agora?"
        )
        reply._provider = "catalog"
    if reply and searched:
        reply._searched_web = True
        reply._sources = sources
        reply._images = images
        candidate = (assessment or {}).get("candidate", "")
        corpora = [normalized(r.title + " " + r.content) for r in results]
        candidate_words = re.findall(r"[a-z]+", normalized(candidate))
        scientific = re.match(r"^[A-Z][a-z]{2,}\s+[a-z-]{3,}", candidate)
        if (
            identification
            and scientific
            and candidate_words
            and any(
                normalized(scientific.group()) in corpus
                and all(word in corpus for word in candidate_words)
                for corpus in corpora
            )
        ):
            reply._hypothesis = {
                "label": candidate[:180],
                "status": "hypothesis",
                "confidence": "medium" if confidence != "low" else "low",
                "sources": sources[:5],
            }
        if (
            confidence == "low"
            and (assessment or {}).get("conflicting")
            and "diverg" not in normalized(reply.text)
        ):
            reply.text = (
                "As referências apresentam divergências; ainda não há uma conclusão segura.\n\n"
                + reply.text
            )
    metadata = {
        "status": status,
        "reason": reason if len(bundles) > 1 else "tavily_first",
        "sources": sources,
        "images": images,
        "providers": [
            {"provider": b.provider, "status": b.status, "cache": b.cache} for b in bundles
        ],
        "confidence": confidence,
        "cache": "hit" if cached else "miss",
        "conflicting": bool(assessment and assessment.get("conflicting")),
    }
    logger.info("[RAF_HYBRID] results=%s confidence=%s status=%s", len(results), confidence, status)
    return reply, metadata
