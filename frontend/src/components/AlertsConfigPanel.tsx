import React, { useEffect, useState } from 'react';
import { MessageCircle, Save, Send, Webhook } from 'lucide-react';
import { apiClient } from '../services/apiClient';
import { AlertConfigDTO } from '../types/domain';

interface AlertsConfigPanelProps {
  notifyToast: (msg: string) => void;
}

export const AlertsConfigPanel: React.FC<AlertsConfigPanelProps> = ({
  notifyToast,
}) => {
  const [cfg, setCfg] = useState<AlertConfigDTO>({
    whatsapp_enabled: true,
    whatsapp_provider: 'evolution_or_zapi',
    whatsapp_recipient_phone: '',
    whatsapp_api_url: '',
    whatsapp_api_token: '',
    webhook_enabled: false,
    webhook_format: 'json',
    webhook_url: '',
    telegram_chat_id: '',
    auto_alert_on_price_bug: true,
    auto_alert_on_watchlist_hit: true,
  });
  const [previewMsg, setPreviewMsg] = useState<string>('');
  const [waPreviewLink, setWaPreviewLink] = useState<string>('');

  useEffect(() => {
    apiClient.getAlertConfig().then(setCfg).catch(() => {});
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const saved = await apiClient.saveAlertConfig(cfg);
    setCfg(saved);
    notifyToast('Configurações de WhatsApp & Webhooks salvas no SQLite.');
  };

  const handleTestDispatch = async () => {
    await apiClient.saveAlertConfig(cfg);
    const res = await apiClient.dispatchAlert({
      title: 'SSD Kingston NV3 1TB M.2 NVMe PCIe 4.0 SNV3S/1000G',
      store_name: 'Amazon.com.br',
      pix_price_brl: 'R$ 809,10',
      installment_info: '10x de R$ 89,90',
      url: 'https://www.amazon.com.br/dp/B0DBR3DZWG',
      badge: 'TESTE DE ALERTA ICEBERG',
      discount_pct: 36.5,
      median_price_brl: 'R$ 1.274,00',
    });
    setPreviewMsg(res.formatted_text);
    setWaPreviewLink(res.whatsapp.wa_me_url);
    notifyToast(
      res.whatsapp.sent_via_api || res.webhook.sent_via_api
        ? 'Alerta disparado com sucesso via API!'
        : 'Card WhatsApp formatado gerado! Clique em "Abrir no WhatsApp" ou conecte sua API.'
    );
  };

  return (
    <form onSubmit={handleSave} className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* WhatsApp Integration Card */}
        <section className="rounded-2xl p-6 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <MessageCircle className="w-4 h-4 text-sky-600 dark:text-cyan-400" />
              Integração WhatsApp (API & Disparo Rápido)
            </h2>
            <label className="inline-flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={cfg.whatsapp_enabled}
                onChange={(e) =>
                  setCfg({ ...cfg, whatsapp_enabled: e.target.checked })
                }
                className="accent-cyan-500"
              />
              <span>Ativo</span>
            </label>
          </div>

          <div className="space-y-3 text-xs">
            <label className="block">
              <span className="text-slate-600 dark:text-slate-400">
                Número Destino WhatsApp (com DDI + DDD, ex: 5592999999999)
              </span>
              <input
                type="text"
                value={cfg.whatsapp_recipient_phone}
                onChange={(e) =>
                  setCfg({ ...cfg, whatsapp_recipient_phone: e.target.value })
                }
                placeholder="5592999999999"
                className="num-mono mt-1 w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
              />
            </label>

            <label className="block">
              <span className="text-slate-600 dark:text-slate-400">
                Provedor de Gateway WhatsApp
              </span>
              <select
                value={cfg.whatsapp_provider}
                onChange={(e) =>
                  setCfg({ ...cfg, whatsapp_provider: e.target.value })
                }
                className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
              >
                <option value="evolution_or_zapi">
                  Evolution API / Z-API (Self-Hosted ou Cloud)
                </option>
                <option value="callmebot">
                  CallMeBot WhatsApp Free Webhook
                </option>
                <option value="meta_cloud">
                  Meta WhatsApp Business Cloud API Oficial
                </option>
              </select>
            </label>

            <label className="block">
              <span className="text-slate-600 dark:text-slate-400">
                Endpoint da API WhatsApp (Opcional p/ Disparo Background)
              </span>
              <input
                type="text"
                value={cfg.whatsapp_api_url}
                onChange={(e) =>
                  setCfg({ ...cfg, whatsapp_api_url: e.target.value })
                }
                placeholder="https://sua-instancia/message/sendText/radar"
                className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
              />
            </label>

            <label className="block">
              <span className="text-slate-600 dark:text-slate-400">
                API Key / Bearer Token
              </span>
              <input
                type="password"
                value={cfg.whatsapp_api_token}
                onChange={(e) =>
                  setCfg({ ...cfg, whatsapp_api_token: e.target.value })
                }
                placeholder="Token da instância ou API Key"
                className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
              />
            </label>
          </div>
        </section>

        {/* Webhook Integration Card */}
        <section className="rounded-2xl p-6 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Webhook className="w-4 h-4 text-sky-600 dark:text-cyan-400" />
              Webhooks (n8n, Discord, Slack & Telegram)
            </h2>
            <label className="inline-flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={cfg.webhook_enabled}
                onChange={(e) =>
                  setCfg({ ...cfg, webhook_enabled: e.target.checked })
                }
                className="accent-cyan-500"
              />
              <span>Ativo</span>
            </label>
          </div>

          <div className="space-y-3 text-xs">
            <label className="block">
              <span className="text-slate-600 dark:text-slate-400">
                Formato do Payload
              </span>
              <select
                value={cfg.webhook_format}
                onChange={(e) =>
                  setCfg({ ...cfg, webhook_format: e.target.value })
                }
                className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
              >
                <option value="json">JSON Estruturado (n8n / Make / ERP)</option>
                <option value="discord">Discord Rich Embed</option>
                <option value="slack">Slack Incoming Webhook</option>
                <option value="telegram">Telegram Bot sendMessage</option>
              </select>
            </label>

            <label className="block">
              <span className="text-slate-600 dark:text-slate-400">
                URL do Webhook
              </span>
              <input
                type="text"
                value={cfg.webhook_url}
                onChange={(e) =>
                  setCfg({ ...cfg, webhook_url: e.target.value })
                }
                placeholder="https://discord.com/api/webhooks/... ou https://seu-n8n/webhook/..."
                className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
              />
            </label>

            {cfg.webhook_format === 'telegram' && (
              <label className="block">
                <span className="text-slate-600 dark:text-slate-400">
                  Telegram Chat ID
                </span>
                <input
                  type="text"
                  value={cfg.telegram_chat_id}
                  onChange={(e) =>
                    setCfg({ ...cfg, telegram_chat_id: e.target.value })
                  }
                  placeholder="-1001234567890"
                  className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
                />
              </label>
            )}

            <div className="pt-2 space-y-2 border-t border-slate-200 dark:border-slate-800">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={cfg.auto_alert_on_price_bug}
                  onChange={(e) =>
                    setCfg({
                      ...cfg,
                      auto_alert_on_price_bug: e.target.checked,
                    })
                  }
                  className="accent-cyan-500"
                />
                <span>Disparar automaticamente ao detectar Possível Bug (&ge;35% abaixo da mediana)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={cfg.auto_alert_on_watchlist_hit}
                  onChange={(e) =>
                    setCfg({
                      ...cfg,
                      auto_alert_on_watchlist_hit: e.target.checked,
                    })
                  }
                  className="accent-cyan-500"
                />
                <span>Disparar automaticamente quando item da Watchlist bater meta no PIX</span>
              </label>
            </div>
          </div>
        </section>
      </div>

      {/* Save & Test Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80">
        <div className="flex items-center gap-2">
          <button
            type="submit"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-slate-900 dark:bg-cyan-600 text-white cursor-pointer"
          >
            <Save className="w-3.5 h-3.5" />
            Salvar Configurações
          </button>
          <button
            type="button"
            onClick={handleTestDispatch}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold border border-sky-500/40 text-sky-700 dark:text-cyan-300 hover:bg-sky-500/10 cursor-pointer"
          >
            <Send className="w-3.5 h-3.5" />
            Gerar / Disparar Alerta de Teste
          </button>
        </div>

        {waPreviewLink && (
          <a
            href={waPreviewLink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white"
          >
            <MessageCircle className="w-3.5 h-3.5" />
            Abrir Mensagem no WhatsApp Web
          </a>
        )}
      </div>

      {previewMsg && (
        <pre className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-mono whitespace-pre-wrap text-slate-800 dark:text-cyan-100">
          {previewMsg}
        </pre>
      )}
    </form>
  );
};
