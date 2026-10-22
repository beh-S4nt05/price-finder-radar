"""Live Scraper Adapter: Copafer Official Store (VTEX Schema.org Elétrica & Ferramentas)."""
from __future__ import annotations

import json
import urllib.parse
from typing import List

from bs4 import BeautifulSoup

from src.domain.entities.product_offer import ProductOffer
from src.domain.value_objects.money import Money
from src.domain.value_objects.search_criteria import SearchCriteria
from src.domain.value_objects.seller_reliability import SellerReliability
from src.infrastructure.scraping.base_http_scraper import BaseWebScraper


class CopaferEletricaScraper(BaseWebScraper):
    """Extracts live VTEX Schema.org ItemList products for Electrical, Tools & Infrastructure."""

    @property
    def engine_id(self) -> str:
        return "copafer_eletrica"

    @property
    def display_name(self) -> str:
        return "Copafer Oficial (Elétrica, Cabos, Disjuntores & Ferramentas)"

    @property
    def target_verticals(self) -> List[str]:
        return ["all", "eletrica", "escritorio"]

    async def search(self, criteria: SearchCriteria) -> List[ProductOffer]:
        enc = urllib.parse.quote(criteria.normalized_query)
        html = await self.fetch_html(f"https://www.copafer.com.br/{enc}?_q={enc}&map=ft")
        soup = BeautifulSoup(html, "lxml")

        offers: List[ProductOffer] = []
        for sc in soup.find_all("script", type="application/ld+json"):
            if not sc.string:
                continue
            try:
                data = json.loads(sc.string)
            except Exception:
                continue

            if not isinstance(data, dict) or data.get("@type") != "ItemList":
                continue

            for entry in data.get("itemListElement", []):
                prod = entry.get("item", entry)
                if not isinstance(prod, dict):
                    continue
                name = prod.get("name", "").strip()
                url = prod.get("@id") or prod.get("url") or ""
                offer_node = prod.get("offers", {})
                if isinstance(offer_node, list) and offer_node:
                    offer_node = offer_node[0]

                low_price = (
                    offer_node.get("lowPrice")
                    or offer_node.get("price")
                )
                high_price = offer_node.get("highPrice") or low_price
                pix_money = Money.from_raw(low_price)
                card_money = Money.from_raw(high_price)
                if not name or not url or not pix_money:
                    continue

                image_val = prod.get("image")
                if isinstance(image_val, list):
                    image_val = image_val[0] if image_val else None

                reliability = SellerReliability.evaluate(
                    store_name="Copafer",
                    seller_name="Copafer Oficial",
                )

                offers.append(
                    ProductOffer(
                        title=name,
                        url=url,
                        pix_price=pix_money,
                        installment_price=card_money or pix_money,
                        store_name="Copafer",
                        scraper_engine=self.engine_id,
                        reliability=reliability,
                        image_url=image_val,
                        sku_or_code=str(prod.get("sku") or prod.get("mpn") or ""),
                    )
                )
                if len(offers) >= criteria.max_results_per_engine:
                    return offers

        return offers
