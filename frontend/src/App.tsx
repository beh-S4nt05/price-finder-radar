import React, { useEffect, useState } from 'react';
import {
  Zap,
  BookmarkPlus,
  Download,
  ExternalLink,
  Filter,
  LayoutGrid,
  List,
  Loader2,
  MessageCircle,
  Plus,
  Search,
  SlidersHorizontal,
} from 'lucide-react';
import { ThemeProvider } from './context/ThemeContext';
import { LotCartProvider, useLotCart } from './context/LotCartContext';
import { ActiveTab, HeaderBar } from './components/HeaderBar';
import { OfferCard } from './components/OfferCard';
import { UrlAndDorksStudio } from './components/UrlAndDorksStudio';
import { WatchlistPanel } from './components/WatchlistPanel';
import { AlertsConfigPanel } from './components/AlertsConfigPanel';
import { ResaleLotDrawer } from './components/ResaleLotDrawer';
import { apiClient } from './services/apiClient';
import {
  AdvancedDorkDTO,
  EngineDescriptor,
  EngineTelemetryDTO,
  MarketSummaryDTO,
  ProductCategory,
  ProductOfferDTO,
  RecentSearchLog,
  SortCriterion,
  WatchlistItemDTO,
} from './types/domain';

const QUICK_REAL_SEARCHES: Array<{
  label: string;
  query: string;
  cat: ProductCategory;
}> = [
  { label: 'SSD Kingston NV3 1TB', query: 'SSD Kingston NV3 1TB', cat: 'informatica' },
  { label: 'Cadeira Escritório Ergonômica', query: 'Cadeira Escritório Ergonômica', cat: 'escritorio' },
  { label: 'Disjuntor WEG', query: 'Disjuntor WEG', cat: 'eletrica' },
  { label: 'Placa de Vídeo RTX 4060', query: 'RTX 4060', cat: 'informatica' },
  { label: 'Impressora EcoTank Epson', query: 'Impressora Epson EcoTank', cat: 'escritorio' },
  { label: 'Filtro de Linha Clamper', query: 'Filtro de Linha Clamper', cat: 'eletrica' },
];

const DashboardContent: React.FC = () => {
  const { addOffer } = useLotCart();
  const [activeTab, setActiveTab] = useState<ActiveTab>('search');

  // Search state
  const [query, setQuery] = useState('SSD Kingston NV3 1TB');
  const [category, setCategory] = useState<ProductCategory>('informatica');
  const [sortBy, setSortBy] = useState<SortCriterion>('lowest_pix');
  const [onlyNational, setOnlyNational] = useState(false);
  const [onlyFreeShipping, setOnlyFreeShipping] = useState(false);
  const [onlyAnomalies, setOnlyAnomalies] = useState(false);
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Live Results State
  const [loading, setLoading] = useState(false);
  const [offers, setOffers] = useState<ProductOfferDTO[]>([]);
  const [summary, setSummary] = useState<MarketSummaryDTO | null>(null);
  const [telemetry, setTelemetry] = useState<EngineTelemetryDTO[]>([]);
  const [dorks, setDorks] = useState<AdvancedDorkDTO[]>([]);
  const [engines, setEngines] = useState<EngineDescriptor[]>([]);
  const [selectedEngines, setSelectedEngines] = useState<string[]>([]);
  const [recentLogs, setRecentLogs] = useState<RecentSearchLog[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItemDTO[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  const notifyToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  const loadSystemMeta = async () => {
    try {
      const [health, wl] = await Promise.all([
        apiClient.getHealth(),
        apiClient.getWatchlist(),
      ]);
      setEngines(health.engines);
      setRecentLogs(health.recent_searches);
      setWatchlist(wl.items);
    } catch {
      // ignore initial race
    }
  };

  const runLiveSearch = async (
    overrideQuery?: string,
    overrideCat?: ProductCategory,
    overrideSort?: SortCriterion
  ) => {
    const q = (overrideQuery ?? query).trim();
    if (q.length < 2) return;
    setLoading(true);
    try {
      const res = await apiClient.searchOffers({
        query: q,
        category: overrideCat ?? category,
        sort_by: overrideSort ?? sortBy,
        enabled_engines: selectedEngines,
        min_price: minPrice ? parseFloat(minPrice) : undefined,
        max_price: maxPrice ? parseFloat(maxPrice) : undefined,
        exclude_used_and_refurbished: true,
        only_free_shipping: onlyFreeShipping,
        only_anomalies: onlyAnomalies,
        only_national_stores: onlyNational,
      });
      setOffers(res.offers);
      setSummary(res.summary);
      setTelemetry(res.telemetry);
      setDorks(res.dorks);
      loadSystemMeta();
    } catch (err) {
      notifyToast(
        err instanceof Error ? err.message : 'Erro ao executar scraping ao vivo.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSystemMeta();
    runLiveSearch('SSD Kingston NV3 1TB', 'informatica', 'lowest_pix');
  }, []);

  const handleSaveOfferToWatchlist = async (offer: ProductOfferDTO) => {
    const target = Number((offer.pix_price * 0.92).toFixed(2));
    await apiClient.addToWatchlist({
      label: offer.title.slice(0, 75),
      query_or_url: query.trim() || offer.title.slice(0, 50),
      is_direct_url: false,
      category,
      target_pix_price: target,
      current_best_pix: offer.pix_price,
      current_best_installment: offer.installment_price,
      best_store_name: offer.store_name,
      best_offer_url: offer.url,
      image_url: offer.image_url,
      notes: `Salvo a partir de ${offer.store_name}`,
    });
    await loadSystemMeta();
    notifyToast(`Monitorando queda abaixo de R$ ${target.toFixed(2)} na Watchlist!`);
  };

  const handleShareOfferWhatsApp = async (offer: ProductOfferDTO) => {
    const res = await apiClient.dispatchAlert({
      title: offer.title,
      store_name: offer.store_name,
      pix_price_brl: offer.pix_price_brl,
      installment_info: offer.installment_label,
      url: offer.url,
      badge:
        offer.anomaly_level === 'POTENTIAL_PRICE_BUG'
          ? 'POSSÍVEL BUG DE PREÇO'
          : 'OFERTA VERIFICADA',
      discount_pct:
        offer.deviation_from_median_pct > 0
          ? offer.deviation_from_median_pct
          : null,
      median_price_brl: summary?.median_pix
        ? summary.median_pix.toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL',
          })
        : null,
    });
    if (res.whatsapp.sent_via_api) {
      notifyToast('Alerta enviado direto via API WhatsApp configurada!');
    } else {
      window.open(res.whatsapp.wa_me_url, '_blank', 'noopener,noreferrer');
    }
  };

  const handleExportCurrentResultsCsv = async () => {
    if (!offers.length) return;
    await apiClient.downloadCsv(
      offers.map((o) => ({
        title: o.title,
        store_name: o.store_name,
        reliability_score: o.reliability.score,
        anomaly_level: o.anomaly_level,
        quantity: 1,
        pix_price: o.pix_price,
        installment_price: o.installment_price,
        installment_label: o.installment_label,
        coupon_code: o.coupon_code,
        url: o.url,
      })),
      30,
      12
    );
    notifyToast('CSV exportado com cálculo de margem de revenda.');
  };

  const toggleEngine = (id: string) => {
    setSelectedEngines((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  return (
    <div className="min-h-screen flex flex-col">
      <HeaderBar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        watchlistCount={watchlist.length}
        enginesOnline={engines.length || 8}
      />

      {toast && (
        <div className="fixed bottom-5 right-5 z-50 px-4 py-2.5 rounded-xl bg-slate-900 dark:bg-cyan-950 border border-cyan-500/40 text-xs font-medium text-white dark:text-cyan-100 shadow-lg">
          {toast}
        </div>
      )}

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        {activeTab === 'search' && (
          <>
            {/* Search Command Surface */}
            <section className="rounded-2xl p-5 sm:p-6 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80 shadow-xs space-y-4">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  runLiveSearch();
                }}
                className="flex flex-col md:flex-row gap-2.5"
              >
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Busque qualquer produto, modelo ou código (ex: SSD Kingston NV3 1TB, Cadeira Ergonômica, Disjuntor WEG)..."
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <select
                  value={category}
                  onChange={(e) => {
                    const nextCat = e.target.value as ProductCategory;
                    setCategory(nextCat);
                  }}
                  className="px-3.5 py-2.5 rounded-xl text-xs font-medium bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200"
                >
                  <option value="all">Todas Categorias</option>
                  <option value="informatica">Informática & Hardware</option>
                  <option value="escritorio">Escritório & Mobiliário</option>
                  <option value="eletrica">Elétrica & Infraestrutura</option>
                </select>

                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold bg-slate-900 hover:bg-slate-800 dark:bg-cyan-600 dark:hover:bg-cyan-500 text-white transition-colors disabled:opacity-60 cursor-pointer"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Varrendo Lojas...
                    </>
                  ) : (
                    'Buscar Menor Preço'
                  )}
                </button>
              </form>

              {/* Quick Preset Pills + Controls Row */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] font-medium text-slate-400 mr-1">
                    Buscas rápidas reais:
                  </span>
                  {QUICK_REAL_SEARCHES.map((item) => (
                    <button
                      key={item.label}
                      type="button"
                      onClick={() => {
                        setQuery(item.query);
                        setCategory(item.cat);
                        runLiveSearch(item.query, item.cat, sortBy);
                      }}
                      className="text-[11px] px-2.5 py-1 rounded-full bg-slate-100 hover:bg-sky-100/80 dark:bg-slate-900 dark:hover:bg-cyan-950/60 border border-slate-200/80 dark:border-slate-800 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
                    >
                      {item.label}
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={sortBy}
                    onChange={(e) => {
                      const nextSort = e.target.value as SortCriterion;
                      setSortBy(nextSort);
                      runLiveSearch(query, category, nextSort);
                    }}
                    className="px-2.5 py-1.5 rounded-lg text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200"
                  >
                    <option value="lowest_pix">Ordenar: Menor Preço PIX</option>
                    <option value="lowest_installment">Ordenar: Menor Parcelado</option>
                    <option value="seller_reliability">Ordenar: Confiabilidade Loja</option>
                    <option value="price_bug_probability">Ordenar: Possível Bug / Promo</option>
                    <option value="biggest_discount">Ordenar: Maior Desconto %</option>
                  </select>

                  <button
                    type="button"
                    onClick={() => setShowFilters((v) => !v)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition-colors cursor-pointer ${
                      showFilters
                        ? 'border-cyan-500 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300'
                        : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300'
                    }`}
                  >
                    <SlidersHorizontal className="w-3.5 h-3.5" />
                    Filtros & Scrapers
                  </button>
                </div>
              </div>

              {/* Expandable Filters, Engines & Google Dorks Bar */}
              {showFilters && (
                <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-4 text-xs">
                  <div className="flex flex-wrap items-center gap-4">
                    <label className="inline-flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={onlyNational}
                        onChange={(e) => setOnlyNational(e.target.checked)}
                        className="accent-cyan-500"
                      />
                      <span>Apenas Lojas Nacionais (NF-e BR)</span>
                    </label>

                    <label className="inline-flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={onlyFreeShipping}
                        onChange={(e) => setOnlyFreeShipping(e.target.checked)}
                        className="accent-cyan-500"
                      />
                      <span>Somente Frete Grátis</span>
                    </label>

                    <label className="inline-flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={onlyAnomalies}
                        onChange={(e) => setOnlyAnomalies(e.target.checked)}
                        className="accent-cyan-500"
                      />
                      <span>Apenas Alertas de Promoção / Possível Bug</span>
                    </label>

                    <div className="flex items-center gap-1.5">
                      <Filter className="w-3.5 h-3.5 text-slate-400" />
                      <input
                        type="number"
                        placeholder="Mín R$"
                        value={minPrice}
                        onChange={(e) => setMinPrice(e.target.value)}
                        className="num-mono w-24 px-2 py-1 rounded bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
                      />
                      <span>até</span>
                      <input
                        type="number"
                        placeholder="Máx R$"
                        value={maxPrice}
                        onChange={(e) => setMaxPrice(e.target.value)}
                        className="num-mono w-24 px-2 py-1 rounded bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
                      />
                      <button
                        type="button"
                        onClick={() => runLiveSearch()}
                        className="px-2.5 py-1 rounded bg-sky-600 dark:bg-cyan-600 text-white font-medium cursor-pointer"
                      >
                        Aplicar
                      </button>
                    </div>
                  </div>

                  {/* Engine Selector Pills */}
                  {engines.length > 0 && (
                    <div>
                      <span className="block text-[11px] text-slate-400 mb-1.5">
                        Adaptadores de Scraping (vazio = todos da categoria ativos em paralelo):
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {engines.map((eng) => {
                          const active =
                            selectedEngines.length === 0 ||
                            selectedEngines.includes(eng.engine_id);
                          return (
                            <button
                              key={eng.engine_id}
                              type="button"
                              onClick={() => toggleEngine(eng.engine_id)}
                              className={`px-2.5 py-1 rounded-md border text-[11px] cursor-pointer ${
                                active
                                  ? 'border-cyan-500/40 bg-cyan-500/10 text-sky-800 dark:text-cyan-200'
                                  : 'border-slate-200 dark:border-slate-800 text-slate-400'
                              }`}
                            >
                              {eng.display_name}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Quick External Search Dorks */}
                  {dorks.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200/70 dark:border-slate-800">
                      <span className="text-[11px] text-slate-400">
                        Auditar via Dork Externo:
                      </span>
                      {dorks.map((d) => (
                        <a
                          key={d.id}
                          href={d.target_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 dark:bg-slate-900 text-[11px] text-slate-700 dark:text-cyan-300 hover:underline"
                        >
                          {d.label}
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* Live Engine Telemetry Ribbon */}
            {telemetry.length > 0 && (
              <div className="flex items-center gap-2 overflow-x-auto pb-1 text-[11px]">
                {telemetry.map((t) => (
                  <div
                    key={t.engine_id}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80 shrink-0 text-slate-600 dark:text-slate-300"
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        t.status === 'ok'
                          ? 'bg-cyan-500'
                          : t.status === 'empty'
                          ? 'bg-slate-400'
                          : 'bg-amber-500'
                      }`}
                    />
                    <span className="font-medium">
                      {t.display_name.split('(')[0].trim()}
                    </span>
                    <span className="num-mono text-slate-400">
                      {t.offers_found} · {(t.duration_ms / 1000).toFixed(1)}s
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Market Comparison Summary KPIs */}
            {summary && (
              <section className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                <div className="rounded-xl p-4 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80">
                  <span className="text-[11px] uppercase tracking-wider text-sky-700 dark:text-cyan-400 font-semibold">
                    Menor Preço PIX
                  </span>
                  <div className="num-mono text-xl sm:text-2xl font-bold mt-1 text-slate-900 dark:text-white">
                    {summary.lowest_pix !== null
                      ? summary.lowest_pix.toLocaleString('pt-BR', {
                          style: 'currency',
                          currency: 'BRL',
                        })
                      : '--'}
                  </div>
                </div>

                <div className="rounded-xl p-4 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80">
                  <span className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-medium">
                    Menor Parcelado
                  </span>
                  <div className="num-mono text-xl sm:text-2xl font-semibold mt-1 text-slate-900 dark:text-slate-100">
                    {summary.lowest_installment !== null
                      ? summary.lowest_installment.toLocaleString('pt-BR', {
                          style: 'currency',
                          currency: 'BRL',
                        })
                      : '--'}
                  </div>
                </div>

                <div className="rounded-xl p-4 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80">
                  <span className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-medium">
                    Mediana do Mercado
                  </span>
                  <div className="num-mono text-xl sm:text-2xl font-semibold mt-1 text-slate-900 dark:text-slate-100">
                    {summary.median_pix !== null
                      ? summary.median_pix.toLocaleString('pt-BR', {
                          style: 'currency',
                          currency: 'BRL',
                        })
                      : '--'}
                  </div>
                </div>

                <div className="rounded-xl p-4 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80">
                  <span className="text-[11px] uppercase tracking-wider text-cyan-700 dark:text-cyan-300 font-semibold">
                    Bugs / Oportunidades
                  </span>
                  <div className="num-mono text-xl sm:text-2xl font-bold mt-1 text-cyan-700 dark:text-cyan-300">
                    {summary.potential_bugs_count}{' '}
                    <span className="text-xs font-normal text-slate-400">
                      bugs · {summary.good_deals_count} promos
                    </span>
                  </div>
                </div>

                <div className="col-span-2 lg:col-span-1 rounded-xl p-4 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80">
                  <span className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-medium">
                    Cobertura Real
                  </span>
                  <div className="num-mono text-xl sm:text-2xl font-semibold mt-1 text-slate-900 dark:text-slate-100">
                    {summary.total_offers}{' '}
                    <span className="text-xs font-normal text-slate-400">
                      em {summary.unique_stores.length} lojas
                    </span>
                  </div>
                </div>
              </section>
            )}

            {/* Results Toolbar */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                {recentLogs.length > 0 && (
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    Última consulta: <strong className="text-slate-700 dark:text-slate-200">{summary ? query : recentLogs[0].query}</strong>
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                {offers.length > 0 && (
                  <button
                    onClick={handleExportCurrentResultsCsv}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0D1424] text-slate-700 dark:text-slate-200 hover:border-cyan-500 cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5 text-cyan-500" />
                    Exportar CSV ({offers.length})
                  </button>
                )}

                <div className="inline-flex rounded-lg p-0.5 bg-white dark:bg-[#0D1424] border border-slate-200 dark:border-slate-800">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-1.5 rounded-md cursor-pointer ${
                      viewMode === 'grid'
                        ? 'bg-slate-900 text-white dark:bg-cyan-500/20 dark:text-cyan-300'
                        : 'text-slate-400'
                    }`}
                  >
                    <LayoutGrid className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setViewMode('table')}
                    className={`p-1.5 rounded-md cursor-pointer ${
                      viewMode === 'table'
                        ? 'bg-slate-900 text-white dark:bg-cyan-500/20 dark:text-cyan-300'
                        : 'text-slate-400'
                    }`}
                  >
                    <List className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            {/* Loading Skeleton or Offers Display */}
            {loading ? (
              <div className="rounded-2xl p-16 text-center bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80 space-y-3">
                <Loader2 className="w-8 h-8 animate-spin text-cyan-500 mx-auto" />
                <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                  Consultando Amazon, Mercado Livre, Terabyteshop, MeuPC, Buscapé, KaBuM!, Kalunga e Copafer em tempo real...
                </p>
                <p className="text-xs text-slate-400">
                  Zero dados fictícios — extraindo e validando preços PIX, parcelamento e confiabilidade ao vivo.
                </p>
              </div>
            ) : offers.length === 0 ? (
              <div className="rounded-2xl p-12 text-center bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80">
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Nenhuma oferta exata encontrada com os filtros atuais. Tente simplificar o termo de busca ou relaxar os filtros de preço.
                </p>
              </div>
            ) : viewMode === 'grid' ? (
              <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {offers.map((offer, idx) => (
                  <OfferCard
                    key={offer.offer_id}
                    offer={offer}
                    rankIndex={idx}
                    medianPix={summary?.median_pix ?? null}
                    onSaveWatchlist={handleSaveOfferToWatchlist}
                    onShareWhatsApp={handleShareOfferWhatsApp}
                  />
                ))}
              </section>
            ) : (
              /* Dense Comparative Table View */
              <section className="rounded-2xl overflow-hidden bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-900/90 text-slate-500 dark:text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-200 dark:border-slate-800">
                    <tr>
                      <th className="py-3 px-4">#</th>
                      <th className="py-3 px-4">Produto</th>
                      <th className="py-3 px-4">Loja & Trust</th>
                      <th className="py-3 px-4">Preço PIX</th>
                      <th className="py-3 px-4">Parcelado</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 text-right">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/80">
                    {offers.map((o, idx) => (
                      <tr
                        key={o.offer_id}
                        className="hover:bg-slate-50/80 dark:hover:bg-slate-900/50 transition-colors"
                      >
                        <td className="py-3 px-4 num-mono text-slate-400">
                          {idx + 1}
                        </td>
                        <td className="py-3 px-4 max-w-md">
                          <a
                            href={o.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-medium text-slate-800 dark:text-slate-100 hover:text-cyan-400 line-clamp-1"
                          >
                            {o.title}
                          </a>
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className="font-semibold text-slate-800 dark:text-slate-200">
                            {o.store_name}
                          </span>
                          <span className="num-mono ml-1.5 text-[11px] text-cyan-600 dark:text-cyan-400">
                            ({o.reliability.score})
                          </span>
                        </td>
                        <td className="py-3 px-4 num-mono font-bold text-slate-900 dark:text-white whitespace-nowrap">
                          {o.pix_price_brl}
                        </td>
                        <td className="py-3 px-4 num-mono text-slate-600 dark:text-slate-300 whitespace-nowrap">
                          {o.installment_label}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          {o.anomaly_level === 'POTENTIAL_PRICE_BUG' ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 font-semibold text-[11px]">
                              <Zap className="w-3 h-3" />
                              BUG -{o.deviation_from_median_pct}%
                            </span>
                          ) : o.anomaly_level === 'GOOD_DEAL' ? (
                            <span className="text-sky-600 dark:text-sky-400 font-medium">
                              -{o.deviation_from_median_pct}% Mediana
                            </span>
                          ) : (
                            <span className="text-slate-400">Mercado</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          <div className="inline-flex items-center gap-1">
                            <button
                              onClick={() => addOffer(o)}
                              title="Adicionar ao Lote"
                              className="p-1.5 rounded hover:bg-slate-200/70 dark:hover:bg-slate-800 cursor-pointer"
                            >
                              <Plus className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleSaveOfferToWatchlist(o)}
                              title="Monitorar na Watchlist"
                              className="p-1.5 rounded hover:bg-slate-200/70 dark:hover:bg-slate-800 cursor-pointer"
                            >
                              <BookmarkPlus className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleShareOfferWhatsApp(o)}
                              title="Enviar no WhatsApp"
                              className="p-1.5 rounded hover:bg-slate-200/70 dark:hover:bg-slate-800 cursor-pointer"
                            >
                              <MessageCircle className="w-3.5 h-3.5" />
                            </button>
                            <a
                              href={o.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1.5 rounded hover:bg-slate-200/70 dark:hover:bg-slate-800"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}
          </>
        )}

        {activeTab === 'urls' && (
          <UrlAndDorksStudio
            onSaveWatchlist={handleSaveOfferToWatchlist}
            onShareWhatsApp={handleShareOfferWhatsApp}
          />
        )}

        {activeTab === 'watchlist' && (
          <WatchlistPanel
            items={watchlist}
            onReload={loadSystemMeta}
            notifyToast={notifyToast}
          />
        )}

        {activeTab === 'alerts' && (
          <AlertsConfigPanel notifyToast={notifyToast} />
        )}
      </main>

      <ResaleLotDrawer />
    </div>
  );
};

export function App() {
  return (
    <ThemeProvider>
      <LotCartProvider>
        <DashboardContent />
      </LotCartProvider>
    </ThemeProvider>
  );
}

export default App;
