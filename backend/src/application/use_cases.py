"""Application Layer Use Cases (Single Responsibility Principle & Pure Orchestration)."""
from __future__ import annotations

import asyncio
import csv
import io
import time
from typing import Dict, List, Optional

from src.domain.entities.alert_config import DealNotificationPayload
from src.domain.entities.product_offer import AnomalyClassification, ProductOffer
from src.domain.entities.watchlist_item import WatchlistItem
from src.domain.ports.interfaces import (
    EngineTelemetry,
    IAlertConfigRepository,
    IDirectUrlInspectorPort,
    INotificationGateway,
    IScraperAdapter,
    ISearchLogRepository,
    IWatchlistRepository,
)
from src.domain.services.comparator_service import (
    CrossStoreComparatorService,
    MarketComparisonSummary,
)
from src.domain.services.dork_builder import AdvancedDorkLink, AdvancedSearchDorkBuilder
from src.domain.value_objects.money import Money
from src.domain.value_objects.search_criteria import ProductCategory, SearchCriteria


class SearchOffersUseCase:
    """Executes parallel live scraping, domain comparison, anomaly detection & search logging."""

    def __init__(
        self,
        scrapers: List[IScraperAdapter],
        comparator: CrossStoreComparatorService,
        dork_builder: AdvancedSearchDorkBuilder,
        search_log_repo: ISearchLogRepository,
        alert_config_repo: IAlertConfigRepository,
        notifiers: List[INotificationGateway],
    ) -> None:
        self._scrapers = scrapers
        self._comparator = comparator
        self._dork_builder = dork_builder
        self._search_log_repo = search_log_repo
        self._alert_config_repo = alert_config_repo
        self._notifiers = notifiers

    @property
    def available_engines(self) -> List[Dict[str, object]]:
        return [
            {
                "engine_id": s.engine_id,
                "display_name": s.display_name,
                "target_verticals": s.target_verticals,
            }
            for s in self._scrapers
        ]

    async def _run_single_adapter(
        self, adapter: IScraperAdapter, criteria: SearchCriteria
    ) -> tuple[List[ProductOffer], EngineTelemetry]:
        t0 = time.perf_counter()
        try:
            offers = await asyncio.wait_for(adapter.search(criteria), timeout=14.0)
            elapsed = int((time.perf_counter() - t0) * 1000)
            status = "ok" if offers else "empty"
            return offers, EngineTelemetry(
                engine_id=adapter.engine_id,
                display_name=adapter.display_name,
                status=status,
                offers_found=len(offers),
                duration_ms=elapsed,
            )
        except asyncio.TimeoutError:
            elapsed = int((time.perf_counter() - t0) * 1000)
            return [], EngineTelemetry(
                engine_id=adapter.engine_id,
                display_name=adapter.display_name,
                status="timeout",
                offers_found=0,
                duration_ms=elapsed,
                error_detail="Tempo limite excedido (14s)",
            )
        except Exception as exc:
            elapsed = int((time.perf_counter() - t0) * 1000)
            return [], EngineTelemetry(
                engine_id=adapter.engine_id,
                display_name=adapter.display_name,
                status="error",
                offers_found=0,
                duration_ms=elapsed,
                error_detail=str(exc)[:140],
            )

    async def execute(
        self, criteria: SearchCriteria
    ) -> tuple[
        List[ProductOffer],
        MarketComparisonSummary,
        List[EngineTelemetry],
        List[AdvancedDorkLink],
    ]:
        selected = [
            s
            for s in self._scrapers
            if (
                not criteria.enabled_engines
                or s.engine_id in criteria.enabled_engines
            )
            and (
                criteria.enabled_engines
                or criteria.category.value in s.target_verticals
            )
        ]

        results = await asyncio.gather(
            *(self._run_single_adapter(s, criteria) for s in selected)
        )

        raw_pool: List[ProductOffer] = []
        telemetry: List[EngineTelemetry] = []
        for offers, tel in results:
            raw_pool.extend(offers)
            telemetry.append(tel)

        ranked_offers, summary = self._comparator.process_and_rank(raw_pool, criteria)
        dorks = self._dork_builder.build_dorks(
            criteria.normalized_query, criteria.category
        )

        # Persist real search telemetry
        await self._search_log_repo.record_search(
            query=criteria.normalized_query,
            category=criteria.category.value,
            total_offers=summary.total_offers,
            lowest_pix=summary.lowest_pix,
            median_pix=summary.median_pix,
            anomalies_count=summary.potential_bugs_count,
        )

        # Fire non-blocking alerts if price bug detected and auto-alerts active
        if summary.potential_bugs_count > 0:
            cfg = await self._alert_config_repo.get_config()
            if cfg.auto_alert_on_price_bug and (cfg.whatsapp_enabled or cfg.webhook_enabled):
                top_bug = next(
                    (
                        o
                        for o in ranked_offers
                        if o.anomaly_level == AnomalyClassification.POTENTIAL_PRICE_BUG
                    ),
                    None,
                )
                if top_bug:
                    asyncio.create_task(self._dispatch_bug_alert(top_bug, summary, cfg))

        return ranked_offers, summary, telemetry, dorks

    async def _dispatch_bug_alert(self, offer: ProductOffer, summary: MarketComparisonSummary, cfg) -> None:
        med_str = Money(summary.median_pix).formatted_brl() if summary.median_pix else None
        inst_str = (
            f"{offer.installments_count}x de {offer.installment_value.formatted_brl()}"
            if offer.installments_count and offer.installment_value
            else offer.effective_installment_total.formatted_brl()
        )
        payload = DealNotificationPayload(
            headline="Possível Bug de Preço Detectado",
            product_title=offer.title,
            store_name=offer.store_name,
            pix_price_brl=offer.pix_price.formatted_brl(),
            installment_info=inst_str,
            product_url=offer.url,
            badge="ALERTA DE POSSÍVEL BUG",
            median_price_brl=med_str,
            discount_pct=offer.deviation_from_median_pct,
        )
        for gw in self._notifiers:
            try:
                if gw.channel_name == "whatsapp" and cfg.whatsapp_enabled:
                    await gw.send(payload, cfg)
                elif gw.channel_name == "webhook" and cfg.webhook_enabled:
                    await gw.send(payload, cfg)
            except Exception:
                pass


class InspectUrlsUseCase:
    """Scrapes 1..N arbitrary product URLs directly via TLS impersonation + Playwright."""

    def __init__(
        self,
        url_inspector: IDirectUrlInspectorPort,
        comparator: CrossStoreComparatorService,
    ) -> None:
        self._url_inspector = url_inspector
        self._comparator = comparator

    async def execute(
        self, urls: List[str], force_browser: bool = False
    ) -> tuple[List[ProductOffer], MarketComparisonSummary]:
        clean_urls = [u.strip() for u in urls if u.strip()][:8]
        batches = await asyncio.gather(
            *(self._url_inspector.inspect_url(u, force_browser=force_browser) for u in clean_urls),
            return_exceptions=True,
        )
        collected: List[ProductOffer] = []
        for b in batches:
            if isinstance(b, list):
                collected.extend(b)

        criteria = SearchCriteria(query="", exclude_used_and_refurbished=False)
        return self._comparator.process_and_rank(collected, criteria)


class WatchlistUseCase:
    """Manages SQLite Watchlist items, historical snapshots, and live radar re-scans."""

    def __init__(
        self,
        repo: IWatchlistRepository,
        search_use_case: SearchOffersUseCase,
        url_inspector: IDirectUrlInspectorPort,
        alert_config_repo: IAlertConfigRepository,
        notifiers: List[INotificationGateway],
    ) -> None:
        self._repo = repo
        self._search_uc = search_use_case
        self._url_inspector = url_inspector
        self._alert_repo = alert_config_repo
        self._notifiers = notifiers

    async def list_items(self) -> List[WatchlistItem]:
        return await self._repo.list_all()

    async def create_item(self, item: WatchlistItem) -> WatchlistItem:
        return await self._repo.save(item)

    async def update_target(
        self, item_id: int, target_pix_price: float, notes: Optional[str] = None
    ) -> Optional[WatchlistItem]:
        existing = await self._repo.get_by_id(item_id)
        if not existing:
            return None
        existing.target_pix_price = target_pix_price
        if notes is not None:
            existing.notes = notes
        return await self._repo.save(existing)

    async def remove_item(self, item_id: int) -> bool:
        return await self._repo.delete(item_id)

    async def refresh_single(self, item_id: int) -> Optional[WatchlistItem]:
        item = await self._repo.get_by_id(item_id)
        if not item:
            return None

        best_offer: Optional[ProductOffer] = None
        if item.is_direct_url:
            found = await self._url_inspector.inspect_url(item.query_or_url)
            if found:
                best_offer = min(found, key=lambda o: o.pix_price.amount)
        else:
            cat = (
                ProductCategory(item.category)
                if item.category in {c.value for c in ProductCategory}
                else ProductCategory.ALL
            )
            ranked, _, _, _ = await self._search_uc.execute(
                SearchCriteria(query=item.query_or_url, category=cat)
            )
            if ranked:
                best_offer = ranked[0]

        if best_offer:
            should_alert = item.register_observation(
                pix_price=best_offer.pix_price.as_float,
                installment_price=best_offer.effective_installment_total.as_float,
                store_name=best_offer.store_name,
                offer_url=best_offer.url,
                image_url=best_offer.image_url,
            )
            await self._repo.add_snapshot(item.id, item.history[-1])
            item = await self._repo.save(item)

            if should_alert:
                cfg = await self._alert_repo.get_config()
                if cfg.auto_alert_on_watchlist_hit:
                    payload = DealNotificationPayload(
                        headline=f"Meta Atingida: {item.label}",
                        product_title=best_offer.title,
                        store_name=best_offer.store_name,
                        pix_price_brl=best_offer.pix_price.formatted_brl(),
                        installment_info=best_offer.effective_installment_total.formatted_brl(),
                        product_url=best_offer.url,
                        badge="META WATCHLIST ATINGIDA",
                    )
                    for gw in self._notifiers:
                        try:
                            if gw.channel_name == "whatsapp" and cfg.whatsapp_enabled and item.notify_whatsapp:
                                await gw.send(payload, cfg)
                            elif gw.channel_name == "webhook" and cfg.webhook_enabled and item.notify_webhook:
                                await gw.send(payload, cfg)
                        except Exception:
                            pass
        return item


class ExportOffersCsvUseCase:
    """Exports comparative offers and resale lot simulations into Excel-compatible UTF-8-BOM CSV."""

    def generate_csv(
        self,
        rows: List[dict],
        markup_pct: float = 30.0,
        marketplace_fee_pct: float = 12.0,
    ) -> str:
        buf = io.StringIO()
        buf.write("\ufeff")  # UTF-8 BOM for native Excel BR compatibility
        writer = csv.writer(buf, delimiter=";")
        writer.writerow(
            [
                "Produto",
                "Loja",
                "Confiabilidade_Score",
                "Classificacao",
                "Quantidade_Lote",
                "Preco_Unitario_PIX_R$",
                "Preco_Parcelado_Total_R$",
                "Parcelamento",
                "Investimento_Lote_PIX_R$",
                "Preco_Sugerido_Revenda_R$",
                "Taxa_Venda_Estimada_R$",
                "Lucro_Liquido_Unitario_R$",
                "Lucro_Liquido_Lote_R$",
                "ROI_Estimado_%",
                "Cupom",
                "Link_Direto",
            ]
        )

        for r in rows:
            qty = max(1, int(r.get("quantity", 1)))
            pix = float(r.get("pix_price", 0.0))
            inst_total = float(r.get("installment_price") or pix)
            resale_unit = float(
                r.get("target_resale_price") or round(pix * (1.0 + markup_pct / 100.0), 2)
            )
            fee_unit = round(resale_unit * (marketplace_fee_pct / 100.0), 2)
            net_unit = round(resale_unit - fee_unit - pix, 2)
            roi = round((net_unit / pix) * 100.0, 1) if pix > 0 else 0.0

            writer.writerow(
                [
                    r.get("title", ""),
                    r.get("store_name", ""),
                    f"{r.get('reliability_score', 85)}/100",
                    r.get("anomaly_level", "NORMAL"),
                    qty,
                    f"{pix:.2f}".replace(".", ","),
                    f"{inst_total:.2f}".replace(".", ","),
                    r.get("installment_label", "À vista"),
                    f"{pix * qty:.2f}".replace(".", ","),
                    f"{resale_unit:.2f}".replace(".", ","),
                    f"{fee_unit:.2f}".replace(".", ","),
                    f"{net_unit:.2f}".replace(".", ","),
                    f"{net_unit * qty:.2f}".replace(".", ","),
                    f"{roi:.1f}%".replace(".", ","),
                    r.get("coupon_code") or "-",
                    r.get("url", ""),
                ]
            )
        return buf.getvalue()
