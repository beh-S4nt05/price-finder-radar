"""Notification Adapters: WhatsApp Business / Gateway APIs & Generic Webhooks."""
from __future__ import annotations

import re
import urllib.parse

import httpx

from src.domain.entities.alert_config import AlertChannelConfig, DealNotificationPayload
from src.domain.ports.interfaces import INotificationGateway


class WhatsAppNotificationAdapter(INotificationGateway):
    """Dispatches formatted deal alerts to WhatsApp APIs + produces direct wa.me deep link."""

    @property
    def channel_name(self) -> str:
        return "whatsapp"

    @staticmethod
    def build_wa_me_url(phone: str, text: str) -> str:
        clean_digits = re.sub(r"\D", "", phone or "")
        encoded = urllib.parse.quote(text)
        if clean_digits:
            return f"https://wa.me/{clean_digits}?text={encoded}"
        return f"https://wa.me/?text={encoded}"

    async def send(
        self, payload: DealNotificationPayload, config: AlertChannelConfig
    ) -> dict:
        message = payload.format_whatsapp_text()
        wa_link = self.build_wa_me_url(config.whatsapp_recipient_phone, message)

        if not config.whatsapp_api_url and config.whatsapp_provider != "callmebot":
            return {
                "channel": "whatsapp",
                "sent_via_api": False,
                "wa_me_url": wa_link,
                "detail": "Link direto WhatsApp gerado (configure URL da API Evolution/Z-API/Meta para disparo automático background).",
            }

        clean_phone = re.sub(r"\D", "", config.whatsapp_recipient_phone)
        async with httpx.AsyncClient(timeout=10.0) as client:
            if config.whatsapp_provider == "callmebot":
                url = (
                    f"https://api.callmebot.com/whatsapp.php?"
                    f"phone={clean_phone}&text={urllib.parse.quote(message)}&apikey={config.whatsapp_api_token}"
                )
                resp = await client.get(url)
                return {
                    "channel": "whatsapp",
                    "sent_via_api": resp.status_code < 400,
                    "status_code": resp.status_code,
                    "wa_me_url": wa_link,
                }

            headers = {"Content-Type": "application/json"}
            if config.whatsapp_api_token:
                headers["apikey"] = config.whatsapp_api_token
                headers["Authorization"] = f"Bearer {config.whatsapp_api_token}"

            if config.whatsapp_provider == "meta_cloud":
                body = {
                    "messaging_product": "whatsapp",
                    "to": clean_phone,
                    "type": "text",
                    "text": {"preview_url": True, "body": message},
                }
            else:
                # Compatible with Evolution API v1/v2 & Z-API payloads
                body = {
                    "number": clean_phone,
                    "phone": clean_phone,
                    "text": message,
                    "message": message,
                }

            resp = await client.post(config.whatsapp_api_url, json=body, headers=headers)
            return {
                "channel": "whatsapp",
                "sent_via_api": resp.status_code < 400,
                "status_code": resp.status_code,
                "wa_me_url": wa_link,
            }


class WebhookNotificationAdapter(INotificationGateway):
    """Dispatches formatted alerts to Discord, Slack, Telegram, or Custom JSON Webhooks."""

    @property
    def channel_name(self) -> str:
        return "webhook"

    async def send(
        self, payload: DealNotificationPayload, config: AlertChannelConfig
    ) -> dict:
        if not config.webhook_url:
            return {
                "channel": "webhook",
                "sent_via_api": False,
                "detail": "URL de Webhook não configurada.",
            }

        text_msg = payload.format_whatsapp_text()
        fmt = config.webhook_format.lower()

        if fmt == "discord":
            body = {
                "username": "Iceberg Price Radar",
                "embeds": [
                    {
                        "title": f"[{payload.badge}] {payload.product_title[:220]}",
                        "url": payload.product_url,
                        "color": 0x06B6D4,
                        "fields": [
                            {"name": "Loja", "value": payload.store_name, "inline": True},
                            {"name": "Preço PIX", "value": payload.pix_price_brl, "inline": True},
                            {
                                "name": "Parcelamento",
                                "value": payload.installment_info or "À vista",
                                "inline": True,
                            },
                        ],
                    }
                ],
            }
        elif fmt == "slack":
            body = {"text": text_msg}
        elif fmt == "telegram":
            body = {
                "chat_id": config.telegram_chat_id,
                "text": text_msg,
                "parse_mode": "Markdown",
            }
        else:
            body = {
                "event": "price_alert",
                "badge": payload.badge,
                "headline": payload.headline,
                "product_title": payload.product_title,
                "store_name": payload.store_name,
                "pix_price_brl": payload.pix_price_brl,
                "installment_info": payload.installment_info,
                "discount_pct": payload.discount_pct,
                "median_price_brl": payload.median_price_brl,
                "product_url": payload.product_url,
                "formatted_message": text_msg,
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(config.webhook_url, json=body)
            return {
                "channel": "webhook",
                "sent_via_api": resp.status_code < 400,
                "status_code": resp.status_code,
            }
