"""Live Scraper Adapter: Amazon.com.br Direct PDP Scraper via Advanced Search Dork."""
from __future__ import annotations

import asyncio
import re
from typing import List, Optional

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from ddgs import DDGS

from src.domain.entities.product_offer import ProductOffer
from src.domain.value_objects.money import Money
from src.domain.value_objects.search_criteria import SearchCriteria
from src.domain.value_objects.seller_reliability import SellerReliability
from src.infrastructure.scraping.base_http_scraper import BaseWebScraper, DEFAULT_HEADERS


class AmazonDirectDorkScraper(BaseWebScraper):
    """Finds canonical Amazon.com.br /dp/ URLs via search dorking and scrapes live prices directly."""

    @property
    def engine_id(self) -> str:
        return "amazon_direct_dork"

    @property
    def display_name(self) -> str:
        return "Amazon.com.br (Dork PDP Direto)"

    @property
    def target_verticals(self) -> List[str]:
        return ["all", "informatica", "escritorio", "eletrica"]

    @staticmethod
    def _discover_amazon_dp_urls(query: str) -> List[str]:
        urls: List[str] = []
        seen_asins = set()
        with DDGS() as ddgs:
            hits = list(
                ddgs.text(
                    f"{query} site:amazon.com.br/dp OR site:amazon.com.br",
                    region="br-pt",
                    max_results=8,
                )
            )
            for h in hits:
                href = h.get("href", "")
                m = re.search(r"amazon\.com\.br/(?:[^/]+/)?dp/([A-Z0-9]{10})", href)
                if m:
                    asin = m.group(1)
                    if asin not in seen_asins:
                        seen_asins.add(asin)
                        urls.append(f"https://www.amazon.com.br/dp/{asin}")
        return urls[:5]

    async def _scrape_dp_url(
        self, session: AsyncSession, url: str
    ) -> Optional[ProductOffer]:
        try:
            resp = await session.get(url, headers=DEFAULT_HEADERS, timeout=10.0)
            if resp.status_code >= 400:
                return None
        except Exception:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        title_el = soup.select_one("#productTitle")
        if not title_el:
            return None
        title = title_el.get_text(" ", strip=True)

        # Primary live price block
        price_el = (
            soup.select_one("#corePriceDisplay_desktop_feature_div .priceToPay .a-offscreen")
            or soup.select_one("#corePrice_feature_div .a-price .a-offscreen")
            or soup.select_one(".a-price .a-offscreen")
        )
        if not price_el:
            whole = soup.select_one(".a-price-whole")
            frac = soup.select_one(".a-price-fraction")
            raw_price = (
                f"{whole.get_text(strip=True)},{frac.get_text(strip=True) if frac else '00'}"
                if whole
                else None
            )
        else:
            raw_price = price_el.get_text(strip=True)

        pix_money = Money.from_raw(raw_price)
        if not pix_money:
            return None

        # Crossed-out list price
        old_el = soup.select_one(".basisPrice .a-offscreen, span[data-a-strike='true'] .a-offscreen")
        old_money = Money.from_raw(old_el.get_text(strip=True)) if old_el else None

        # Installments block
        inst_block = soup.select_one("#installmentCalculator_feature_div, #corePriceDisplay_desktop_feature_div")
        inst_text = inst_block.get_text(" ", strip=True) if inst_block else ""
        inst_count, inst_val, inst_total = self.parse_installment_plan(inst_text)

        # Seller attribution
        seller_el = soup.select_one("#sellerProfileTriggerId")
        seller_name = seller_el.get_text(" ", strip=True) if seller_el else "Amazon.com.br"

        # Star rating & reviews
        rating_val = None
        rating_el = soup.select_one("#acrPopover")
        if rating_el and rating_el.get("title"):
            m_rat = re.search(r"(\d,\d)", rating_el["title"])
            if m_rat:
                rating_val = float(m_rat.group(1).replace(",", "."))

        rev_el = soup.select_one("#acrCustomerReviewText")
        rev_count = self.parse_review_count(rev_el.get_text()) if rev_el else None

        img_el = soup.select_one("#landingImage, #imgBlkFront")
        img_url = img_el.get("src") if img_el else None
        free_ship = "frete grátis" in resp.text.lower() or "entrega grátis" in resp.text.lower()

        reliability = SellerReliability.evaluate(
            store_name="Amazon.com.br",
            seller_name=seller_name,
            rating=rating_val,
            review_count=rev_count,
        )

        return ProductOffer(
            title=title,
            url=url,
            pix_price=pix_money,
            installment_price=inst_total if inst_total and inst_total.amount >= pix_money.amount else pix_money,
            installments_count=inst_count,
            installment_value=inst_val,
            original_price=old_money,
            store_name="Amazon.com.br",
            scraper_engine=self.engine_id,
            reliability=reliability,
            image_url=img_url,
            free_shipping=free_ship,
            sku_or_code=url.split("/dp/")[-1],
        )

    async def search(self, criteria: SearchCriteria) -> List[ProductOffer]:
        dp_urls = await asyncio.to_thread(
            self._discover_amazon_dp_urls, criteria.normalized_query
        )
        if not dp_urls:
            return []

        async with AsyncSession(impersonate="chrome") as session:
            results = await asyncio.gather(
                *(self._scrape_dp_url(session, u) for u in dp_urls),
                return_exceptions=True,
            )

        return [r for r in results if isinstance(r, ProductOffer)]
