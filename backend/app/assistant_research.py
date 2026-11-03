"""Bounded institutional discovery. No search-engine HTML scraping or commercial queries."""

import asyncio
import hashlib
import ipaddress
import logging
import os
import re
import socket
import threading
import time
from datetime import date, timedelta
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from .business import normalized
from .clock import today
from .models import AssistantResearchCache

logger = logging.getLogger("rafinha.research")
TRUSTED = {
    "plants.ces.ncsu.edu",
    "rhs.org.uk",
    "kew.org",
    "missouribotanicalgarden.org",
    "embrapa.br",
    "aspca.org",
    "extension.umn.edu",
    "extension.psu.edu",
    "ufl.edu",
}
TOPICS = {
    "propagation": ["propagation", "cutting", "seed", "division"],
    "substrate": ["soil", "drainage", "substrate"],
    "pruning": ["prune", "pruning", "cut"],
    "season": ["season", "pruning", "winter", "spring"],
    "pesticides": ["pesticide", "disease", "control", "safety"],
    "current": ["disease", "current", "outbreak", "recent"],
    "watering": ["water", "moist", "drain"],
    "lighting": ["light", "sun", "shade"],
    "toxicity": ["poison", "toxic", "pet", "cat", "dog"],
    "problem": ["disease", "pest", "leaf", "leaves", "water"],
    "plant_care": ["water", "light", "soil", "care", "grow"],
}
# Common-name resolution points to a botanical group, never a cultivar diagnosis.
# Genus reference: https://plants.ces.ncsu.edu/plants/rosa/
BOTANICAL_NAMES = {"roseira": "Rosa", "roseiras": "Rosa"}
HEADERS = {
    "User-Agent": "AtelieVerdeBotanicalResearch/1.0 (local gardening assistant)",
    "Accept": "application/json, text/html, application/xml",
}


def trusted_url(url):
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and not parsed.username
        and not parsed.password
        and parsed.port in {None, 443}
        and bool(parsed.hostname)
        and any(parsed.hostname == host or parsed.hostname.endswith("." + host) for host in TRUSTED)
    )


def public_host(url):
    try:
        addresses = socket.getaddrinfo(urlparse(url).hostname, 443, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)
    except (OSError, ValueError):
        return False


async def resolve_public(url, seconds):
    # DNS runs in a daemon worker; a failed resolver cannot delay asyncio.run shutdown.
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    def finish(value):
        if not future.done():
            future.set_result(value)

    def worker():
        value = public_host(url)
        if not loop.is_closed():
            try:
                loop.call_soon_threadsafe(finish, value)
            except RuntimeError:
                pass

    threading.Thread(target=worker, daemon=True).start()
    return await asyncio.wait_for(future, timeout=min(1, seconds))


def canonical(species, topic):
    return hashlib.sha256(f"{normalized(species)}|{topic}".encode()).hexdigest()


def rank_sources(results, species):
    tokens = normalized(species).split()
    ranked = sorted(
        (r for r in results if trusted_url(r.get("url", ""))),
        key=lambda r: sum(t in normalized(r.get("title", "") + " " + r["url"]) for t in tokens),
        reverse=True,
    )
    selected = []
    publishers = set()
    for row in ranked:
        host = urlparse(row["url"]).hostname
        publisher = next((p for p in TRUSTED if host == p or host.endswith("." + p)), host)
        if publisher in publishers:
            continue
        publishers.add(publisher)
        selected.append(row)
        if len(selected) == 2:
            break
    return selected


def cache_get(db, key):
    row = db.get(AssistantResearchCache, key)
    return row.value if row and row.expires_at > time.time() else None


def cache_put(db, key, value, ttl=86400):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    db.execute(
        insert(AssistantResearchCache)
        .values(key=key, value=value, expires_at=time.time() + ttl)
        .on_conflict_do_update(
            index_elements=["key"], set_={"value": value, "expires_at": time.time() + ttl}
        )
    )
    # Cache transactions contain only public botanical material, not conversation state.
    db.commit()


async def fetch(url, seconds, limit=1000000):
    if not trusted_url(url) or seconds <= 0:
        raise ValueError("Fonte não autorizada.")
    if not await resolve_public(url, seconds):
        raise ValueError("Destino de rede não autorizado.")
    async with asyncio.timeout(seconds):
        async with httpx.AsyncClient(
            timeout=seconds, follow_redirects=False, trust_env=False, headers=HEADERS
        ) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                if response.status_code >= 300:
                    raise ValueError("Redirecionamento não seguido.")
                if not any(
                    t in response.headers.get("content-type", "") for t in ["html", "xml", "json"]
                ):
                    raise ValueError("Conteúdo não textual.")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > limit:
                        raise ValueError("Fonte excede o limite.")
                return bytes(body)


class SearchProvider(Protocol):
    async def search(self, species: str, topic: str, db, seconds: float) -> list[dict]: ...


class InstitutionalIndexProvider:
    """Search a standard public XML index instead of scraping a search-engine page."""

    async def search(self, species, topic, db, seconds):
        key = canonical("ncstate-sitemap", "index")
        index = cache_get(db, key)
        if not index:
            xml = await fetch("https://plants.ces.ncsu.edu/sitemap.xml", seconds, 2500000)
            if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
                raise ValueError("XML não permitido.")
            root = ElementTree.fromstring(xml)
            urls = [
                e.text
                for e in root.iter()
                if e.tag.endswith("}loc")
                and e.text
                and "/plants/" in e.text
                and trusted_url(e.text)
            ]
            index = {"urls": urls}
            cache_put(db, key, index)
        lookup = BOTANICAL_NAMES.get(normalized(species), species)
        words = normalized(lookup).replace(" ", "-")
        exact = [u for u in index["urls"] if urlparse(u).path.rstrip("/").split("/")[-1] == words]
        # Synonyms are looked up through public taxonomy references, not inferred as an identity.
        if not exact and " " in normalized(lookup):
            epithet = normalized(lookup).split()[-1]
            exact = [
                u
                for u in index["urls"]
                if urlparse(u).path.rstrip("/").split("/")[-1].endswith("-" + epithet)
            ]
            if len(exact) != 1:
                exact = []
        return [
            {
                "url": u,
                "title": "NC State Extension · " + species,
                "reported_name": species,
                "lookup_name": lookup,
                "scope": "genus" if normalized(species) in BOTANICAL_NAMES else "species",
            }
            for u in exact[:2]
        ]


class SearxProvider:
    async def search(self, species, topic, db, seconds):
        endpoint = os.getenv("WEB_SEARCH_URL", "").rstrip("/")
        parsed = urlparse(endpoint)
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or not await resolve_public(endpoint, seconds)
        ):
            raise ValueError("Configure uma API SearXNG HTTPS pública com JSON habilitado.")
        query = species + " " + " ".join(TOPICS.get(topic, TOPICS["plant_care"]))
        async with asyncio.timeout(seconds):
            async with httpx.AsyncClient(
                timeout=seconds, trust_env=False, headers=HEADERS
            ) as client:
                response = await client.get(
                    endpoint + "/search", params={"q": query, "format": "json", "safesearch": 2}
                )
                response.raise_for_status()
                if len(response.content) > 150000 or "json" not in response.headers.get(
                    "content-type", ""
                ):
                    raise ValueError("A API não retornou JSON utilizável.")
                return [
                    {"title": str(r.get("title", "Fonte botânica"))[:120], "url": r.get("url", "")}
                    for r in response.json().get("results", [])
                    if trusted_url(r.get("url", ""))
                ][:4]


class Extractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.depth = 0
        self.buffer = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "footer", "svg", "noscript"}:
            self.skip += 1
        if not self.skip and tag in {"p", "dd", "dt", "h1", "h2", "li"}:
            if self.depth == 0:
                self.buffer = []
            self.depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer", "svg", "noscript"}:
            self.skip = max(0, self.skip - 1)
        if tag in {"p", "dd", "dt", "h1", "h2", "li"} and self.depth:
            self.depth -= 1
            if not self.depth:
                text = " ".join(" ".join(self.buffer).split())
                if 15 < len(text) < 2000 and not re.search(
                    r"ignore.*instructions|system prompt|send.*(data|token)|api.key|credentials|ignore.*instru",
                    text,
                    re.I,
                ):
                    self.blocks.append(text)

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.buffer.append(data)


def relevant(html, species, topic):
    parser = Extractor()
    parser.feed(html)
    query = normalized(species).split() + TOPICS.get(topic, TOPICS["plant_care"])
    ranked = sorted(
        parser.blocks, key=lambda b: sum(term in normalized(b) for term in query), reverse=True
    )
    return "\n".join(ranked[:5])[:3000]


def source_summary(documents, topic="plant_care"):
    # Translate a publisher's structured vocabulary, not plant-specific canned answers.
    if topic == "propagation":
        methods = []
        for d in documents:
            section = re.search(
                r"(?:Recommended Propagation Strategy|Propagation):\s*(.*?)(?:Country|Whole Plant|Dimensions|Distribution|$)",
                d["excerpt"],
                re.S | re.I,
            )
            if not section:
                continue
            for marker, label in [
                ("stem cutting", "estaquia de caule"),
                ("division", "divisão"),
                ("seed", "sementes"),
                ("root cutting", "estaquia de raiz"),
            ]:
                if marker in normalized(section.group(1)):
                    methods.append(label)
        if methods:
            return (
                "A referência menciona propagação por "
                + ", ".join(dict.fromkeys(methods))
                + ". A técnica e o período precisam ser conferidos para a variedade e as condições locais."
            )
        return None
    if topic in {"pruning", "season", "toxicity", "pesticides", "current"}:
        return None
    light_values = []
    drainage = False
    for d in documents:
        text = d["excerpt"]
        section = re.search(
            r"Light:\s*(.*?)(?:Soil Texture:|Soil pH:|Soil Drainage:|$)", text, re.S
        )
        light = normalized(section.group(1)) if section else ""
        for marker, label in [
            ("partial shade", "meia-sombra"),
            ("full sun", "sol pleno"),
            ("deep shade", "sombra"),
        ]:
            if marker in light:
                light_values.append(label)
        drainage = drainage or bool(
            re.search(r"Soil Drainage:\s*(?:Good Drainage|.*?Good Drainage)", text, re.S)
        )
    labels = list(dict.fromkeys(light_values))
    if len(labels) > 1:
        return "As referências apresentam indicações diferentes de luminosidade. É melhor conferir clima, substrato e condições do local antes de escolher uma orientação."
    facts = []
    if labels and topic != "substrate":
        facts.append("luminosidade de " + labels[0])
    if drainage:
        facts.append("substrato com boa drenagem")
    return (
        "A ficha consultada indica "
        + " e ".join(facts)
        + ". A adequação depende das condições reais de cultivo."
        if facts
        else None
    )


def research(db, species, topic, budget, cancelled=lambda: False):
    if (
        not species
        or not re.fullmatch(
            r"[A-Za-zÀ-ÿ -]{3,180}" if topic == "current" else r"[A-Za-zÀ-ÿ -]{3,70}", species
        )
        or cancelled()
    ):
        return {"sources": [], "documents": [], "status": "insufficient"}
    topic = topic if topic in TOPICS else "plant_care"
    key = canonical(species, topic)
    cached = cache_get(db, key)
    if cached:
        return {**cached, "cache": "hit"}
    provider = (
        SearxProvider()
        if os.getenv("WEB_SEARCH_PROVIDER", "institutional") == "searxng"
        else InstitutionalIndexProvider()
    )
    if topic == "current" and isinstance(provider, InstitutionalIndexProvider):
        return {"sources": [], "documents": [], "status": "current_unavailable", "cache": "miss"}

    async def run():
        seconds = min(7, budget.remaining())
        documents = []
        try:
            async with asyncio.timeout(seconds):
                candidates = await provider.search(species, topic, db, seconds)
                for candidate in rank_sources(candidates, species):
                    if cancelled() or budget.remaining() < 0.2:
                        break
                    try:
                        raw = await fetch(candidate["url"], min(4, budget.remaining()))
                        lookup = candidate.get("lookup_name", species)
                        content = relevant(raw.decode("utf-8", errors="replace"), lookup, topic)
                        plain = Extractor()
                        plain.feed(raw.decode("utf-8", errors="replace"))
                        identity_present = bool(
                            re.search(
                                r"\b" + re.escape(normalized(lookup)) + r"\b",
                                normalized(" ".join(plain.blocks)),
                            )
                        )
                        if topic == "current":
                            meaningful = [
                                w
                                for w in normalized(species).split()
                                if len(w) > 3
                                and w
                                not in {
                                    "qual",
                                    "doenca",
                                    "esta",
                                    "afetando",
                                    "regiao",
                                    "atualmente",
                                    "recente",
                                    "recomendacao",
                                    "controle",
                                    "dessa",
                                    "planta",
                                }
                            ]
                            plain_text = normalized(" ".join(plain.blocks))
                            published = re.search(
                                r"(?:datePublished|article:published_time)[^\d]{1,100}(\d{4}-\d{2}-\d{2})",
                                raw.decode("utf-8", errors="replace"),
                            )
                            identity_present = bool(
                                meaningful
                                and all(w in plain_text for w in meaningful)
                                and published
                                and today() - timedelta(days=90)
                                <= date.fromisoformat(published.group(1))
                                <= today()
                            )
                        if content and identity_present:
                            documents.append({**candidate, "excerpt": content})
                    except (TimeoutError, httpx.HTTPError, ValueError):
                        logger.info("[WEB_SOURCE] status=unavailable")
        except TimeoutError:
            if not documents:
                raise
        return documents

    try:
        documents = asyncio.run(run())
        result = {
            "documents": documents,
            "sources": [{"title": d["title"], "url": d["url"]} for d in documents],
            "status": "found" if documents else "insufficient",
            "cache": "miss",
        }
        cache_put(db, key, result, (900 if topic == "current" else 86400) if documents else 300)
        logger.info(
            "[WEB_SEARCH] provider=%s cache=miss sources=%s",
            type(provider).__name__,
            len(documents),
        )
        return result
    except (TimeoutError, httpx.HTTPError, ValueError, ElementTree.ParseError, TypeError, KeyError):
        logger.info("[WEB_SEARCH] provider=%s status=unavailable", type(provider).__name__)
        return {"sources": [], "documents": [], "status": "unavailable", "cache": "miss"}
