"""Domain Aggregate Root: WatchlistItem & PriceSnapshot (DDD Persistence Core)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass(slots=True)
class PriceSnapshot:
    """Child entity recording a historical price point in SQLite."""

    pix_price: float
    installment_price: Optional[float]
    store_name: str
    offer_url: str
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class WatchlistItem:
    """Aggregate Root managing monitored products/queries and target prices."""

    id: Optional[int]
    label: str
    query_or_url: str
    is_direct_url: bool
    category: str
    target_pix_price: float
    current_best_pix: Optional[float] = None
    current_best_installment: Optional[float] = None
    lowest_historical_pix: Optional[float] = None
    best_store_name: Optional[str] = None
    best_offer_url: Optional[str] = None
    image_url: Optional[str] = None
    notes: str = ""
    notify_whatsapp: bool = True
    notify_webhook: bool = True
    last_checked_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    history: List[PriceSnapshot] = field(default_factory=list)

    @property
    def is_below_target(self) -> bool:
        return (
            self.current_best_pix is not None
            and self.target_pix_price > 0
            and self.current_best_pix <= self.target_pix_price
        )

    def register_observation(
        self,
        pix_price: float,
        installment_price: Optional[float],
        store_name: str,
        offer_url: str,
        image_url: Optional[str] = None,
    ) -> bool:
        """Record a new live price observation and return True if an alert should trigger."""
        previous_pix = self.current_best_pix
        self.current_best_pix = pix_price
        self.current_best_installment = installment_price
        self.best_store_name = store_name
        self.best_offer_url = offer_url
        if image_url and not self.image_url:
            self.image_url = image_url
        self.last_checked_at = datetime.now(timezone.utc)

        if self.lowest_historical_pix is None or pix_price < self.lowest_historical_pix:
            self.lowest_historical_pix = pix_price

        self.history.append(
            PriceSnapshot(
                pix_price=pix_price,
                installment_price=installment_price,
                store_name=store_name,
                offer_url=offer_url,
            )
        )

        hit_target = self.target_pix_price > 0 and pix_price <= self.target_pix_price
        dropped_further = previous_pix is None or pix_price < previous_pix
        return hit_target and dropped_further
