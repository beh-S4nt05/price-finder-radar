"""Explicit IoC / Dependency Injection Container wiring Ports to Concrete Adapters."""
from __future__ import annotations

from src.application.use_cases import (
    ExportOffersCsvUseCase,
    InspectUrlsUseCase,
    SearchOffersUseCase,
    WatchlistUseCase,
)
from src.domain.services.comparator_service import CrossStoreComparatorService
from src.domain.services.dork_builder import AdvancedSearchDorkBuilder
from src.infrastructure.notifications.gateways import (
    WebhookNotificationAdapter,
    WhatsAppNotificationAdapter,
)
from src.infrastructure.persistence.sqlite_db import (
    SqliteAlertConfigRepository,
    SqliteSearchLogRepository,
    SqliteWatchlistRepository,
)
from src.infrastructure.scraping.amazon_dork_scraper import AmazonDirectDorkScraper
from src.infrastructure.scraping.bing_shop_scraper import BingShoppingMetasearchScraper
from src.infrastructure.scraping.browser_manager import PlaywrightBrowserManager
from src.infrastructure.scraping.buscape_scraper import (
    BuscapeCrossStoreScraper,
    ZoomCrossStoreScraper,
)
from src.infrastructure.scraping.copafer_scraper import CopaferEletricaScraper
from src.infrastructure.scraping.kabum_scraper import KaBuMOfficialScraper
from src.infrastructure.scraping.kalunga_scraper import KalungaOfficialScraper
from src.infrastructure.scraping.meupc_scraper import MeuPcCrossStoreScraper
from src.infrastructure.scraping.url_inspector import DirectUrlBrowserInspector


class AppContainer:
    """Centralized Composition Root adhering strictly to Dependency Inversion (SOLID)."""

    def __init__(self) -> None:
        self.browser_manager = PlaywrightBrowserManager()

        # Domain Services
        self.comparator_service = CrossStoreComparatorService()
        self.dork_builder = AdvancedSearchDorkBuilder()

        # Persistence Repositories (SQLite)
        self.watchlist_repo = SqliteWatchlistRepository()
        self.alert_config_repo = SqliteAlertConfigRepository()
        self.search_log_repo = SqliteSearchLogRepository()

        # Notification Gateways (WhatsApp + Webhook)
        self.whatsapp_gateway = WhatsAppNotificationAdapter()
        self.webhook_gateway = WebhookNotificationAdapter()
        self.notifiers = [self.whatsapp_gateway, self.webhook_gateway]

        # Live Web Scraper Adapters (Zero Fake Data!)
        self.scrapers = [
            MeuPcCrossStoreScraper(),
            AmazonDirectDorkScraper(),
            BuscapeCrossStoreScraper(),
            ZoomCrossStoreScraper(),
            KaBuMOfficialScraper(),
            KalungaOfficialScraper(),
            CopaferEletricaScraper(),
            BingShoppingMetasearchScraper(),
        ]
        self.url_inspector = DirectUrlBrowserInspector(self.browser_manager)

        # Application Use Cases
        self.search_use_case = SearchOffersUseCase(
            scrapers=self.scrapers,
            comparator=self.comparator_service,
            dork_builder=self.dork_builder,
            search_log_repo=self.search_log_repo,
            alert_config_repo=self.alert_config_repo,
            notifiers=self.notifiers,
        )
        self.inspect_urls_use_case = InspectUrlsUseCase(
            url_inspector=self.url_inspector,
            comparator=self.comparator_service,
        )
        self.watchlist_use_case = WatchlistUseCase(
            repo=self.watchlist_repo,
            search_use_case=self.search_use_case,
            url_inspector=self.url_inspector,
            alert_config_repo=self.alert_config_repo,
            notifiers=self.notifiers,
        )
        self.export_csv_use_case = ExportOffersCsvUseCase()
