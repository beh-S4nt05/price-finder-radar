import React, { useState } from 'react';
import {
  Zap,
  BookmarkPlus,
  Calculator,
  ExternalLink,
  MessageCircle,
  Plus,
  ShieldCheck,
  Sparkles,
  Tag,
  Truck,
} from 'lucide-react';
import { ProductOfferDTO } from '../types/domain';
import { useLotCart } from '../context/LotCartContext';

interface OfferCardProps {
  offer: ProductOfferDTO;
  rankIndex: number;
  medianPix: number | null;
  onSaveWatchlist: (offer: ProductOfferDTO) => void;
  onShareWhatsApp: (offer: ProductOfferDTO) => void;
}

export const OfferCard: React.FC<OfferCardProps> = ({
  offer,
  rankIndex,
  medianPix,
  onSaveWatchlist,
  onShareWhatsApp,
}) => {
  const { addOffer } = useLotCart();
  const [showCalc, setShowCalc] = useState(false);
  const [resalePrice, setResalePrice] = useState<string>(() =>
    Math.round(offer.pix_price * 1.32).toString()
  );
  const [feePct, setFeePct] = useState<string>('12');

  const isBug = offer.anomaly_level === 'POTENTIAL_PRICE_BUG';
  const isDeal = offer.anomaly_level === 'GOOD_DEAL';

  const parsedResale = parseFloat(resalePrice) || 0;
  const parsedFee = parseFloat(feePct) || 0;
  const netProfit =
    parsedResale - parsedResale * (parsedFee / 100) - offer.pix_price;
  const roiPct = offer.pix_price > 0 ? (netProfit / offer.pix_price) * 100 : 0;

  return (
    <article
      className={`group flex flex-col justify-between rounded-xl p-4 transition-all border ${
        isBug
          ? 'bg-cyan-50/50 dark:bg-cyan-950/20 border-cyan-400/70 dark:border-cyan-400/50 shadow-sm'
          : 'bg-white dark:bg-[#0D1424] border-slate-200/85 dark:border-slate-800/85 hover:border-sky-400/60 dark:hover:border-cyan-500/40'
      }`}
    >
      {/* Top Row: Rank + Store + Trust Score + Anomaly Pill */}
      <div>
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className="num-mono text-[11px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              #{rankIndex + 1}
            </span>
            <span className="text-xs font-semibold text-slate-800 dark:text-slate-100 truncate">
              {offer.store_name}
            </span>
          </div>

          <div
            title={`${offer.reliability.badge_label} (${offer.reliability.seller_name})`}
            className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800/90 text-[11px] text-slate-700 dark:text-slate-300 shrink-0"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-sky-600 dark:text-cyan-400" />
            <span className="num-mono font-medium">{offer.reliability.score}</span>
          </div>
        </div>

        {/* Anomaly / Coupon / Free Shipping Badges */}
        <div className="flex flex-wrap items-center gap-1.5 mb-3 min-h-[22px]">
          {isBug && (
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md bg-cyan-500/15 text-cyan-800 dark:text-cyan-300 border border-cyan-500/30">
              <Zap className="w-3 h-3" />
              POSSÍVEL BUG ({offer.deviation_from_median_pct > 0 ? `-${offer.deviation_from_median_pct}%` : 'QUEDA'})
            </span>
          )}
          {isDeal && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-sky-500/10 text-sky-700 dark:text-sky-300 border border-sky-500/25">
              <Sparkles className="w-3 h-3" />
               Abaixo da Mediana
            </span>
          )}
          {offer.coupon_code && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/25">
              <Tag className="w-3 h-3" />
              {offer.coupon_code}
            </span>
          )}
          {offer.free_shipping && (
            <span className="inline-flex items-center gap-1 text-[11px] text-slate-600 dark:text-slate-400 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800/70">
              <Truck className="w-3 h-3 text-sky-500" />
              Frete Grátis
            </span>
          )}
        </div>

        {/* Product Thumbnail + Title */}
        <div className="flex gap-3 items-start mb-4">
          <div className="w-16 h-16 rounded-lg bg-white border border-slate-200/80 dark:border-slate-700/60 p-1.5 flex items-center justify-center shrink-0 overflow-hidden">
            {offer.image_url ? (
              <img
                src={offer.image_url}
                alt={offer.title}
                loading="lazy"
                className="w-full h-full object-contain"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).style.display = 'none';
                }}
              />
            ) : (
              <span className="text-[10px] font-medium text-slate-400 text-center">
                SEM FOTO
              </span>
            )}
          </div>
          <a
            href={offer.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium leading-snug text-slate-800 dark:text-slate-100 hover:text-sky-600 dark:hover:text-cyan-300 line-clamp-3 transition-colors"
          >
            {offer.title}
          </a>
        </div>
      </div>

      {/* Pricing Block + Actions */}
      <div>
        <div className="rounded-lg p-3 bg-slate-50 dark:bg-slate-900/80 border border-slate-200/70 dark:border-slate-800/80 mb-3">
          <div className="flex items-baseline justify-between gap-2">
            <div>
              <span className="block text-[10px] uppercase tracking-wider font-semibold text-sky-700 dark:text-cyan-400">
                À Vista no PIX
              </span>
              <span className="num-mono text-xl font-bold text-slate-900 dark:text-white">
                {offer.pix_price_brl}
              </span>
            </div>

            {offer.original_price_brl && offer.original_price && offer.original_price > offer.pix_price && (
              <div className="text-right">
                <span className="block text-[10px] text-slate-400">De</span>
                <span className="num-mono text-xs line-through text-slate-400">
                  {offer.original_price_brl}
                </span>
              </div>
            )}
          </div>

          <div className="mt-1.5 pt-1.5 border-t border-slate-200/70 dark:border-slate-800 flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
            <span>Cartão / Prazo:</span>
            <span className="num-mono font-medium text-slate-800 dark:text-slate-200">
              {offer.installment_label}
            </span>
          </div>

          {medianPix && (
            <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
              <span>vs. Mediana ({medianPix.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}):</span>
              <span
                className={`num-mono font-medium ${
                  offer.deviation_from_median_pct > 0
                    ? 'text-cyan-700 dark:text-cyan-300'
                    : 'text-slate-500'
                }`}
              >
                {offer.deviation_from_median_pct > 0
                  ? `-${offer.deviation_from_median_pct}% mais barato`
                  : `+${Math.abs(offer.deviation_from_median_pct)}%`}
              </span>
            </div>
          )}
        </div>

        {/* Optional Quick Resale Margin Calculator */}
        {showCalc && (
          <div className="mb-3 p-2.5 rounded-lg bg-slate-100/80 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <label className="block">
                <span className="text-[10px] text-slate-500 dark:text-slate-400">
                  Venda (R$)
                </span>
                <input
                  type="number"
                  value={resalePrice}
                  onChange={(e) => setResalePrice(e.target.value)}
                  className="num-mono mt-0.5 w-full px-2 py-1 rounded bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100"
                />
              </label>
              <label className="block">
                <span className="text-[10px] text-slate-500 dark:text-slate-400">
                  Taxa Mkt (%)
                </span>
                <input
                  type="number"
                  value={feePct}
                  onChange={(e) => setFeePct(e.target.value)}
                  className="num-mono mt-0.5 w-full px-2 py-1 rounded bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100"
                />
              </label>
            </div>
            <div className="flex items-center justify-between pt-1 border-t border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Lucro Líquido:</span>
              <span
                className={`num-mono font-semibold ${
                  netProfit > 0 ? 'text-cyan-700 dark:text-cyan-300' : 'text-rose-500'
                }`}
              >
                {netProfit.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })} ({roiPct.toFixed(1)}%)
              </span>
            </div>
          </div>
        )}

        {/* Action Toolbar */}
        <div className="flex items-center gap-1.5">
          <a
            href={offer.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 dark:bg-cyan-600 dark:hover:bg-cyan-500 text-white transition-colors"
          >
            <span>Ir à Loja</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>

          <button
            onClick={() => addOffer(offer)}
            title="Adicionar ao Lote de Compra & Exportação CSV"
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-sky-500 dark:hover:border-cyan-400 text-slate-700 dark:text-slate-200 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
          </button>

          <button
            onClick={() => setShowCalc((v) => !v)}
            title="Simular Margem de Revenda"
            className={`p-1.5 rounded-lg border transition-colors cursor-pointer ${
              showCalc
                ? 'border-cyan-500 bg-cyan-500/15 text-cyan-700 dark:text-cyan-300'
                : 'border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:border-sky-500'
            }`}
          >
            <Calculator className="w-4 h-4" />
          </button>

          <button
            onClick={() => onSaveWatchlist(offer)}
            title="Monitorar Preço na Watchlist SQLite"
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-sky-500 dark:hover:border-cyan-400 text-slate-700 dark:text-slate-200 transition-colors cursor-pointer"
          >
            <BookmarkPlus className="w-4 h-4" />
          </button>

          <button
            onClick={() => onShareWhatsApp(offer)}
            title="Disparar Alerta / Compartilhar no WhatsApp"
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-sky-500 dark:hover:border-cyan-400 text-slate-700 dark:text-slate-200 transition-colors cursor-pointer"
          >
            <MessageCircle className="w-4 h-4" />
          </button>
        </div>
      </div>
    </article>
  );
};
