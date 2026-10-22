"""Live Scraper Adapter: Kalunga Official Store (Especialista Escritório & Informática)."""
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


class KalungaOfficialScraper(BaseWebScraper):
    """Extracts live PIX cash and installment prices from Kalunga.com.br."""

    @property
    def engine_id(self) -> str:
        return "kalunga_official"

    @property
    def display_name(self) -> str:
        return "Kalunga Oficial (Escritório, Suprimentos & TI)"

    @property
    def target_verticals(self) -> List[str]:
        return ["all", "escritorio", "informatica"]

    async def search(self, criteria: SearchCriteria) -> List[ProductOffer]:
        q = urllib.parse.quote_plus(criteria.normalized_query)
        html = await self.fetch_html(f"https://www.kalunga.com.br/busca/1?q={q}")
        soup = BeautifulSoup(html, "lxml")

        offers: List[ProductOffer] = []
        for card in soup.select(".blocoproduto"):
            a_el = card.select_one("a[href*='/prod/']") or card.select_one("a[href]")
            img_el = card.select_one("img")
            title = ""
            if img_el and img_el.get("title"):
                title = img_el["title"].strip()
            if not title and a_el:
                title = a_el.get_text(" ", strip=True)
            if not title:
                continue

            cash_el = card.select_one(".blocoproduto__price")
            pix_money = Money.from_raw(cash_el.get_text(" ", strip=True)) if cash_el else None
            if not pix_money:
                continue

            prazo_el = card.select_one(".blocoproduto__prazo")
            card_money = (
                Money.from_raw(prazo_el.get_text(" ", strip=True))
                if prazo_el
                else pix_money
            )

            full_text = " ".join(card.stripped_strings)
            inst_count, inst_val, inst_calc = self.parse_installment_plan(full_text)
            if (not card_money or card_money.amount < pix_money.amount) and inst_calc:
                card_money = inst_calc

            href = a_el["href"] if a_el else ""
            if href.startswith("/"):
                href = f"https://www.kalunga.com.br{href}"

            img_url = None
            if img_el:
                candidate = img_el.get("data-src") or img_el.get("src")
                if candidate and not candidate.startswith("data:"):
                    img_url = candidate

            free_ship = "frete grátis" in full_text.lower()
            m_sku = re.search(r"/(\d+)/?$", href)
            sku = m_sku.group(1) if m_sku else None

            reliability = SellerReliability.evaluate(
                store_name="Kalunga",
                seller_name="Kalunga Oficial",
            )

            offers.append(
                ProductOffer(
                    title=title,
                    url=href,
                    pix_price=pix_money,
                    installment_price=card_money or pix_money,
                    installments_count=inst_count,
                    installment_value=inst_val,
                    store_name="Kalunga",
                    scraper_engine=self.engine_id,
                    reliability=reliability,
                    image_url=img_url,
                    free_shipping=free_ship,
                    sku_or_code=sku,
                )
            )
            if len(offers) >= criteria.max_results_per_engine:
                break

        return offers
