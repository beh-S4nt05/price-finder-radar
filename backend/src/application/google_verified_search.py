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
from dataclasses import asdict
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


async def google_discover(query: str, limit: int = 8, browser_manager=None) -> tuple[list[dict], str | None]:
    """Use Playwright Chromium for Google discovery; no Bing/API fallback."""
    from bs4 import BeautifulSoup
    from urllib.parse import quote_plus, parse_qs, unquote

    if browser_manager is None:
        return [], "Navegador Chromium não configurado."
    search_url = "https://www.google.com/search?q=" + quote_plus(query) + "&num=" + str(min(limit, 10))
    try:
        final_url, html = await browser_manager.render_page_html(search_url, wait_ms=600)
        if urlsplit(final_url).hostname not in {"www.google.com", "google.com"}:
            return [], "Google redirecionou a navegação; pesquisa não confirmada."
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True).lower()
        if any(term in text for term in ("unusual traffic", "tráfego incomum", "não sou um robô", "verify you are human")):
            return [], "Google solicitou verificação humana; não será contornada."
        found = []
        seen = set()
        for heading in soup.select("h3"):
            anchor = heading.find_parent("a", href=True)
            if anchor is None:
                continue
            href = anchor["href"]
            if href.startswith("/url?"):
                href = parse_qs(urlsplit(href).query).get("q", [""])[0]
            if not href.startswith(("https://", "http://")):
                continue
            host = urlsplit(href).hostname or ""
            if host.endswith((".google.com", ".google.com.br")) or host in seen:
                continue
            seen.add(host + href)
            found.append({"title": heading.get_text(" ", strip=True), "url": href, "snippet": ""})
            if len(found) >= limit:
                break
        return found, None if found else "Nenhum link extraído do Google; layout ou acesso pode ter mudado."
    except Exception as exc:
        return [], f"Falha na navegação Chromium: {type(exc).__name__}"


async def verified_google_search(query: str, inspector, comparator, limit: int = 8, browser_manager=None) -> dict:
    candidates, discovery_error = await google_discover(query, limit, browser_manager)
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
        "summary": asdict(summary),
        "telemetry": [],
        "dorks": [],
    }
