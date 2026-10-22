import React, { useState } from 'react';
import {
  Check,
  Copy,
  Cpu,
  ExternalLink,
  Globe,
  Loader2,
  SearchCode,
} from 'lucide-react';
import { apiClient } from '../services/apiClient';
import {
  AdvancedDorkDTO,
  ProductCategory,
  ProductOfferDTO,
} from '../types/domain';
import { OfferCard } from './OfferCard';

interface UrlAndDorksStudioProps {
  onSaveWatchlist: (offer: ProductOfferDTO) => void;
  onShareWhatsApp: (offer: ProductOfferDTO) => void;
}

export const UrlAndDorksStudio: React.FC<UrlAndDorksStudioProps> = ({
  onSaveWatchlist,
  onShareWhatsApp,
}) => {
  const [urlsText, setUrlsText] = useState(
    'https://meupc.net/peca/HOeL4x/ssd-kingston-nv3-nv3-1tb\nhttps://www.amazon.com.br/dp/B0DBR3DZWG'
  );
  const [forceBrowser, setForceBrowser] = useState(false);
  const [loadingUrls, setLoadingUrls] = useState(false);
  const [inspectedOffers, setInspectedOffers] = useState<ProductOfferDTO[]>([]);
  const [medianPix, setMedianPix] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Advanced Search Dork Studio State
  const [dorkTerm, setDorkTerm] = useState('Cadeira Escritório Ergonômica');
  const [dorkCategory, setDorkCategory] = useState<ProductCategory>('escritorio');
  const [dorks, setDorks] = useState<AdvancedDorkDTO[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleInspect = async (e: React.FormEvent) => {
    e.preventDefault();
    const lines = urlsText
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);
    if (!lines.length) return;

    setLoadingUrls(true);
    setErrorMsg(null);
    try {
      const res = await apiClient.inspectUrls(lines, forceBrowser);
      setInspectedOffers(res.offers);
      setMedianPix(res.summary.median_pix);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Erro ao inspecionar URLs');
    } finally {
      setLoadingUrls(false);
    }
  };

  const handleGenerateDorks = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dorkTerm.trim()) return;
    const res = await apiClient.previewDorks(dorkTerm.trim(), dorkCategory);
    setDorks(res.dorks);
  };

  const copyDork = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  return (
    <div className="space-y-8">
      {/* Section 1: Direct URL & Playwright Chromium Scraper */}
      <section className="rounded-2xl p-6 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Globe className="w-4 h-4 text-sky-600 dark:text-cyan-400" />
              Extrator Real por URL Direta (HTTP TLS + Playwright Chromium)
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Cole até 8 links diretos de produtos (Amazon, KaBuM!, Kalunga, MeuPC, Copafer, VTEX, etc.) para extrair preços ao vivo e comparar lado a lado.
            </p>
          </div>
        </div>

        <form onSubmit={handleInspect} className="space-y-3">
          <textarea
            rows={4}
            value={urlsText}
            onChange={(e) => setUrlsText(e.target.value)}
            placeholder="https://www.amazon.com.br/dp/...&#10;https://meupc.net/peca/..."
            className="w-full rounded-xl p-3 text-xs sm:text-sm font-mono bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-cyan-500"
          />

          <div className="flex flex-wrap items-center justify-between gap-3">
            <label className="inline-flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={forceBrowser}
                onChange={(e) => setForceBrowser(e.target.checked)}
                className="rounded accent-cyan-500"
              />
              <Cpu className="w-3.5 h-3.5 text-cyan-500" />
              <span>Forçar renderização completa em navegador Headless (Playwright Chromium)</span>
            </label>

            <button
              type="submit"
              disabled={loadingUrls}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-slate-900 hover:bg-slate-800 dark:bg-cyan-600 dark:hover:bg-cyan-500 text-white disabled:opacity-50 cursor-pointer"
            >
              {loadingUrls ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Extraindo Páginas ao Vivo...
                </>
              ) : (
                'Extrair & Comparar URLs'
              )}
            </button>
          </div>
        </form>

        {errorMsg && (
          <p className="mt-3 text-xs text-rose-500">{errorMsg}</p>
        )}

        {inspectedOffers.length > 0 && (
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {inspectedOffers.map((off, idx) => (
              <OfferCard
                key={off.offer_id}
                offer={off}
                rankIndex={idx}
                medianPix={medianPix}
                onSaveWatchlist={onSaveWatchlist}
                onShareWhatsApp={onShareWhatsApp}
              />
            ))}
          </div>
        )}
      </section>

      {/* Section 2: Google / Web Advanced Search Dorks Builder */}
      <section className="rounded-2xl p-6 bg-white dark:bg-[#0D1424] border border-slate-200/80 dark:border-slate-800/80">
        <div className="mb-4">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <SearchCode className="w-4 h-4 text-sky-600 dark:text-cyan-400" />
            Gerador de Busca Avançada (Google / Shopping / DuckDuckGo Dorks)
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Gera operadores avançados (<code className="text-cyan-600 dark:text-cyan-400">site:</code>,{' '}
            <code className="text-cyan-600 dark:text-cyan-400">intitle:</code>, exclusão de usados e filtro de cupons) para auditoria cruzada em lojas oficiais.
          </p>
        </div>

        <form onSubmit={handleGenerateDorks} className="flex flex-col sm:flex-row gap-2.5 mb-5">
          <input
            type="text"
            value={dorkTerm}
            onChange={(e) => setDorkTerm(e.target.value)}
            placeholder="Ex: Disjuntor Bipolar WEG 20A, Monitor Dell 27, Cadeira..."
            className="flex-1 px-3.5 py-2 rounded-lg text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500"
          />
          <select
            value={dorkCategory}
            onChange={(e) => setDorkCategory(e.target.value as ProductCategory)}
            className="px-3 py-2 rounded-lg text-xs font-medium bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200"
          >
            <option value="all">Todas as Lojas Oficiais</option>
            <option value="informatica">Informática & Hardware</option>
            <option value="escritorio">Escritório & Papelaria</option>
            <option value="eletrica">Elétrica & Ferramentas</option>
          </select>
          <button
            type="submit"
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-700 dark:bg-cyan-600 dark:hover:bg-cyan-500 text-white cursor-pointer"
          >
            Gerar Operadores Dork
          </button>
        </form>

        {dorks.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {dorks.map((d) => (
              <div
                key={d.id}
                className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800 flex flex-col justify-between gap-3"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                      {d.label}
                    </span>
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-sky-500/10 text-sky-700 dark:text-cyan-300">
                      {d.engine_name}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">
                    {d.description}
                  </p>
                  <pre className="p-2 rounded bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-700 dark:text-cyan-200/90 overflow-x-auto">
                    {d.dork_query}
                  </pre>
                </div>

                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => copyDork(d.id, d.dork_query)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-cyan-500 cursor-pointer"
                  >
                    {copiedId === d.id ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-cyan-500" />
                        Copiado
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        Copiar Dork
                      </>
                    )}
                  </button>
                  <a
                    href={d.target_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-medium bg-slate-900 dark:bg-cyan-600 text-white"
                  >
                    Executar no Buscador
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};
