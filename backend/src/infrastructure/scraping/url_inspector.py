"""Direct Product URL Scraper using TLS Impersonation + Headless Playwright Fallback."""
from __future__ import annotations

import json
import re
from typing import List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

from src.domain.entities.product_offer import ProductOffer
from src.domain.ports.interfaces import IDirectUrlInspectorPort
from src.domain.value_objects.money import Money
from src.domain.value_objects.seller_reliability import SellerReliability
from src.infrastructure.scraping.base_http_scraper import BaseWebScraper, DEFAULT_HEADERS
from src.infrastructure.scraping.browser_manager import PlaywrightBrowserManager


class DirectUrlBrowserInspector(IDirectUrlInspectorPort):
    """Scrapes any direct product URL via JSON-LD, OpenGraph, Store DOM, and Playwright Chromium."""

    def __init__(self, browser_manager: PlaywrightBrowserManager) -> None:
        self._browser_manager = browser_manager

    @staticmethod
    def _infer_store_from_url(url: str) -> str:
        host = urlparse(url).netloc.lower().replace("www.", "")
        parts = host.split(".")
        return parts[0].capitalize() if parts else "Loja Web"

    def _extract_offers_from_html(
        self, url: str, html: str, engine_tag: str
    ) -> List[ProductOffer]:
        soup = BeautifulSoup(html, "lxml")
        store_name = self._infer_store_from_url(url)

        # 1. Check MeuPC.net multi-store table if inspecting a meupc.net/peca page
        if "meupc.net/peca/" in url:
            offers: List[ProductOffer] = []
            h1 = soup.select_one("h1")
            title = h1.get_text(" ", strip=True) if h1 else "Produto MeuPC"
            for tr in soup.select("table tr"):
                txt = " | ".join(tr.stripped_strings)
                links = [a.get("href", "") for a in tr.select("a[href]") if "/link/" in a.get("href", "")]
                if "R$" in txt and links:
                    prices = [
                        Money.from_raw(m)
                        for m in re.findall(r"R\$\s*(?:\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})", txt)
                    ]
                    prices = [p for p in prices if p]
                    if prices:
                        out = links[0] if links[0].startswith("http") else f"https://meupc.net{links[0]}"
                        st = urlparse(out).path.split("/")[2] if len(urlparse(out).path.split("/")) > 2 else store_name
                        offers.append(
                            ProductOffer(
                                title=title,
                                url=out,
                                pix_price=prices[-1],
                                installment_price=prices[0],
                                store_name=st,
                                scraper_engine=engine_tag,
                                reliability=SellerReliability.evaluate(st, via_trusted_aggregator=True),
                            )
                        )
            if offers:
                return offers

        # 2. Try Schema.org application/ld+json (@type == Product)
        title: Optional[str] = None
        pix_money: Optional[Money] = None
        old_money: Optional[Money] = None
        img_url: Optional[str] = None
        seller_name: Optional[str] = None
        rating_val: Optional[float] = None

        for sc in soup.find_all("script", type="application/ld+json"):
            if not sc.string:
                continue
            try:
                raw_json = json.loads(sc.string)
            except Exception:
                continue

            nodes = raw_json if isinstance(raw_json, list) else [raw_json]
            for node in nodes:
                if isinstance(node, dict) and "@graph" in node and isinstance(node["@graph"], list):
                    nodes.extend(node["@graph"])
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                if "Product" in str(node.get("@type", "")):
                    title = title or node.get("name")
                    im = node.get("image")
                    if isinstance(im, list) and im:
                        img_url = img_url or (im[0].get("url") if isinstance(im[0], dict) else str(im[0]))
                    elif isinstance(im, dict):
                        img_url = img_url or im.get("url")
                    elif isinstance(im, str):
                        img_url = img_url or im

                    agg_rat = node.get("aggregateRating")
                    if isinstance(agg_rat, dict) and agg_rat.get("ratingValue"):
                        try:
                            rating_val = float(str(agg_rat["ratingValue"]).replace(",", "."))
                        except ValueError:
                            pass

                    off = node.get("offers")
                    if isinstance(off, list) and off:
                        off = off[0]
                    if isinstance(off, dict):
                        p = off.get("lowPrice") or off.get("price")
                        pix_money = pix_money or Money.from_raw(p)
                        seller_obj = off.get("seller")
                        if isinstance(seller_obj, dict):
                            seller_name = seller_obj.get("name")

        # 3. Fallback / Enrich with OpenGraph + Amazon/MercadoLivre/Generic DOM selectors
        if not title:
            og_t = soup.find("meta", property="og:title")
            h1_el = soup.select_one("#productTitle, h1.ui-pdp-title, h1")
            title = (
                h1_el.get_text(" ", strip=True)
                if h1_el
                else (og_t["content"].strip() if og_t and og_t.get("content") else None)
            )

        if not img_url:
            og_i = soup.find("meta", property="og:image")
            dom_i = soup.select_one("#landingImage, img.ui-pdp-image")
            img_url = (
                dom_i.get("src")
                if dom_i and dom_i.get("src")
                else (og_i["content"] if og_i and og_i.get("content") else None)
            )

        if not pix_money:
            meta_p = (
                soup.find("meta", property="product:price:amount")
                or soup.find("meta", itemprop="price")
            )
            if meta_p and meta_p.get("content"):
                pix_money = Money.from_raw(meta_p["content"])

        if not pix_money:
            price_sel = soup.select_one(
                "#corePriceDisplay_desktop_feature_div .priceToPay .a-offscreen, "
                ".a-price .a-offscreen, "
                ".andes-money-amount__fraction, "
                ".finalPrice, .blocoproduto__price, [data-testid='price-value']"
            )
            if price_sel:
                pix_money = Money.from_raw(price_sel.get_text(" ", strip=True))

        if not pix_money:
            # Last-resort regex over visible R$ token inside main body
            body_text = soup.get_text(" ", strip=True)
            m_any = re.search(r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})", body_text)
            if m_any:
                pix_money = Money.from_raw(m_any.group(1))

        if not title or not pix_money:
            return []

        full_txt = soup.get_text(" ", strip=True)
        inst_count, inst_val, inst_total = BaseWebScraper.parse_installment_plan(full_txt)
        reliability = SellerReliability.evaluate(
            store_name=store_name,
            seller_name=seller_name or store_name,
            rating=rating_val,
        )

        return [
            ProductOffer(
                title=title,
                url=url,
                pix_price=pix_money,
                installment_price=(
                    inst_total
                    if inst_total and inst_total.amount >= pix_money.amount
                    else pix_money
                ),
                installments_count=inst_count,
                installment_value=inst_val,
                original_price=old_money,
                store_name=store_name,
                scraper_engine=engine_tag,
                reliability=reliability,
                image_url=img_url,
            )
        ]

    async def inspect_url(
        self, url: str, force_browser: bool = False
    ) -> List[ProductOffer]:
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = f"https://{clean_url}"

        if not force_browser:
            try:
                async with AsyncSession(impersonate="chrome") as session:
                    resp = await session.get(
                        clean_url,
                        headers=DEFAULT_HEADERS,
                        timeout=11.0,
                        allow_redirects=True,
                    )
                    if resp.status_code < 400:
                        found = self._extract_offers_from_html(
                            str(resp.url), resp.text, "direct_url_http"
                        )
                        if found:
                            return found
            except Exception:
                pass

        # Real Headless Chromium Browser Extraction via Playwright
        final_url, rendered_html = await self._browser_manager.render_page_html(clean_url)
        return self._extract_offers_from_html(
            final_url, rendered_html, "playwright_chromium"
        )
