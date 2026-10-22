import React, { useState } from 'react';
import {
  BookmarkCheck,
  CheckCircle2,
  ExternalLink,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { apiClient } from '../services/apiClient';
import { WatchlistItemDTO } from '../types/domain';

interface WatchlistPanelProps {
  items: WatchlistItemDTO[];
  onReload: () => Promise<void>;
  notifyToast: (msg: string) => void;
}

const Sparkline: React.FC<{ points: number[]; target: number }> = ({
  points,
  target,
}) => {
  if (points.length < 2) {
    return (
      <span className="text-[11px] text-slate-400">
        {points.length === 1 ? '1 coleta registrada' : 'Aguardando varredura'}
      </span>
    );
  }
  const all = target > 0 ? [...points, target] : points;
  const minV = Math.min(...all) * 0.96;
  const maxV = Math.max(...all) * 1.04 || 1;
  const w = 130;
  const h = 34;

  const toCoords = (val: number, idx: number) => {
    const x = (idx / (points.length - 1)) * w;
    const y = h - ((val - minV) / (maxV - minV || 1)) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  };

  const poly = points.map(toCoords).join(' ');
  const targetY =
    target > 0 ? h - ((target - minV) / (maxV - minV || 1)) * h : null;

  return (
    <svg width={w} height={h} className="overflow-visible">
      {targetY !== null && (
        <line
          x1={0}
          y1={targetY}
          x2={w}
          y2={targetY}
          stroke="#06b6d4"
          strokeDasharray="3 3"
          strokeOpacity={0.55}
          strokeWidth={1}
        />
      )}
      <polyline
        fill="none"
        stroke="#0ea5e9"
        strokeWidth={2}
        points={poly}
      />
    </svg>
  );
};

export const WatchlistPanel: React.FC<WatchlistPanelProps> = ({
  items,
  onReload,
  notifyToast,
}) => {
  const [label, setLabel] = useState('');
  const [queryOrUrl, setQueryOrUrl] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [category, setCategory] = useState('informatica');
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [checkingAll, setCheckingAll] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!label.trim() || !queryOrUrl.trim()) return;
    const isUrl = /^https?:\/\//i.test(queryOrUrl.trim());
    await apiClient.addToWatchlist({
      label: label.trim(),
      query_or_url: queryOrUrl.trim(),
      is_direct_url: isUrl,
      category,
      target_pix_price: parseFloat(targetPrice) || 0,
    });
    setLabel('');
    setQueryOrUrl('');
    setTargetPrice('');
    await onReload();
    notifyToast('Radar adicionado à Watchlist SQLite.');
  };

  const handleCheckOne = async (id: number) => {
    setCheckingId(id);
    try {
      await apiClient.checkWatchlistItem(id);
      await onReload();
      notifyToast('Preço atualizado via scraping real e salvo no histórico.');
    } finally {
      setCheckingId(null);
    }
  };

  const handleCheckAll = async () => {
    setCheckingAll(true);
    try {
      await apiClient.checkAllWatchlist();
      await onReload();
      notifyToast('Todos os itens da Watchlist foram varridos ao vivo.');
    } finally {
      setCheckingAll(false);
    }
  };

  const handleDelete = async (id: number) => {
    await apiClient.deleteWatchlistItem(id);
    await onReload();
  };

  return (
    <div className="space-y-6">
      {/* Add New Radar Card */}
      <section className="rounded-2xl p-6 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <BookmarkCheck className="w-4 h-4 text-sky-600 dark:text-cyan-400" />
              Watchlist & Histórico Persistente (SQLite)
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Cadastre um termo de busca ou URL direta de produto com preço-alvo no PIX para disparo automático de alertas.
            </p>
          </div>

          {items.length > 0 && (
            <button
              onClick={handleCheckAll}
              disabled={checkingAll}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-700 dark:bg-cyan-600 dark:hover:bg-cyan-500 text-white disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${checkingAll ? 'animate-spin' : ''}`} />
              <span>{checkingAll ? 'Varrendo Lojas...' : 'Varrer Todos Agora'}</span>
            </button>
          )}
        </div>

        <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-12 gap-2.5">
          <input
            type="text"
            placeholder="Nome de referência (ex: SSD NV3 Estoque)"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="sm:col-span-3 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
          />
          <input
            type="text"
            placeholder="Termo de busca ou URL direta https://..."
            value={queryOrUrl}
            onChange={(e) => setQueryOrUrl(e.target.value)}
            className="sm:col-span-4 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
          />
          <input
            type="number"
            step="0.01"
            placeholder="Meta PIX R$ (ex: 850)"
            value={targetPrice}
            onChange={(e) => setTargetPrice(e.target.value)}
            className="num-mono sm:col-span-2 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="sm:col-span-2 px-2.5 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200"
          >
            <option value="informatica">Informática</option>
            <option value="escritorio">Escritório</option>
            <option value="eletrica">Elétrica</option>
            <option value="all">Geral</option>
          </select>
          <button
            type="submit"
            className="sm:col-span-1 inline-flex items-center justify-center gap-1 px-3 py-2 rounded-lg text-xs font-semibold bg-slate-900 dark:bg-cyan-600 text-white cursor-pointer"
          >
            <Plus className="w-4 h-4" />
          </button>
        </form>
      </section>

      {/* Watchlist Items Table / Cards */}
      {items.length === 0 ? (
        <div className="rounded-2xl p-12 text-center bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Nenhum produto monitorado ainda. Salve ofertas direto da busca ou adicione um radar acima.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="rounded-xl p-4 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80 flex flex-col lg:flex-row lg:items-center justify-between gap-4"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-sm text-slate-900 dark:text-white">
                    {item.label}
                  </span>
                  {item.is_below_target && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-700 dark:text-cyan-300">
                      <CheckCircle2 className="w-3 h-3" />
                      META ATINGIDA
                    </span>
                  )}
                  <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                    {item.is_direct_url ? 'URL Direta' : `Busca: ${item.query_or_url}`}
                  </span>
                </div>

                {item.best_store_name && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    Melhor oferta atual em <strong className="text-slate-700 dark:text-slate-200">{item.best_store_name}</strong>
                    {item.lowest_historical_pix !== null && (
                      <>
                        {' · '}Menor histórico:{' '}
                        <span className="num-mono">
                          {item.lowest_historical_pix.toLocaleString('pt-BR', {
                            style: 'currency',
                            currency: 'BRL',
                          })}
                        </span>
                      </>
                    )}
                  </p>
                )}
              </div>

              {/* Sparkline */}
              <div className="shrink-0">
                <Sparkline
                  points={item.history.map((h) => h.pix_price)}
                  target={item.target_pix_price}
                />
              </div>

              {/* Prices + Actions */}
              <div className="flex items-center gap-4 shrink-0">
                <div className="text-right">
                  <span className="block text-[10px] uppercase text-slate-400">
                    Atual PIX / Meta
                  </span>
                  <span className="num-mono text-sm font-bold text-slate-900 dark:text-white">
                    {item.current_best_pix !== null
                      ? item.current_best_pix.toLocaleString('pt-BR', {
                          style: 'currency',
                          currency: 'BRL',
                        })
                      : '--'}
                  </span>
                  <span className="num-mono text-xs text-sky-600 dark:text-cyan-400 ml-1.5">
                    / {item.target_pix_price > 0 ? `R$ ${item.target_pix_price.toFixed(2)}` : 'Sem teto'}
                  </span>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleCheckOne(item.id)}
                    disabled={checkingId === item.id}
                    title="Consultar lojas ao vivo agora"
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-900 dark:bg-cyan-600 text-white disabled:opacity-50 cursor-pointer"
                  >
                    {checkingId === item.id ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3.5 h-3.5" />
                    )}
                    <span>Varrer</span>
                  </button>

                  {item.best_offer_url && (
                    <a
                      href={item.best_offer_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}

                  <button
                    onClick={() => handleDelete(item.id)}
                    className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-rose-500 cursor-pointer"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
