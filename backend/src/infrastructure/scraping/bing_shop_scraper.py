"""Live Scraper Adapter: Bing Shopping BR Metasearch (Mercado Livre, Amazon, Varejo Geral)."""
from __future__ import annotations

import base64
import re
import urllib.parse
from typing import List

from bs4 import BeautifulSoup

from src.domain.entities.product_offer import ProductOffer
from src.domain.value_objects.money import Money
from src.domain.value_objects.search_criteria import SearchCriteria
from src.domain.value_objects.seller_reliability import SellerReliability
from src.infrastructure.scraping.base_http_scraper import BaseWebScraper


def _decode_bing_redirect(href: str) -> str:
    if href.startswith("/"):
        return f"https://www.bing.com{href}"
    parsed = urllib.parse.urlparse(href)
    qs = urllib.parse.parse_qs(parsed.query)
    u = qs.get("u", [""])[0]
    if u.startswith("a1"):
        try:
            decoded = base64.urlsafe_b64decode(u[2:] + "===").decode("utf-8", errors="ignore")
            if decoded.startswith("http"):
                return decoded
        except Exception:
            pass
    return href


class BingShoppingMetasearchScraper(BaseWebScraper):
    """Extracts live cross-web offers across Mercado Livre, Amazon, Kalunga, Dell & retailers."""

    @property
    def engine_id(self) -> str:
        return "bing_shopping_metasearch"

    @property
    def display_name(self) -> str:
        return "Web Shopping Index (Mercado Livre / Multi-Varejo)"

    @property
    def target_verticals(self) -> List[str]:
        return ["all", "informatica", "escritorio", "eletrica"]

    async def search(self, criteria: SearchCriteria) -> List[ProductOffer]:
        q = urllib.parse.quote_plus(criteria.normalized_query)
        url = f"https://www.bing.com/shop?q={q}&cc=br&setlang=pt-br"
        html = await self.fetch_html(url)
        soup = BeautifulSoup(html, "lxml")

        offers: List[ProductOffer] = []
        for card in soup.select("li.br-item, div.br-item"):
            strings = [s.strip() for s in card.stripped_strings if s.strip()]
            if len(strings) < 3:
                continue

            # Extract prices in card order: [current_price, optional crossed_out_old_price]
            prices: List[Money] = []
            for s in strings:
                if "R$" in s:
                    m = Money.from_raw(s)
                    if m:
                        prices.append(m)
            if not prices:
                continue

            pix_money = prices[0]
            old_money = (
                prices[1]
                if len(prices) >= 2 and prices[1].amount > pix_money.amount
                else None
            )

            # Extract full title (prefer element with [title] attribute or longest non-price string)
            title = ""
            titled_el = card.select_one("[title]")
            if titled_el and len(titled_el.get("title", "").strip()) > 10:
                title = titled_el["title"].strip()
            if not title:
                candidates = [
                    s for s in strings
                    if len(s) > 12
                    and "R$" not in s
                    and "vendedores" not in s.lower()
                    and "envio" not in s.lower()
                ]
                title = max(candidates, key=len) if candidates else ""
            if not title:
                continue

            # Extract rating (e.g. '4,9') and review count (e.g. '10K+' or '282')
            rating_val = None
            rev_count = None
            for idx, s in enumerate(strings[:5]):
                if re.fullmatch(r"[1-5],\d", s):
                    rating_val = float(s.replace(",", "."))
                    for nxt in strings[idx + 1 : idx + 4]:
                        if nxt != "·" and re.fullmatch(r"[\d.,]+K?\+?", nxt, re.I):
                            rev_count = self.parse_review_count(nxt)
                            break
                    break

            # Identify store name
            ignore_tokens = {
                "VENDA", "Envio gratuito", "Frete grátis",
                "Compare os preços entre os vendedores",
            }
            trailing = [
                s for s in strings
                if s not in ignore_tokens
                and "R$" not in s
                and s != title
                and len(s) > 2
                and not re.fullmatch(r"[1-5],\d", s)
                and not re.fullmatch(r"[\d.,]+K?\+?", s, re.I)
            ]
            store_name = trailing[-1] if trailing else "Marketplace Web"

            # Resolve best outbound URL
            href = ""
            for a in card.select("a[href]"):
                cand = a.get("href", "")
                if cand and not cand.startswith("javascript"):
                    href = _decode_bing_redirect(cand)
                    if not href.startswith("https://www.bing.com/shop/productpage"):
                        break
            if not href:
                href = url

            img_el = card.select_one("img")
            img_url = (img_el.get("src") or img_el.get("data-src")) if img_el else None
            free_ship = any("gratuito" in s.lower() or "grátis" in s.lower() for s in strings)

            reliability = SellerReliability.evaluate(
                store_name=store_name,
                seller_name=store_name,
                rating=rating_val,
                review_count=rev_count,
                via_trusted_aggregator=True,
            )

            offers.append(
                ProductOffer(
                    title=title,
                    url=href,
                    pix_price=pix_money,
                    installment_price=pix_money,
                    original_price=old_money,
                    store_name=store_name,
                    scraper_engine=self.engine_id,
                    reliability=reliability,
                    image_url=img_url,
                    free_shipping=free_ship,
                )
            )
            if len(offers) >= criteria.max_results_per_engine:
                break

        return offers
