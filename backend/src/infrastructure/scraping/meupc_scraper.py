"""Live Scraper Adapter: MeuPC.net Multi-Store Table Extractor via Web Dorking."""
from __future__ import annotations

import asyncio
import re
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from ddgs import DDGS

from src.domain.entities.product_offer import ProductOffer
from src.domain.value_objects.money import Money
from src.domain.value_objects.search_criteria import SearchCriteria
from src.domain.value_objects.seller_reliability import SellerReliability
from src.infrastructure.scraping.base_http_scraper import BaseWebScraper, DEFAULT_HEADERS

STORE_NAME_MAP = {
    "amazon": "Amazon.com.br",
    "mercadolivre": "Mercado Livre",
    "kabum": "KaBuM!",
    "terabyte": "Terabyteshop",
    "pichau": "Pichau",
    "gigantec": "Gigantec",
    "fgtec": "FGTEC",
    "magazineluiza": "Magazine Luiza",
    "patoloco": "PatoLoco",
    "guerradigital": "Guerra Digital",
}


class MeuPcCrossStoreScraper(BaseWebScraper):
    """Discovers canonical MeuPC.net part pages via real search dork and extracts all live store rows."""

    @property
    def engine_id(self) -> str:
        return "meupc_cross_store"

    @property
    def display_name(self) -> str:
        return "MeuPC.net (Amazon / Terabyte / ML / Pichau / KaBuM)"

    @property
    def target_verticals(self) -> List[str]:
        return ["all", "informatica", "escritorio"]

    @staticmethod
    def _dork_peca_urls(query: str) -> List[str]:
        urls: List[str] = []
        seen = set()
        with DDGS() as ddgs:
            results = list(
                ddgs.text(f"{query} site:meupc.net/peca", region="br-pt", max_results=5)
            )
            for item in results:
                href = item.get("href", "")
                if "meupc.net/peca/" in href and href not in seen:
                    seen.add(href)
                    urls.append(href)
        return urls[:3]

    async def _scrape_peca_page(
        self, session: AsyncSession, url: str
    ) -> List[ProductOffer]:
        offers: List[ProductOffer] = []
        resp = await session.get(url, headers=DEFAULT_HEADERS, timeout=10.0)
        if resp.status_code >= 400:
            return offers

        soup = BeautifulSoup(resp.text, "lxml")
        h1 = soup.select_one("h1")
        page_title = h1.get_text(" ", strip=True) if h1 else ""
        if not page_title:
            title_tag = soup.select_one("title")
            page_title = (
                title_tag.get_text(" ", strip=True).replace("- MEUPC.NET", "").strip()
                if title_tag
                else "Produto MeuPC"
            )

        img_url = None
        for im in soup.select("img[src]"):
            src = im.get("src", "")
            if "static.meupc.net/peca/" in src:
                img_url = src
                break

        for tr in soup.select("table tr"):
            row_text = " | ".join(tr.stripped_strings)
            if "R$" not in row_text:
                continue

            links = [a.get("href", "") for a in tr.select("a[href]") if "/link/" in a.get("href", "")]
            if not links:
                continue

            out_url = links[0]
            if out_url.startswith("/"):
                out_url = f"https://meupc.net{out_url}"

            # Infer official store name from /link/{StoreName}/{ID}
            path_parts = [p for p in urlparse(out_url).path.split("/") if p]
            raw_store = path_parts[1] if len(path_parts) >= 2 and path_parts[0] == "link" else "Loja Parceira"
            store_display = STORE_NAME_MAP.get(raw_store.lower(), raw_store)

            # Extract all R$ tokens in row: typically [Card Total, per installment, PIX Cash]
            price_matches = re.findall(r"R\$\s*(?:\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})", row_text)
            parsed_prices = [Money.from_raw(m) for m in price_matches]
            parsed_prices = [p for p in parsed_prices if p is not None]
            if not parsed_prices:
                continue

            inst_count, inst_val, _ = self.parse_installment_plan(row_text)
            # In MeuPC rows: first price is Card Total, last price is PIX Cash price!
            card_total = parsed_prices[0]
            pix_cash = parsed_prices[-1]
            # Safeguard if installment per-month matched last accidentally
            if inst_val and pix_cash.amount == inst_val.amount and inst_count and inst_count > 1:
                pix_cash = card_total

            if card_total.amount < pix_cash.amount:
                pix_cash, card_total = card_total, pix_cash

            coupon_match = re.search(r"cupom\s+([A-Z0-9_-]{3,20})", row_text, re.IGNORECASE)
            coupon = coupon_match.group(1).upper() if coupon_match else None
            free_ship = "grátis" in row_text.lower() or "gratis" in row_text.lower()

            reliability = SellerReliability.evaluate(
                store_name=store_display,
                seller_name=store_display,
                via_trusted_aggregator=True,
            )

            offers.append(
                ProductOffer(
                    title=page_title,
                    url=out_url,
                    pix_price=pix_cash,
                    installment_price=card_total,
                    installments_count=inst_count,
                    installment_value=inst_val,
                    store_name=store_display,
                    scraper_engine=self.engine_id,
                    reliability=reliability,
                    image_url=img_url,
                    coupon_code=coupon,
                    free_shipping=free_ship,
                )
            )
        return offers

    async def search(self, criteria: SearchCriteria) -> List[ProductOffer]:
        urls = await asyncio.to_thread(self._dork_peca_urls, criteria.normalized_query)
        if not urls:
            return []

        async with AsyncSession(impersonate="chrome") as session:
            batches = await asyncio.gather(
                *(self._scrape_peca_page(session, u) for u in urls),
                return_exceptions=True,
            )

        collected: List[ProductOffer] = []
        for batch in batches:
            if isinstance(batch, list):
                collected.extend(batch)
        return collected[: criteria.max_results_per_engine]
