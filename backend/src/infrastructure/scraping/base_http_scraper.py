"""Template Method Base Class for Live HTTP Browser-Impersonated Web Scrapers."""
from __future__ import annotations

import re
from abc import ABC
from typing import Optional, Tuple

from curl_cffi.requests import AsyncSession

from src.domain.ports.interfaces import IScraperAdapter
from src.domain.value_objects.money import Money

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}


class BaseWebScraper(IScraperAdapter, ABC):
    """Shared HTTP TLS Chrome impersonation utilities & Brazilian price parsers (OOP Base)."""

    timeout_seconds: float = 12.0

    async def fetch_html(self, url: str, extra_headers: Optional[dict] = None) -> str:
        headers = {**DEFAULT_HEADERS, **(extra_headers or {})}
        async with AsyncSession(impersonate="chrome") as session:
            resp = await session.get(
                url,
                headers=headers,
                timeout=self.timeout_seconds,
                allow_redirects=True,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code} ao consultar {url}")
            return resp.text

    @staticmethod
    def parse_installment_plan(text: str) -> Tuple[Optional[int], Optional[Money], Optional[Money]]:
        """Extract (count, per_installment_money, computed_total_money) from e.g. '10x de R$ 135,29'."""
        match = re.search(
            r"(\d{1,2})\s*x\s*(?:de\s*)?R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None, None, None
        count = int(match.group(1))
        per_inst = Money.from_raw(match.group(2))
        if not per_inst or count <= 0:
            return None, None, None
        total = Money(per_inst.amount * count)
        return count, per_inst, total

    @staticmethod
    def parse_review_count(raw: str) -> Optional[int]:
        text = raw.strip().upper().replace(".", "")
        m_k = re.search(r"(\d+(?:,\d+)?)K\+?", text)
        if m_k:
            return int(float(m_k.group(1).replace(",", ".")) * 1000)
        m_num = re.search(r"(\d+)", text)
        return int(m_num.group(1)) if m_num else None
