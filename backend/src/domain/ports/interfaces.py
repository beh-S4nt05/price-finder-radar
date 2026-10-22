"""Domain Ports (Interfaces / ABCs) following Interface Segregation & Dependency Inversion."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from src.domain.entities.alert_config import AlertChannelConfig, DealNotificationPayload
from src.domain.entities.product_offer import ProductOffer
from src.domain.entities.watchlist_item import PriceSnapshot, WatchlistItem
from src.domain.value_objects.search_criteria import SearchCriteria


@dataclass(frozen=True, slots=True)
class EngineTelemetry:
    engine_id: str
    display_name: str
    status: str  # "ok" | "empty" | "timeout" | "error"
    offers_found: int
    duration_ms: int
    error_detail: Optional[str] = None


class IScraperAdapter(ABC):
    """Port for live store / search-engine web scrapers (Open/Closed Principle)."""

    @property
    @abstractmethod
    def engine_id(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @property
    @abstractmethod
    def target_verticals(self) -> List[str]: ...

    @abstractmethod
    async def search(self, criteria: SearchCriteria) -> List[ProductOffer]:
        """Scrape live web offers matching SearchCriteria without mock data."""
        ...


class IDirectUrlInspectorPort(ABC):
    """Port for direct product page extraction via HTTP TLS impersonation + Playwright."""

    @abstractmethod
    async def inspect_url(self, url: str, force_browser: bool = False) -> List[ProductOffer]:
        ...


class IWatchlistRepository(ABC):
    """Repository Port for Watchlist Aggregate Root."""

    @abstractmethod
    async def list_all(self) -> List[WatchlistItem]: ...

    @abstractmethod
    async def get_by_id(self, item_id: int) -> Optional[WatchlistItem]: ...

    @abstractmethod
    async def save(self, item: WatchlistItem) -> WatchlistItem: ...

    @abstractmethod
    async def delete(self, item_id: int) -> bool: ...

    @abstractmethod
    async def add_snapshot(self, item_id: int, snapshot: PriceSnapshot) -> None: ...


class IAlertConfigRepository(ABC):
    """Repository Port for Notification Channel Settings."""

    @abstractmethod
    async def get_config(self) -> AlertChannelConfig: ...

    @abstractmethod
    async def save_config(self, config: AlertChannelConfig) -> AlertChannelConfig: ...


class ISearchLogRepository(ABC):
    """Repository Port for recent search history analytics."""

    @abstractmethod
    async def record_search(
        self,
        query: str,
        category: str,
        total_offers: int,
        lowest_pix: Optional[float],
        median_pix: Optional[float],
        anomalies_count: int,
    ) -> None: ...

    @abstractmethod
    async def list_recent(self, limit: int = 12) -> List[dict]: ...


class INotificationGateway(ABC):
    """Port for external alert delivery adapters (WhatsApp, Discord/Slack/Generic Webhook)."""

    @property
    @abstractmethod
    def channel_name(self) -> str: ...

    @abstractmethod
    async def send(
        self, payload: DealNotificationPayload, config: AlertChannelConfig
    ) -> dict: ...
