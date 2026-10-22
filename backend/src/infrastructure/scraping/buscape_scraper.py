"""Live Scraper Adapter: Buscapé & Zoom Cross-Store Aggregators (SSR HTML)."""
from __future__ import annotations

import re
import urllib.parse
from typing import List

from bs4 import BeautifulSoup

from src.domain.entities.product_offer import ProductOffer
from src.domain.value_objects.money import Money
from src.domain.value_objects.search_criteria import SearchCriteria
from src.domain.value_objects.seller_reliability import SellerReliability
from src.infrastructure.scraping.base_http_scraper import BaseWebScraper


class BuscapeCrossStoreScraper(BaseWebScraper):
    """Scrapes Buscapé live cross-marketplace listings (ML, Amazon, Magalu, KaBuM, Fast Shop)."""

    base_domain: str = "https://www.buscape.com.br"

    @property
    def engine_id(self) -> str:
        return "buscape_aggregator"

    @property
    def display_name(self) -> str:
        return "Buscapé (Mercado Livre / Amazon / Magalu / Varejo)"

    @property
    def target_verticals(self) -> List[str]:
        return ["all", "informatica", "escritorio", "eletrica"]

    async def search(self, criteria: SearchCriteria) -> List[ProductOffer]:
        q = urllib.parse.quote_plus(criteria.normalized_query)
        html = await self.fetch_html(f"{self.base_domain}/search?q={q}")
        soup = BeautifulSoup(html, "lxml")

        offers: List[ProductOffer] = []
        for card in soup.select('[data-testid="product-card"]'):
            strings = list(card.stripped_strings)
            if len(strings) < 2:
                continue

            # Title from heading or first non-badge string
            title_el = card.select_one('[data-testid="product-card::name"], h2, h3')
            title = title_el.get_text(" ", strip=True) if title_el else strings[0]

            # Primary cash/PIX price
            price_el = card.select_one('[data-testid="product-card::price"]')
            raw_cash = price_el.get_text(" ", strip=True) if price_el else ""
            if not raw_cash:
                for s in strings:
                    if s.startswith("R$"):
                        raw_cash = s
                        break
            pix_money = Money.from_raw(raw_cash)
            if not pix_money:
                continue

            joined = " | ".join(strings)
            inst_count, inst_val, inst_total = self.parse_installment_plan(joined)

            # Cashback percentage if shown (e.g. '1% de volta')
            m_cb = re.search(r"(\d+(?:,\d+)?)%\s*de\s*volta", joined, re.IGNORECASE)
            cashback_pct = float(m_cb.group(1).replace(",", ".")) if m_cb else None

            # Store name is typically the trailing string (e.g. 'Amazon', 'Mercado Livre', 'Menor preço via ...')
            store_name = strings[-1]
            store_name = re.sub(r"^menor preço via\s+", "", store_name, flags=re.IGNORECASE).strip()
            if (
                not store_name
                or "R$" in store_name
                or "volta" in store_name.lower()
                or len(store_name) > 38
            ):
                store_name = "Parceiro Buscapé"

            a_el = card.select_one("a[href]")
            href = a_el["href"] if a_el else ""
            if href.startswith("/"):
                href = f"{self.base_domain}{href}"

            img_el = card.select_one("img")
            img_url = (img_el.get("src") or img_el.get("data-src")) if img_el else None

            reliability = SellerReliability.evaluate(
                store_name=store_name,
                seller_name=store_name,
                via_trusted_aggregator=True,
            )

            offers.append(
                ProductOffer(
                    title=title,
                    url=href,
                    pix_price=pix_money,
                    installment_price=(
                        inst_total
                        if inst_total and inst_total.amount >= pix_money.amount
                        else pix_money
                    ),
                    installments_count=inst_count,
                    installment_value=inst_val,
                    store_name=store_name,
                    scraper_engine=self.engine_id,
                    reliability=reliability,
                    image_url=img_url,
                    cashback_pct=cashback_pct,
                )
            )
            if len(offers) >= criteria.max_results_per_engine:
                break

        return offers


class ZoomCrossStoreScraper(BuscapeCrossStoreScraper):
    """Polymorphic subclass reusing Buscapé's exact SSR schema against Zoom.com.br (OOP Reuse!)."""

    base_domain: str = "https://www.zoom.com.br"

    @property
    def engine_id(self) -> str:
        return "zoom_aggregator"

    @property
    def display_name(self) -> str:
        return "Zoom.com.br (Comparador Oficial Multi-Loja)"
