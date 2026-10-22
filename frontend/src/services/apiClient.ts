import {
  AdvancedDorkDTO,
  AlertConfigDTO,
  EngineDescriptor,
  MarketSummaryDTO,
  ProductCategory,
  ProductOfferDTO,
  RecentSearchLog,
  SearchResponseDTO,
  SortCriterion,
  WatchlistItemDTO,
} from '../types/domain';

export interface SearchPayload {
  query: string;
  category: ProductCategory;
  sort_by: SortCriterion;
  enabled_engines: string[];
  min_price?: number;
  max_price?: number;
  exclude_used_and_refurbished: boolean;
  only_free_shipping: boolean;
  only_anomalies: boolean;
  only_national_stores: boolean;
}

class PriceRadarApiService {
  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(path, {
      headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
      ...init,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Erro HTTP ${res.status}`);
    }
    return res.json() as Promise<T>;
  }

  async getHealth(): Promise<{
    status: string;
    engines: EngineDescriptor[];
    watchlist_count: number;
    recent_searches: RecentSearchLog[];
  }> {
    return this.request('/api/health');
  }

  async searchOffers(payload: SearchPayload): Promise<SearchResponseDTO> {
    return this.request('/api/search', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async inspectUrls(
    urls: string[],
    forceBrowser: boolean
  ): Promise<{ summary: MarketSummaryDTO; offers: ProductOfferDTO[] }> {
    return this.request('/api/inspect-urls', {
      method: 'POST',
      body: JSON.stringify({ urls, force_browser: forceBrowser }),
    });
  }

  async previewDorks(
    query: string,
    category: ProductCategory
  ): Promise<{ query: string; dorks: AdvancedDorkDTO[] }> {
    const params = new URLSearchParams({ query, category });
    return this.request(`/api/dorks?${params.toString()}`);
  }

  async getWatchlist(): Promise<{ items: WatchlistItemDTO[] }> {
    return this.request('/api/watchlist');
  }

  async addToWatchlist(payload: {
    label: string;
    query_or_url: string;
    is_direct_url: boolean;
    category: string;
    target_pix_price: number;
    current_best_pix?: number | null;
    current_best_installment?: number | null;
    best_store_name?: string | null;
    best_offer_url?: string | null;
    image_url?: string | null;
    notes?: string;
  }): Promise<WatchlistItemDTO> {
    return this.request('/api/watchlist', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateWatchlistTarget(
    id: number,
    targetPixPrice: number,
    notes?: string
  ): Promise<WatchlistItemDTO> {
    return this.request(`/api/watchlist/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ target_pix_price: targetPixPrice, notes }),
    });
  }

  async deleteWatchlistItem(id: number): Promise<void> {
    await this.request(`/api/watchlist/${id}`, { method: 'DELETE' });
  }

  async checkWatchlistItem(id: number): Promise<WatchlistItemDTO> {
    return this.request(`/api/watchlist/${id}/check`, { method: 'POST' });
  }

  async checkAllWatchlist(): Promise<{ items: WatchlistItemDTO[] }> {
    return this.request('/api/watchlist/check-all', { method: 'POST' });
  }

  async getAlertConfig(): Promise<AlertConfigDTO> {
    return this.request('/api/alerts/config');
  }

  async saveAlertConfig(cfg: AlertConfigDTO): Promise<AlertConfigDTO> {
    return this.request('/api/alerts/config', {
      method: 'PUT',
      body: JSON.stringify(cfg),
    });
  }

  async dispatchAlert(payload: {
    title: string;
    store_name: string;
    pix_price_brl: string;
    installment_info: string;
    url: string;
    badge?: string;
    discount_pct?: number | null;
    median_price_brl?: string | null;
  }): Promise<{
    whatsapp: { sent_via_api: boolean; wa_me_url: string; detail?: string };
    webhook: { sent_via_api: boolean };
    formatted_text: string;
  }> {
    return this.request('/api/alerts/dispatch', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async downloadCsv(
    items: Array<Record<string, unknown>>,
    markupPct: number,
    marketplaceFeePct: number
  ): Promise<void> {
    const res = await fetch('/api/export/csv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items,
        markup_pct: markupPct,
        marketplace_fee_pct: marketplaceFeePct,
      }),
    });
    if (!res.ok) throw new Error('Falha ao gerar arquivo CSV');
    const blob = await res.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `iceberg_lote_revenda_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  }
}

export const apiClient = new PriceRadarApiService();
