"""Domain Entity: ProductOffer — Core comparative commercial offer representation."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from src.domain.value_objects.money import Money
from src.domain.value_objects.seller_reliability import SellerReliability


class AnomalyClassification(str, Enum):
    NORMAL = "NORMAL"
    GOOD_DEAL = "GOOD_DEAL"           # 15% - 34% below market median or old list price
    POTENTIAL_PRICE_BUG = "POTENTIAL_PRICE_BUG"  # >= 35% below market median with high trust!


@dataclass(slots=True)
class ProductOffer:
    """Domain Entity representing a verified live product listing scraped from the web.

    Encapsulates PIX cash pricing, card installment pricing, seller trust,
    anomaly classification against live market median, and resale profit simulation.
    """

    title: str
    url: str
    pix_price: Money
    store_name: str
    scraper_engine: str
    reliability: SellerReliability

    installment_price: Optional[Money] = None
    installments_count: Optional[int] = None
    installment_value: Optional[Money] = None
    original_price: Optional[Money] = None
    image_url: Optional[str] = None
    coupon_code: Optional[str] = None
    cashback_pct: Optional[float] = None
    free_shipping: bool = False
    in_stock: bool = True
    sku_or_code: Optional[str] = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Computed domain comparative attributes (populated by Comparator Domain Service)
    anomaly_level: AnomalyClassification = AnomalyClassification.NORMAL
    deviation_from_median_pct: float = 0.0
    anomaly_reason: Optional[str] = None

    @property
    def offer_id(self) -> str:
        """Deterministic identity based on store + normalized URL/title."""
        raw = f"{self.store_name.lower().strip()}::{self.title.lower().strip()[:90]}::{self.pix_price.amount}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    @property
    def effective_installment_total(self) -> Money:
        """Returns installment total if explicitly provided, else falls back to PIX/cash price."""
        return self.installment_price if self.installment_price is not None else self.pix_price

    @property
    def pix_savings_vs_installment_pct(self) -> float:
        """How much cheaper PIX is vs card installments on this same offer."""
        if self.installment_price and self.installment_price.amount > self.pix_price.amount:
            return self.pix_price.discount_percentage_from(self.installment_price)
        return 0.0

    @property
    def listed_discount_pct(self) -> float:
        """Discount relative to crossed-out list price when declared by store."""
        if self.original_price and self.original_price.amount > self.pix_price.amount:
            return self.pix_price.discount_percentage_from(self.original_price)
        return 0.0

    def simulate_resale_profit(
        self,
        resale_price: float,
        marketplace_fee_pct: float = 12.0,
        shipping_cost: float = 0.0,
    ) -> dict[str, float]:
        """Domain behavior: calculate net profit and ROI when buying on PIX to resell."""
        cost = self.pix_price.as_float
        fee_value = resale_price * (marketplace_fee_pct / 100.0)
        net_revenue = resale_price - fee_value - shipping_cost
        net_profit = round(net_revenue - cost, 2)
        roi_pct = round((net_profit / cost) * 100.0, 1) if cost > 0 else 0.0
        return {
            "buy_cost_pix": round(cost, 2),
            "gross_resale_price": round(resale_price, 2),
            "marketplace_fee": round(fee_value, 2),
            "net_profit": net_profit,
            "roi_pct": roi_pct,
        }
