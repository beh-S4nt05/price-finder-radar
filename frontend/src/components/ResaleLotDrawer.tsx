import React, { useState } from 'react';
import { Download, MessageCircle, Trash2, X } from 'lucide-react';
import { useLotCart } from '../context/LotCartContext';
import { apiClient } from '../services/apiClient';

export const ResaleLotDrawer: React.FC = () => {
  const { entries, isOpen, setOpen, updateQty, removeOffer, clearLot } =
    useLotCart();
  const [markupPct, setMarkupPct] = useState<number>(32);
  const [feePct, setFeePct] = useState<number>(12);

  if (!isOpen) return null;

  const totalPixInvestment = entries.reduce(
    (sum, e) => sum + e.offer.pix_price * e.quantity,
    0
  );
  const grossRevenue = totalPixInvestment * (1 + markupPct / 100);
  const fees = grossRevenue * (feePct / 100);
  const netProfit = grossRevenue - fees - totalPixInvestment;

  const handleExportCsv = async () => {
    if (!entries.length) return;
    await apiClient.downloadCsv(
      entries.map((e) => ({
        title: e.offer.title,
        store_name: e.offer.store_name,
        reliability_score: e.offer.reliability.score,
        anomaly_level: e.offer.anomaly_level,
        quantity: e.quantity,
        pix_price: e.offer.pix_price,
        installment_price: e.offer.installment_price,
        installment_label: e.offer.installment_label,
        coupon_code: e.offer.coupon_code,
        url: e.offer.url,
      })),
      markupPct,
      feePct
    );
  };

  const buildWhatsAppLotLink = () => {
    const lines = [
      '*LOTE DE COMPRA & REVENDA | ICEBERG RADAR*',
      ...entries.map(
        (e, i) =>
          `${i + 1}. [${e.quantity}x] ${e.offer.title.slice(0, 55)} — *${e.offer.pix_price_brl}* (${e.offer.store_name})`
      ),
      `Total PIX: *${totalPixInvestment.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}*`,
      `Lucro Líquido Est.: *${netProfit.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}*`,
    ];
    return `https://wa.me/?text=${encodeURIComponent(lines.join('\n'))}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/60 backdrop-blur-xs">
      <div className="w-full max-w-md bg-white dark:bg-[#0B1120] border-l border-slate-200 dark:border-slate-800 h-full flex flex-col justify-between p-5">
        <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">
              Lote de Compra & Exportação CSV
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Simulador de capital de giro e lucro líquido para revenda
            </p>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-4 space-y-3">
          {entries.length === 0 ? (
            <p className="text-xs text-center text-slate-500 py-12">
              Clique no botão <strong>+</strong> em qualquer oferta para montar sua lista de compra e exportar em CSV.
            </p>
          ) : (
            entries.map((entry) => (
              <div
                key={entry.offer.offer_id}
                className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <span className="text-[11px] font-semibold text-sky-600 dark:text-cyan-400">
                      {entry.offer.store_name}
                    </span>
                    <p className="text-xs font-medium text-slate-800 dark:text-slate-100 line-clamp-2">
                      {entry.offer.title}
                    </p>
                  </div>
                  <button
                    onClick={() => removeOffer(entry.offer.offer_id)}
                    className="text-slate-400 hover:text-rose-500 cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() =>
                        updateQty(entry.offer.offer_id, entry.quantity - 1)
                      }
                      className="w-6 h-6 rounded border border-slate-300 dark:border-slate-700 cursor-pointer"
                    >
                      -
                    </button>
                    <span className="num-mono w-6 text-center font-semibold">
                      {entry.quantity}
                    </span>
                    <button
                      onClick={() =>
                        updateQty(entry.offer.offer_id, entry.quantity + 1)
                      }
                      className="w-6 h-6 rounded border border-slate-300 dark:border-slate-700 cursor-pointer"
                    >
                      +
                    </button>
                  </div>
                  <span className="num-mono font-bold text-slate-900 dark:text-white">
                    {(entry.offer.pix_price * entry.quantity).toLocaleString(
                      'pt-BR',
                      { style: 'currency', currency: 'BRL' }
                    )}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Bottom Simulation & Export Controls */}
        <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-2.5">
            <label>
              <span className="text-slate-500 dark:text-slate-400">
                Markup Revenda (%)
              </span>
              <input
                type="number"
                value={markupPct}
                onChange={(e) => setMarkupPct(Number(e.target.value))}
                className="num-mono mt-1 w-full px-2.5 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
              />
            </label>
            <label>
              <span className="text-slate-500 dark:text-slate-400">
                Taxa Marketplace (%)
              </span>
              <input
                type="number"
                value={feePct}
                onChange={(e) => setFeePct(Number(e.target.value))}
                className="num-mono mt-1 w-full px-2.5 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
              />
            </label>
          </div>

          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-500">Investimento Total (PIX):</span>
              <span className="num-mono font-semibold">
                {totalPixInvestment.toLocaleString('pt-BR', {
                  style: 'currency',
                  currency: 'BRL',
                })}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Lucro Líquido Estimado:</span>
              <span className="num-mono font-bold text-cyan-600 dark:text-cyan-400">
                {netProfit.toLocaleString('pt-BR', {
                  style: 'currency',
                  currency: 'BRL',
                })}
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <button
              onClick={handleExportCsv}
              disabled={entries.length === 0}
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-lg font-semibold bg-slate-900 dark:bg-cyan-600 hover:opacity-95 text-white disabled:opacity-40 cursor-pointer"
            >
              <Download className="w-4 h-4" />
              Baixar Planilha CSV Completa (Excel BR)
            </button>

            {entries.length > 0 && (
              <div className="flex gap-2">
                <a
                  href={buildWhatsAppLotLink()}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 inline-flex items-center justify-center gap-1.5 py-2 rounded-lg font-medium border border-cyan-500/40 text-cyan-700 dark:text-cyan-300"
                >
                  <MessageCircle className="w-3.5 h-3.5" />
                  Enviar Lote no WhatsApp
                </a>
                <button
                  onClick={clearLot}
                  className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 cursor-pointer"
                >
                  Limpar
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
