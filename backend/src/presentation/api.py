"""FastAPI Entrypoint exposing REST API for Iceberg Price Radar."""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from src.domain.entities.alert_config import AlertChannelConfig, DealNotificationPayload
from src.domain.entities.watchlist_item import WatchlistItem
from src.domain.value_objects.search_criteria import (
    ProductCategory,
    SearchCriteria,
    SortCriterion,
)
from src.infrastructure.persistence.sqlite_db import init_database
from src.presentation.container import AppContainer
from src.presentation.schemas import (
    AlertConfigDTO,
    CreateWatchlistItemDTO,
    CsvExportRequestDTO,
    InspectUrlsRequestDTO,
    SearchRequestDTO,
    ShareOfferAlertDTO,
    UpdateWatchlistTargetDTO,
    serialize_offer,
    serialize_watchlist_item,
)

container = AppContainer()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_database()
    yield
    await container.browser_manager.shutdown()


app = FastAPI(
    title="ICEBERG // Price Radar API",
    description="Comparador Cross-Store Real, Caçador de Anomalias & Monitoramento SQLite/WhatsApp/Webhook",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    recent = await container.search_log_repo.list_recent(limit=8)
    watchlist = await container.watchlist_use_case.list_items()
    return {
        "status": "online",
        "architecture": "DDD + SOLID + Clean Architecture (Ports & Adapters)",
        "mock_data_enabled": False,
        "engines": container.search_use_case.available_engines,
        "watchlist_count": len(watchlist),
        "recent_searches": recent,
    }


@app.get("/api/dorks")
async def preview_dorks(query: str, category: str = "all"):
    cat = (
        ProductCategory(category)
        if category in {c.value for c in ProductCategory}
        else ProductCategory.ALL
    )
    dorks = container.dork_builder.build_dorks(query, cat)
    return {"query": query, "dorks": [asdict(d) for d in dorks]}


@app.post("/api/search")
async def search_offers(req: SearchRequestDTO):
    cat = (
        ProductCategory(req.category)
        if req.category in {c.value for c in ProductCategory}
        else ProductCategory.ALL
    )
    sort = (
        SortCriterion(req.sort_by)
        if req.sort_by in {s.value for s in SortCriterion}
        else SortCriterion.LOWEST_PIX
    )
    criteria = SearchCriteria(
        query=req.query,
        category=cat,
        sort_by=sort,
        enabled_engines=req.enabled_engines,
        min_price=req.min_price,
        max_price=req.max_price,
        exclude_used_and_refurbished=req.exclude_used_and_refurbished,
        only_free_shipping=req.only_free_shipping,
        only_anomalies=req.only_anomalies,
        only_national_stores=req.only_national_stores,
        max_results_per_engine=req.max_results_per_engine,
    )
    offers, summary, telemetry, dorks = await container.search_use_case.execute(criteria)
    return {
        "query": criteria.normalized_query,
        "summary": asdict(summary),
        "telemetry": [asdict(t) for t in telemetry],
        "dorks": [asdict(d) for d in dorks],
        "offers": [serialize_offer(o) for o in offers],
    }


@app.post("/api/inspect-urls")
async def inspect_direct_urls(req: InspectUrlsRequestDTO):
    offers, summary = await container.inspect_urls_use_case.execute(
        req.urls, force_browser=req.force_browser
    )
    return {
        "summary": asdict(summary),
        "offers": [serialize_offer(o) for o in offers],
    }


@app.get("/api/watchlist")
async def get_watchlist():
    items = await container.watchlist_use_case.list_items()
    return {"items": [serialize_watchlist_item(i) for i in items]}


@app.post("/api/watchlist")
async def add_watchlist_item(dto: CreateWatchlistItemDTO):
    entity = WatchlistItem(
        id=None,
        label=dto.label,
        query_or_url=dto.query_or_url,
        is_direct_url=dto.is_direct_url,
        category=dto.category,
        target_pix_price=dto.target_pix_price,
        current_best_pix=dto.current_best_pix,
        current_best_installment=dto.current_best_installment,
        lowest_historical_pix=dto.current_best_pix,
        best_store_name=dto.best_store_name,
        best_offer_url=dto.best_offer_url,
        image_url=dto.image_url,
        notes=dto.notes,
        notify_whatsapp=dto.notify_whatsapp,
        notify_webhook=dto.notify_webhook,
    )
    saved = await container.watchlist_use_case.create_item(entity)
    return serialize_watchlist_item(saved)


@app.patch("/api/watchlist/{item_id}")
async def update_watchlist_item(item_id: int, dto: UpdateWatchlistTargetDTO):
    updated = await container.watchlist_use_case.update_target(
        item_id, dto.target_pix_price, dto.notes
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Item não encontrado na Watchlist")
    return serialize_watchlist_item(updated)


@app.delete("/api/watchlist/{item_id}")
async def delete_watchlist_item(item_id: int):
    ok = await container.watchlist_use_case.remove_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return {"deleted": True}


@app.post("/api/watchlist/{item_id}/check")
async def refresh_watchlist_item(item_id: int):
    refreshed = await container.watchlist_use_case.refresh_single(item_id)
    if not refreshed:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return serialize_watchlist_item(refreshed)


@app.post("/api/watchlist/check-all")
async def refresh_all_watchlist():
    items = await container.watchlist_use_case.list_items()
    updated = []
    for it in items:
        if it.id is not None:
            res = await container.watchlist_use_case.refresh_single(it.id)
            if res:
                updated.append(serialize_watchlist_item(res))
    return {"items": updated}


@app.get("/api/alerts/config")
async def get_alert_config():
    cfg = await container.alert_config_repo.get_config()
    return asdict(cfg)


@app.put("/api/alerts/config")
async def update_alert_config(dto: AlertConfigDTO):
    cfg = AlertChannelConfig(id=1, **dto.model_dump())
    saved = await container.alert_config_repo.save_config(cfg)
    return asdict(saved)


@app.post("/api/alerts/dispatch")
async def dispatch_offer_alert(dto: ShareOfferAlertDTO):
    cfg = await container.alert_config_repo.get_config()
    payload = DealNotificationPayload(
        headline=dto.badge,
        product_title=dto.title,
        store_name=dto.store_name,
        pix_price_brl=dto.pix_price_brl,
        installment_info=dto.installment_info,
        product_url=dto.url,
        badge=dto.badge,
        median_price_brl=dto.median_price_brl,
        discount_pct=dto.discount_pct,
    )
    wa_res = await container.whatsapp_gateway.send(payload, cfg)
    wh_res = (
        await container.webhook_gateway.send(payload, cfg)
        if cfg.webhook_enabled and cfg.webhook_url
        else {"channel": "webhook", "sent_via_api": False}
    )
    return {
        "whatsapp": wa_res,
        "webhook": wh_res,
        "formatted_text": payload.format_whatsapp_text(),
    }


@app.post("/api/export/csv")
async def export_csv(dto: CsvExportRequestDTO):
    csv_text = container.export_csv_use_case.generate_csv(
        dto.items,
        markup_pct=dto.markup_pct,
        marketplace_fee_pct=dto.marketplace_fee_pct,
    )
    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="iceberg_lote_revenda.csv"'
        },
    )


FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
STATIC_GIT_DIR = Path(__file__).resolve().parents[2] / "static_git" / "iceberg-price-radar.git"

if STATIC_GIT_DIR.exists():
    app.mount(
        "/iceberg-price-radar.git",
        StaticFiles(directory=str(STATIC_GIT_DIR)),
        name="git_repo",
    )

if (FRONTEND_DIST / "assets").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST / "assets")),
        name="assets",
    )

    @app.get("/")
    async def serve_spa_index():
        return FileResponse(str(FRONTEND_DIST / "index.html"))

