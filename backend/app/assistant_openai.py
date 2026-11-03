"""Official Responses transport for an explicitly enabled personal connection."""

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import jwt

from . import assistant_credentials as vault
from . import assistant_runtime
from .assistant_connections import API, ConnectionError, ready, refresh
from .assistant_knowledge import grounded_text
from .assistant_request import cloud_permitted
from .assistant_sensitive import contains_secret
from .assistant_state import SemanticReply
from .assistant_web_search import SEARCH_INSTRUCTIONS, parse_results, public_history, tool_options

logger = logging.getLogger("rafinha.cloud")


def error(user_id, connection, message, *, disable=False):
    vault.update(
        user_id,
        connection["generation"],
        {
            "message": message,
            "state": "reconnect" if disable else "ready",
            "cooldown_until": time.time() + 60,
        },
    )


def consume(user_id, connection):
    day = datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    with vault._lock:
        value = vault.load(user_id)
        if not value or value["generation"] != connection["generation"] or not value.get("enabled"):
            return False
        counters = vault.usage(user_id)
        calls = counters.get("calls", 0) if counters.get("day") == day else 0
        if calls >= value.get("daily_limit", 20):
            error(
                user_id,
                value,
                "Limite diário atingido. As orientações do catálogo continuam disponíveis.",
            )
            return False
        vault.save_usage(user_id, {"day": day, "calls": calls + 1})
        return True


def generate(question, facts, history, instructions):
    user_id = facts.get("_connection_owner_id", facts.get("_owner_id"))
    selected = assistant_runtime.selected_profile()
    if not selected or selected[0] != user_id:
        return None
    connection = ready(user_id) if user_id else None
    budget = facts["_budget"]
    web_search = bool(facts.get("_web_search_request"))
    if (
        not facts.get("_allow_cloud")
        or not cloud_permitted.get()
        or not connection
        or connection.get("kind") != "chatgpt"
        or "chatgpt.tokens.use.direct" not in connection.get("scopes", [])
        or (web_search and not connection.get("web_enabled"))
        or connection.get("cooldown_until", 0) > time.time()
        or budget.remaining() < 0.4
    ):
        return None
    if connection["generation"] != facts.get("_connection_generation", connection["generation"]):
        return None
    if not consume(user_id, connection):
        return None

    async def run():
        # A slow search must leave time for a normal answer by the same account.
        attempt_timeout = min(10, budget.remaining() / 2) if web_search else budget.remaining()
        async with asyncio.timeout(attempt_timeout) as deadline:
            current = await refresh(connection, user_id, min(4, budget.remaining()))
            token = current["access_token"] if current["kind"] == "chatgpt" else current["api_key"]
            inputs = []
            history_size = 0
            for message in reversed((public_history(history) if web_search else history)[-20:]):
                if message.status != "completed":
                    continue
                # Keep recent messages intact; cutting every reply at 1,000
                # characters lost conditions and advice needed by follow-ups.
                if history_size + len(message.text) > 20000:
                    break
                inputs.append({"role": message.role, "content": message.text})
                history_size += len(message.text)
            inputs.reverse()
            photos = facts.get("_input_images", [])
            inputs.append(
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": question}, *photos]
                    if photos
                    else question,
                }
            )
            body = {
                "model": current["model"],
                "input": inputs,
                "instructions": instructions,
                "store": False,
                "stream": True,
            }
            if current["kind"] == "api":
                body["max_output_tokens"] = 500
            if web_search:
                body["instructions"] += "\n" + SEARCH_INSTRUCTIONS
                if facts.get("_web_images"):
                    body["instructions"] += (
                        " Busque até três imagens de referência das candidatas à identificação, com texto e origem verificável. Use os resultados de imagem da ferramenta; não invente imagens ou links. Diferencie referências encontradas de fotos realmente anexadas pelo cliente."
                    )
                body["tools"] = [tool_options(facts.get("_web_images", False))]
                body["tool_choice"] = {"type": "web_search"}
                body["include"] = ["web_search_call.action.sources"]
                if facts.get("_web_images"):
                    body["include"].append("web_search_call.results")
            if current["model"] == "gpt-5.6-sol":
                body["reasoning"] = {
                    "effort": "low"
                    if web_search or facts.get("_topic") in {"toxicity", "pesticides"}
                    else "none"
                }
            completed = None
            streamed_text = []
            streamed_items = []
            annotations = []
            total = 0
            cancelled = facts.get("_cancelled", lambda: False)
            publish = facts.get("_stream_reply", lambda text: None)
            started = time.monotonic()
            first_text_at = None
            last_check = last_publish = 0
            search_finished = False

            def evidence_for(text):
                nonlocal search_finished
                evidence = parse_results(streamed_items, text, annotations)
                if evidence["searched_web"] and evidence["sources"] and not search_finished:
                    # The search deadline covers finding evidence, not writing
                    # an already sourced answer. Keep the shared 30-second cap.
                    search_finished = True
                    deadline.reschedule(asyncio.get_running_loop().time() + budget.remaining())
                return evidence

            def preview():
                nonlocal last_publish
                clock = time.monotonic()
                if not streamed_text or clock - last_publish < 0.15:
                    return
                draft = "".join(streamed_text)
                if web_search:
                    evidence = evidence_for(draft)
                    if not evidence["searched_web"] or not evidence["sources"]:
                        return
                    draft = evidence["text"]
                if (
                    not draft.lstrip().startswith(("{", "```"))
                    and not contains_secret(draft)
                    and grounded_text(draft, facts)
                ):
                    publish(draft)
                    last_publish = clock

            def authorized():
                active = vault.load(user_id)
                selection = assistant_runtime.selected_profile()
                return bool(
                    not cancelled()
                    and active
                    and active.get("generation") == current["generation"]
                    and active.get("enabled")
                    and (not web_search or active.get("web_enabled"))
                    and selection
                    and selection[0] == user_id
                    and selection[1].get("generation") == current["generation"]
                )

            async with httpx.AsyncClient(
                timeout=attempt_timeout, trust_env=False, follow_redirects=False
            ) as client:
                async with client.stream(
                    "POST",
                    API + "/responses",
                    json=body,
                    headers={"Authorization": "Bearer " + token, "Accept": "text/event-stream"},
                ) as response:
                    if response.is_error:
                        # Read only a small diagnostic object. Log field names,
                        # never the response body, request, token or user input.
                        raw = bytearray()
                        async for chunk in response.aiter_bytes():
                            if len(raw) + len(chunk) > 12000:
                                break
                            raw.extend(chunk)
                        try:
                            diagnostic = json.loads(raw).get("error", {})
                            safe_fields = [
                                str(diagnostic.get(key, "unknown")) for key in ("code", "param")
                            ]
                            logger.warning(
                                "[RAFINHA_CLOUD_HTTP] code=%s param=%s",
                                *[
                                    v
                                    if re.fullmatch(r"[a-zA-Z_\.\[\]0-9]{1,100}", v)
                                    else "unknown"
                                    for v in safe_fields
                                ],
                            )
                        except (ValueError, AttributeError):
                            pass
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        clock = time.monotonic()
                        # Do not decrypt vaults or query SQLite for every token/blank SSE line.
                        if clock - last_check >= 0.2:
                            last_check = clock
                            if not authorized():
                                return None
                        total += len(line)
                        if total > 160000:
                            return None
                        if not line.startswith("data:") or line[5:].strip() == "[DONE]":
                            continue
                        event = json.loads(line[5:])
                        if event.get("type") == "response.output_item.done" and isinstance(
                            event.get("item"), dict
                        ):
                            streamed_items.append(event["item"])
                            if web_search:
                                evidence_for("".join(streamed_text))
                        if event.get(
                            "type"
                        ) == "response.output_text.annotation.added" and isinstance(
                            event.get("annotation"), dict
                        ):
                            annotations.append(event["annotation"])
                        if event.get("type") == "response.output_text.delta" and isinstance(
                            event.get("delta"), str
                        ):
                            streamed_text.append(event["delta"])
                            if first_text_at is None:
                                first_text_at = clock
                        # Search text can arrive as soon as a completed search
                        # item provides verified source URLs, before synthesis ends.
                        preview()
                        if event.get("type") in {"response.failed", "error", "response.incomplete"}:
                            details = (
                                event.get("error")
                                or (event.get("response") or {}).get("error")
                                or {}
                            )
                            code = str(details.get("code", "unknown"))
                            logger.warning(
                                "[RAFINHA_CLOUD_FAILURE] reason=stream_error code=%s",
                                code if re.fullmatch(r"[a-z_]{1,80}", code) else "unknown",
                            )
                            if web_search and code in {
                                "server_error",
                                "tool_unavailable",
                                "unsupported_tool",
                            }:
                                vault.update(
                                    user_id,
                                    current["generation"],
                                    {
                                        "web_message": "A pesquisa está indisponível neste momento. A conversa continua usando o ChatGPT."
                                    },
                                )
                                return None
                            error(
                                user_id,
                                current,
                                "A conta não concluiu a resposta ou atingiu um limite. O Rafinha local continua disponível.",
                            )
                            return None
                        if event.get("type") == "response.completed":
                            completed = event.get("response")
                            # Completion is the terminal event; waiting for socket closure
                            # can leave a finished answer in "thinking" until the deadline.
                            break
            if not authorized():
                return None
            if not completed or completed.get("status") != "completed":
                logger.warning(
                    "[RAFINHA_CLOUD_FAILURE] reason=no_completed_event delta_chunks=%s",
                    len(streamed_text),
                )
                return None
            text = "".join(
                part.get("text", "")
                for item in completed.get("output", [])
                if item.get("type") == "message"
                for part in item.get("content", [])
                if part.get("type") == "output_text"
            )
            text = text or "".join(streamed_text)
            web_result = (
                parse_results([*completed.get("output", []), *streamed_items], text, annotations)
                if web_search
                else None
            )
            if web_result:
                if not web_result["searched_web"] or not web_result["sources"]:
                    logger.warning("[RAFINHA_WEB_FAILURE] reason=no_verified_sources")
                    return None
                text = web_result["text"]
            plain = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
            if not plain:
                logger.warning(
                    "[RAFINHA_CLOUD_FAILURE] reason=empty_completed_text output_items=%s delta_chunks=%s",
                    len(completed.get("output", [])),
                    len(streamed_text),
                )
                return None
            reply = (
                SemanticReply.model_validate(json.loads(plain))
                if plain.startswith("{")
                else SemanticReply(text=plain)
            )
            if not grounded_text(reply.text, facts):
                logger.warning("[RAFINHA_CLOUD_FAILURE] reason=unsupported_factual_claim")
                return None
            if contains_secret(reply.text):
                return None
            reply._provider = "chatgpt" if current["kind"] == "chatgpt" else "openai"
            if web_result:
                reply._searched_web = True
                reply._sources = web_result["sources"]
                reply._images = web_result["images"]
                reply._hypothesis = web_result["hypothesis"]
            publish(reply.text)
            logger.info(
                "[RAFINHA_LATENCY] first_text_s=%s completed_s=%.2f search=%s",
                round(first_text_at - started, 2) if first_text_at else None,
                time.monotonic() - started,
                web_search,
            )
            vault.update(
                user_id,
                current["generation"],
                {"message": "", "cooldown_until": 0, **({"web_message": ""} if web_search else {})},
            )
            return reply

    try:
        return asyncio.run(run())
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        logger.warning("[RAFINHA_CLOUD_FAILURE] reason=http_status status=%s", status)
        if web_search and status in {400, 403, 422}:
            vault.update(
                user_id,
                connection["generation"],
                {
                    "web_message": "Este modelo ou conta não liberou a pesquisa. Você pode escolher outro modelo disponível ou continuar com o atendimento local."
                },
            )
            return None
        error(
            user_id,
            connection,
            "Conta sem acesso, limite indisponível ou conexão temporariamente indisponível. O Rafinha local continua disponível.",
            disable=status in {401, 403},
        )
    except (
        TimeoutError,
        httpx.HTTPError,
        ValueError,
        TypeError,
        KeyError,
        ConnectionError,
        jwt.PyJWTError,
    ) as exc:
        logger.warning("[RAFINHA_CLOUD_FAILURE] reason=%s", type(exc).__name__)
        if web_search and isinstance(exc, (TimeoutError, httpx.TimeoutException)):
            vault.update(
                user_id,
                connection["generation"],
                {
                    "web_message": "A pesquisa demorou além do limite. A conversa continua usando o ChatGPT."
                },
            )
            return None
        if callable(getattr(exc, "errors", None)):
            logger.warning(
                "[RAFINHA_CLOUD_VALIDATION] fields=%s",
                [(e["loc"], e["type"]) for e in exc.errors(include_input=False)],
            )
        error(
            user_id,
            connection,
            "A conexão externa não concluiu a resposta. O Rafinha local continua disponível.",
        )
    finally:
        # A failed/invalid partial answer is never promoted to saved history.
        facts.get("_stream_reply", lambda text: None)("")
    return None
