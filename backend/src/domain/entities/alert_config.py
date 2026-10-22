"""Domain Entities: AlertChannelConfig & NotificationPayload (WhatsApp & Webhooks)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class AlertChannelConfig:
    """Configuration state for external notification channels (WhatsApp + Webhook)."""

    id: int = 1
    # WhatsApp Channel Settings
    whatsapp_enabled: bool = False
    whatsapp_provider: str = "evolution_or_zapi"  # evolution_or_zapi | callmebot | meta_cloud
    whatsapp_recipient_phone: str = ""            # E.g. 5592999999999
    whatsapp_api_url: str = ""                    # E.g. https://api.evolution.../message/sendText/instance
    whatsapp_api_token: str = ""                  # API Key / Bearer Token

    # Generic Webhook / Discord / Slack / Telegram / n8n Settings
    webhook_enabled: bool = False
    webhook_format: str = "json"                  # json | discord | slack | telegram
    webhook_url: str = ""
    telegram_chat_id: str = ""

    # Automatic Alert Triggers
    auto_alert_on_price_bug: bool = True
    auto_alert_on_watchlist_hit: bool = True


@dataclass(frozen=True, slots=True)
class DealNotificationPayload:
    """Immutable value payload dispatched to notification gateways."""

    headline: str
    product_title: str
    store_name: str
    pix_price_brl: str
    installment_info: str
    product_url: str
    badge: str = "OPORTUNIDADE"
    median_price_brl: Optional[str] = None
    discount_pct: Optional[float] = None

    def format_whatsapp_text(self) -> str:
        lines = [
            f"*{self.badge} | ICEBERG PRICE RADAR*",
            f"📦 *{self.product_title}*",
            f"🏪 Loja: *{self.store_name}*",
            f"💠 PIX à vista: *{self.pix_price_brl}*",
        ]
        if self.installment_info:
            lines.append(f"💳 Parcelado: {self.installment_info}")
        if self.median_price_brl and self.discount_pct:
            lines.append(
                f"📉 Economia Real: *-{self.discount_pct:.1f}%* (Mediana: {self.median_price_brl})"
            )
        lines.append(f"🔗 Link direto: {self.product_url}")
        return "\n".join(lines)
