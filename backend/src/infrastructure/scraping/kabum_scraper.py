"""Live Scraper Adapter: KaBuM! Official Store (__NEXT_DATA__ JSON Extractor)."""
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


class KaBuMOfficialScraper(BaseWebScraper):
    """Extracts live structured product offers from KaBuM! SSR catalog payload."""

    @property
    def engine_id(self) -> str:
        return "kabum_official"

    @property
    def display_name(self) -> str:
        return "KaBuM! (Informática, Escritório & Energia)"

    @property
    def target_verticals(self) -> List[str]:
        return ["all", "informatica", "escritorio", "eletrica"]

    async def search(self, criteria: SearchCriteria) -> List[ProductOffer]:
        slug = urllib.parse.quote(criteria.normalized_query.replace(" ", "-"))
        html = await self.fetch_html(f"https://www.kabum.com.br/busca/{slug}")
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return []

        next_data = json.loads(script.string)
        raw_payload = next_data.get("props", {}).get("pageProps", {}).get("data")
        if not raw_payload:
            return []

        catalog_root = (
            json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
        )
        items = catalog_root.get("catalogServer", {}).get("data", [])

        offers: List[ProductOffer] = []
        for item in items:
            if not item.get("available", True):
                continue

            code = item.get("code")
            name = item.get("name", "").strip()
            if not code or not name:
                continue

            pix_val = item.get("priceWithDiscount") or item.get("price")
            card_val = item.get("price") or pix_val
            old_val = item.get("oldPrice")

            pix_money = Money.from_raw(pix_val)
            card_money = Money.from_raw(card_val)
            old_money = Money.from_raw(old_val)
            if not pix_money:
                continue

            inst_count, inst_val, _ = self.parse_installment_plan(
                str(item.get("maxInstallment") or "")
            )
            seller_name = (item.get("sellerName") or "KaBuM!").strip()
            rating = item.get("averageRating") or item.get("rating")
            rating_num = float(rating) if rating else None
            rating_cnt = item.get("ratingCount")

            images = item.get("images") or []
            img_url = images[0] if images else item.get("thumbnail")
            friendly = item.get("friendlyName") or ""
            url = (
                f"https://www.kabum.com.br/produto/{code}/{friendly}"
                if friendly
                else f"https://www.kabum.com.br/produto/{code}"
            )

            reliability = SellerReliability.evaluate(
                store_name="KaBuM!",
                seller_name=seller_name,
                rating=rating_num,
                review_count=int(rating_cnt) if rating_cnt else None,
            )

            offers.append(
                ProductOffer(
                    title=name,
                    url=url,
                    pix_price=pix_money,
                    installment_price=card_money or pix_money,
                    installments_count=inst_count,
                    installment_value=inst_val,
                    original_price=old_money,
                    store_name="KaBuM!",
                    scraper_engine=self.engine_id,
                    reliability=reliability,
                    image_url=img_url,
                    sku_or_code=str(code),
                )
            )
            if len(offers) >= criteria.max_results_per_engine:
                break

        return offers
