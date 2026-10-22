"""Async SQLite Persistence Adapter implementing Domain Repository Ports."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiosqlite

from src.domain.entities.alert_config import AlertChannelConfig
from src.domain.entities.watchlist_item import PriceSnapshot, WatchlistItem
from src.domain.ports.interfaces import (
    IAlertConfigRepository,
    ISearchLogRepository,
    IWatchlistRepository,
)

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "iceberg_price_radar.db"


async def init_database(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS watchlist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                query_or_url TEXT NOT NULL,
                is_direct_url INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL DEFAULT 'all',
                target_pix_price REAL NOT NULL DEFAULT 0,
                current_best_pix REAL,
                current_best_installment REAL,
                lowest_historical_pix REAL,
                best_store_name TEXT,
                best_offer_url TEXT,
                image_url TEXT,
                notes TEXT NOT NULL DEFAULT '',
                notify_whatsapp INTEGER NOT NULL DEFAULT 1,
                notify_webhook INTEGER NOT NULL DEFAULT 1,
                last_checked_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS price_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_id INTEGER NOT NULL,
                pix_price REAL NOT NULL,
                installment_price REAL,
                store_name TEXT NOT NULL,
                offer_url TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                FOREIGN KEY (watchlist_id) REFERENCES watchlist_items(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS alert_configs (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                whatsapp_enabled INTEGER NOT NULL DEFAULT 0,
                whatsapp_provider TEXT NOT NULL DEFAULT 'evolution_or_zapi',
                whatsapp_recipient_phone TEXT NOT NULL DEFAULT '',
                whatsapp_api_url TEXT NOT NULL DEFAULT '',
                whatsapp_api_token TEXT NOT NULL DEFAULT '',
                webhook_enabled INTEGER NOT NULL DEFAULT 0,
                webhook_format TEXT NOT NULL DEFAULT 'json',
                webhook_url TEXT NOT NULL DEFAULT '',
                telegram_chat_id TEXT NOT NULL DEFAULT '',
                auto_alert_on_price_bug INTEGER NOT NULL DEFAULT 1,
                auto_alert_on_watchlist_hit INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                category TEXT NOT NULL,
                total_offers INTEGER NOT NULL,
                lowest_pix REAL,
                median_pix REAL,
                anomalies_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        await db.commit()


class SqliteWatchlistRepository(IWatchlistRepository):
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path

    async def _load_history(
        self, db: aiosqlite.Connection, item_id: int
    ) -> List[PriceSnapshot]:
        cursor = await db.execute(
            """
            SELECT pix_price, installment_price, store_name, offer_url, captured_at
            FROM price_snapshots
            WHERE watchlist_id = ?
            ORDER BY id ASC
            LIMIT 60
            """,
            (item_id,),
        )
        rows = await cursor.fetchall()
        return [
            PriceSnapshot(
                pix_price=r[0],
                installment_price=r[1],
                store_name=r[2],
                offer_url=r[3],
                captured_at=datetime.fromisoformat(r[4]),
            )
            for r in rows
        ]

    @staticmethod
    def _row_to_entity(row: aiosqlite.Row, history: List[PriceSnapshot]) -> WatchlistItem:
        return WatchlistItem(
            id=row["id"],
            label=row["label"],
            query_or_url=row["query_or_url"],
            is_direct_url=bool(row["is_direct_url"]),
            category=row["category"],
            target_pix_price=row["target_pix_price"],
            current_best_pix=row["current_best_pix"],
            current_best_installment=row["current_best_installment"],
            lowest_historical_pix=row["lowest_historical_pix"],
            best_store_name=row["best_store_name"],
            best_offer_url=row["best_offer_url"],
            image_url=row["image_url"],
            notes=row["notes"] or "",
            notify_whatsapp=bool(row["notify_whatsapp"]),
            notify_webhook=bool(row["notify_webhook"]),
            last_checked_at=(
                datetime.fromisoformat(row["last_checked_at"])
                if row["last_checked_at"]
                else None
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
            history=history,
        )

    async def list_all(self) -> List[WatchlistItem]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM watchlist_items ORDER BY id DESC"
            )
            rows = await cursor.fetchall()
            items: List[WatchlistItem] = []
            for row in rows:
                hist = await self._load_history(db, row["id"])
                items.append(self._row_to_entity(row, hist))
            return items

    async def get_by_id(self, item_id: int) -> Optional[WatchlistItem]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM watchlist_items WHERE id = ?", (item_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            hist = await self._load_history(db, item_id)
            return self._row_to_entity(row, hist)

    async def save(self, item: WatchlistItem) -> WatchlistItem:
        async with aiosqlite.connect(self._db_path) as db:
            if item.id is None:
                cursor = await db.execute(
                    """
                    INSERT INTO watchlist_items (
                        label, query_or_url, is_direct_url, category, target_pix_price,
                        current_best_pix, current_best_installment, lowest_historical_pix,
                        best_store_name, best_offer_url, image_url, notes,
                        notify_whatsapp, notify_webhook, last_checked_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.label,
                        item.query_or_url,
                        int(item.is_direct_url),
                        item.category,
                        item.target_pix_price,
                        item.current_best_pix,
                        item.current_best_installment,
                        item.lowest_historical_pix,
                        item.best_store_name,
                        item.best_offer_url,
                        item.image_url,
                        item.notes,
                        int(item.notify_whatsapp),
                        int(item.notify_webhook),
                        item.last_checked_at.isoformat() if item.last_checked_at else None,
                        item.created_at.isoformat(),
                    ),
                )
                item.id = cursor.lastrowid
                if item.current_best_pix and item.best_store_name and item.best_offer_url:
                    await db.execute(
                        """
                        INSERT INTO price_snapshots (
                            watchlist_id, pix_price, installment_price, store_name, offer_url, captured_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.id,
                            item.current_best_pix,
                            item.current_best_installment,
                            item.best_store_name,
                            item.best_offer_url,
                            item.created_at.isoformat(),
                        ),
                    )
            else:
                await db.execute(
                    """
                    UPDATE watchlist_items SET
                        label = ?, query_or_url = ?, is_direct_url = ?, category = ?,
                        target_pix_price = ?, current_best_pix = ?, current_best_installment = ?,
                        lowest_historical_pix = ?, best_store_name = ?, best_offer_url = ?,
                        image_url = ?, notes = ?, notify_whatsapp = ?, notify_webhook = ?,
                        last_checked_at = ?
                    WHERE id = ?
                    """,
                    (
                        item.label,
                        item.query_or_url,
                        int(item.is_direct_url),
                        item.category,
                        item.target_pix_price,
                        item.current_best_pix,
                        item.current_best_installment,
                        item.lowest_historical_pix,
                        item.best_store_name,
                        item.best_offer_url,
                        item.image_url,
                        item.notes,
                        int(item.notify_whatsapp),
                        int(item.notify_webhook),
                        item.last_checked_at.isoformat() if item.last_checked_at else None,
                        item.id,
                    ),
                )
            await db.commit()
        refreshed = await self.get_by_id(item.id)
        return refreshed or item

    async def add_snapshot(self, item_id: int, snapshot: PriceSnapshot) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO price_snapshots (
                    watchlist_id, pix_price, installment_price, store_name, offer_url, captured_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    snapshot.pix_price,
                    snapshot.installment_price,
                    snapshot.store_name,
                    snapshot.offer_url,
                    snapshot.captured_at.isoformat(),
                ),
            )
            await db.commit()

    async def delete(self, item_id: int) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            cur = await db.execute("DELETE FROM watchlist_items WHERE id = ?", (item_id,))
            await db.commit()
            return cur.rowcount > 0


class SqliteAlertConfigRepository(IAlertConfigRepository):
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path

    async def get_config(self) -> AlertChannelConfig:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM alert_configs WHERE id = 1")
            row = await cur.fetchone()
            if not row:
                return AlertChannelConfig()
            return AlertChannelConfig(
                id=1,
                whatsapp_enabled=bool(row["whatsapp_enabled"]),
                whatsapp_provider=row["whatsapp_provider"],
                whatsapp_recipient_phone=row["whatsapp_recipient_phone"],
                whatsapp_api_url=row["whatsapp_api_url"],
                whatsapp_api_token=row["whatsapp_api_token"],
                webhook_enabled=bool(row["webhook_enabled"]),
                webhook_format=row["webhook_format"],
                webhook_url=row["webhook_url"],
                telegram_chat_id=row["telegram_chat_id"],
                auto_alert_on_price_bug=bool(row["auto_alert_on_price_bug"]),
                auto_alert_on_watchlist_hit=bool(row["auto_alert_on_watchlist_hit"]),
            )

    async def save_config(self, config: AlertChannelConfig) -> AlertChannelConfig:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO alert_configs (
                    id, whatsapp_enabled, whatsapp_provider, whatsapp_recipient_phone,
                    whatsapp_api_url, whatsapp_api_token, webhook_enabled, webhook_format,
                    webhook_url, telegram_chat_id, auto_alert_on_price_bug, auto_alert_on_watchlist_hit
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    whatsapp_enabled = excluded.whatsapp_enabled,
                    whatsapp_provider = excluded.whatsapp_provider,
                    whatsapp_recipient_phone = excluded.whatsapp_recipient_phone,
                    whatsapp_api_url = excluded.whatsapp_api_url,
                    whatsapp_api_token = excluded.whatsapp_api_token,
                    webhook_enabled = excluded.webhook_enabled,
                    webhook_format = excluded.webhook_format,
                    webhook_url = excluded.webhook_url,
                    telegram_chat_id = excluded.telegram_chat_id,
                    auto_alert_on_price_bug = excluded.auto_alert_on_price_bug,
                    auto_alert_on_watchlist_hit = excluded.auto_alert_on_watchlist_hit
                """,
                (
                    int(config.whatsapp_enabled),
                    config.whatsapp_provider,
                    config.whatsapp_recipient_phone,
                    config.whatsapp_api_url,
                    config.whatsapp_api_token,
                    int(config.webhook_enabled),
                    config.webhook_format,
                    config.webhook_url,
                    config.telegram_chat_id,
                    int(config.auto_alert_on_price_bug),
                    int(config.auto_alert_on_watchlist_hit),
                ),
            )
            await db.commit()
        return config


class SqliteSearchLogRepository(ISearchLogRepository):
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path

    async def record_search(
        self,
        query: str,
        category: str,
        total_offers: int,
        lowest_pix: Optional[float],
        median_pix: Optional[float],
        anomalies_count: int,
    ) -> None:
        from datetime import timezone
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO search_logs (
                    query, category, total_offers, lowest_pix, median_pix, anomalies_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query,
                    category,
                    total_offers,
                    lowest_pix,
                    median_pix,
                    anomalies_count,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()

    async def list_recent(self, limit: int = 12) -> List[dict]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM search_logs ORDER BY id DESC LIMIT ?", (limit,)
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
