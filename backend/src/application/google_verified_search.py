"""Google-first discovery with mandatory direct-source verification.

Requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID. No alternate search
engine is used. Google snippets and advertised prices are never treated as proof.
"""
from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
from urllib.parse import urlsplit

import httpx

from src.domain.value_objects.search_criteria import SearchCriteria
from src.presentation.schemas import serialize_offer


def public_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password:
            return False
        host = parts.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return "." in host
    except ValueError:
        return False


async def _public_dns(url: str) -> bool:
    """Reject private destinations even when a public-looking hostname resolves locally."""
    host = urlsplit(url).hostname
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, None, type=socket.SOCK_STREAM)
        return bool(infos) and all(ipaddress.ip_address(info[4][0]).is_global for info in infos)
    except (OSError, ValueError):
        return False


async def google_discover(query: str, limit: int = 8) -> tuple[list[dict], str | None]:
    key = os.getenv("GOOGLE_SEARCH_API_KEY", "").strip()
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "").strip()
    if not key or not cx:
        return [], "Google Programmable Search não configurado (GOOGLE_SEARCH_API_KEY e GOOGLE_SEARCH_ENGINE_ID)."
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
            response = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": key, "cx": cx, "q": query, "num": min(10, max(1, limit))},
            )
            response.raise_for_status()
            data = response.json()
        return [
            {"title": entry.get("title", ""), "url": entry["link"], "snippet": entry.get("snippet", "")}
            for entry in data.get("items", [])
            if isinstance(entry, dict) and isinstance(entry.get("link"), str)
        ], None
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        return [], f"Falha na consulta ao Google: {type(exc).__name__}"


async def verified_google_search(query: str, inspector, comparator, limit: int = 8) -> dict:
    candidates, discovery_error = await google_discover(query, limit)
    pending = []
    raw = []
    visited = set()
    for candidate in candidates:
        url = candidate["url"]
        if url in visited:
            continue
        visited.add(url)
        reason = None
        if not public_url(url) or not await _public_dns(url):
            reason = "Endereço bloqueado por política de segurança"
        else:
            try:
                found = await asyncio.wait_for(inspector.inspect_url(url), timeout=18.0)
                if not isinstance(found, list) or not found:
                    reason = "Preço e produto não confirmados diretamente na página"
                else:
                    accepted = 0
                    for offer in found:
                        # Only direct-source offers with valid positive price and public URL.
                        if (offer.pix_price.as_float > 0 and public_url(offer.url)
                                and urlsplit(offer.url).hostname == urlsplit(url).hostname):
                            raw.append(offer)
                            accepted += 1
                    if accepted == 0:
                        reason = "Página sem oferta verificável"
            except Exception as exc:
                reason = f"Falha na inspeção: {type(exc).__name__}"
        if reason:
            pending.append({**candidate, "status": "pending", "reason": reason})
    ranked, summary = comparator.process_and_rank(raw, SearchCriteria(query=query))
    return {
        "discovery_engine": "google",
        "verification_policy": "direct_source_only",
        "discovery_error": discovery_error,
        "offers": [serialize_offer(o) for o in ranked],
        "pending": pending,
        "summary": {
            "total_offers": summary.total_offers,
            "lowest_pix": summary.lowest_pix,
            "median_pix": summary.median_pix,
        },
    }
