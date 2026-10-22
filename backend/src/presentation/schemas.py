"""Presentation DTO Schemas (Pydantic v2 Contracts)."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from src.domain.entities.product_offer import ProductOffer
from src.domain.entities.watchlist_item import WatchlistItem


class SearchRequestDTO(BaseModel):
    query: str = Field(..., min_length=2, max_length=160)
    category: str = "all"
    sort_by: str = "lowest_pix"
    enabled_engines: List[str] = Field(default_factory=list)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    exclude_used_and_refurbished: bool = True
    only_free_shipping: bool = False
    only_anomalies: bool = False
    only_national_stores: bool = False
    max_results_per_engine: int = Field(default=16, ge=4, le=40)


class InspectUrlsRequestDTO(BaseModel):
    urls: List[str] = Field(..., min_length=1)
    force_browser: bool = False


class CreateWatchlistItemDTO(BaseModel):
    label: str = Field(..., min_length=2, max_length=180)
    query_or_url: str = Field(..., min_length=2, max_length=600)
    is_direct_url: bool = False
    category: str = "all"
    target_pix_price: float = Field(default=0.0, ge=0.0)
    current_best_pix: Optional[float] = None
    current_best_installment: Optional[float] = None
    best_store_name: Optional[str] = None
    best_offer_url: Optional[str] = None
    image_url: Optional[str] = None
    notes: str = ""
    notify_whatsapp: bool = True
    notify_webhook: bool = True


class UpdateWatchlistTargetDTO(BaseModel):
    target_pix_price: float = Field(..., ge=0.0)
    notes: Optional[str] = None


class AlertConfigDTO(BaseModel):
    whatsapp_enabled: bool = False
    whatsapp_provider: str = "evolution_or_zapi"
    whatsapp_recipient_phone: str = ""
    whatsapp_api_url: str = ""
    whatsapp_api_token: str = ""
    webhook_enabled: bool = False
    webhook_format: str = "json"
    webhook_url: str = ""
    telegram_chat_id: str = ""
    auto_alert_on_price_bug: bool = True
    auto_alert_on_watchlist_hit: bool = True


class ShareOfferAlertDTO(BaseModel):
    title: str
    store_name: str
    pix_price_brl: str
    installment_info: str = "À vista"
    url: str
    badge: str = "OPORTUNIDADE DE COMPRA"
    discount_pct: Optional[float] = None
    median_price_brl: Optional[str] = None


class CsvExportRequestDTO(BaseModel):
    items: List[dict]
    markup_pct: float = 30.0
    marketplace_fee_pct: float = 12.0


def serialize_offer(offer: ProductOffer) -> dict:
    inst_label = (
        f"{offer.installments_count}x de {offer.installment_value.formatted_brl()}"
        if offer.installments_count and offer.installment_value
        else f"Total {offer.effective_installment_total.formatted_brl()}"
    )
    return {
        "offer_id": offer.offer_id,
        "title": offer.title,
        "url": offer.url,
        "store_name": offer.store_name,
        "scraper_engine": offer.scraper_engine,
        "pix_price": offer.pix_price.as_float,
        "pix_price_brl": offer.pix_price.formatted_brl(),
        "installment_price": offer.effective_installment_total.as_float,
        "installment_price_brl": offer.effective_installment_total.formatted_brl(),
        "installments_count": offer.installments_count,
        "installment_value": offer.installment_value.as_float if offer.installment_value else None,
        "installment_label": inst_label,
        "original_price": offer.original_price.as_float if offer.original_price else None,
        "original_price_brl": offer.original_price.formatted_brl() if offer.original_price else None,
        "pix_savings_vs_installment_pct": offer.pix_savings_vs_installment_pct,
        "listed_discount_pct": offer.listed_discount_pct,
        "deviation_from_median_pct": offer.deviation_from_median_pct,
        "anomaly_level": offer.anomaly_level.value,
        "anomaly_reason": offer.anomaly_reason,
        "reliability": {
            "seller_name": offer.reliability.seller_name,
            "trust_tier": offer.reliability.trust_tier.value,
            "badge_label": offer.reliability.badge_label,
            "score": offer.reliability.score,
            "rating": offer.reliability.rating,
            "review_count": offer.reliability.review_count,
        },
        "image_url": offer.image_url,
        "coupon_code": offer.coupon_code,
        "cashback_pct": offer.cashback_pct,
        "free_shipping": offer.free_shipping,
        "sku_or_code": offer.sku_or_code,
        "captured_at": offer.captured_at.isoformat(),
    }


def serialize_watchlist_item(item: WatchlistItem) -> dict:
    return {
        "id": item.id,
        "label": item.label,
        "query_or_url": item.query_or_url,
        "is_direct_url": item.is_direct_url,
        "category": item.category,
        "target_pix_price": item.target_pix_price,
        "current_best_pix": item.current_best_pix,
        "current_best_installment": item.current_best_installment,
        "lowest_historical_pix": item.lowest_historical_pix,
        "is_below_target": item.is_below_target,
        "best_store_name": item.best_store_name,
        "best_offer_url": item.best_offer_url,
        "image_url": item.image_url,
        "notes": item.notes,
        "notify_whatsapp": item.notify_whatsapp,
        "notify_webhook": item.notify_webhook,
        "last_checked_at": item.last_checked_at.isoformat() if item.last_checked_at else None,
        "created_at": item.created_at.isoformat(),
        "history": [
            {
                "pix_price": h.pix_price,
                "installment_price": h.installment_price,
                "store_name": h.store_name,
                "offer_url": h.offer_url,
                "captured_at": h.captured_at.isoformat(),
            }
            for h in item.history
        ],
    }
