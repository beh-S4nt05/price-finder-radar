export type ProductCategory = 'all' | 'informatica' | 'escritorio' | 'eletrica';

export type SortCriterion =
  | 'lowest_pix'
  | 'lowest_installment'
  | 'seller_reliability'
  | 'biggest_discount'
  | 'price_bug_probability';

export type AnomalyLevel = 'NORMAL' | 'GOOD_DEAL' | 'POTENTIAL_PRICE_BUG';

export interface SellerReliabilityDTO {
  seller_name: string;
  trust_tier: string;
  badge_label: string;
  score: number;
  rating: number | null;
  review_count: number | null;
}

export interface ProductOfferDTO {
  offer_id: string;
  title: string;
  url: string;
  store_name: string;
  scraper_engine: string;
  pix_price: number;
  pix_price_brl: string;
  installment_price: number;
  installment_price_brl: string;
  installments_count: number | null;
  installment_value: number | null;
  installment_label: string;
  original_price: number | null;
  original_price_brl: string | null;
  pix_savings_vs_installment_pct: number;
  listed_discount_pct: number;
  deviation_from_median_pct: number;
  anomaly_level: AnomalyLevel;
  anomaly_reason: string | null;
  reliability: SellerReliabilityDTO;
  image_url: string | null;
  coupon_code: string | null;
  cashback_pct: number | null;
  free_shipping: boolean;
  sku_or_code: string | null;
  captured_at: string;
}

export interface MarketSummaryDTO {
  total_offers: number;
  unique_stores: string[];
  lowest_pix: number | null;
  lowest_installment: number | null;
  median_pix: number | null;
  highest_pix: number | null;
  potential_bugs_count: number;
  good_deals_count: number;
  max_savings_vs_median_brl: number;
}

export interface EngineTelemetryDTO {
  engine_id: string;
  display_name: string;
  status: 'ok' | 'empty' | 'timeout' | 'error';
  offers_found: number;
  duration_ms: number;
  error_detail: string | null;
}

export interface AdvancedDorkDTO {
  id: string;
  engine_name: string;
  label: string;
  dork_query: string;
  target_url: string;
  description: string;
}

export interface SearchResponseDTO {
  query: string;
  summary: MarketSummaryDTO;
  telemetry: EngineTelemetryDTO[];
  dorks: AdvancedDorkDTO[];
  offers: ProductOfferDTO[];
}

export interface PriceSnapshotDTO {
  pix_price: number;
  installment_price: number | null;
  store_name: string;
  offer_url: string;
  captured_at: string;
}

export interface WatchlistItemDTO {
  id: number;
  label: string;
  query_or_url: string;
  is_direct_url: boolean;
  category: string;
  target_pix_price: number;
  current_best_pix: number | null;
  current_best_installment: number | null;
  lowest_historical_pix: number | null;
  is_below_target: boolean;
  best_store_name: string | null;
  best_offer_url: string | null;
  image_url: string | null;
  notes: string;
  notify_whatsapp: boolean;
  notify_webhook: boolean;
  last_checked_at: string | null;
  created_at: string;
  history: PriceSnapshotDTO[];
}

export interface AlertConfigDTO {
  whatsapp_enabled: boolean;
  whatsapp_provider: string;
  whatsapp_recipient_phone: string;
  whatsapp_api_url: string;
  whatsapp_api_token: string;
  webhook_enabled: boolean;
  webhook_format: string;
  webhook_url: string;
  telegram_chat_id: string;
  auto_alert_on_price_bug: boolean;
  auto_alert_on_watchlist_hit: boolean;
}

export interface EngineDescriptor {
  engine_id: string;
  display_name: string;
  target_verticals: string[];
}

export interface RecentSearchLog {
  id: number;
  query: string;
  category: string;
  total_offers: number;
  lowest_pix: number | null;
  median_pix: number | null;
  anomalies_count: number;
  created_at: string;
}

export interface LotEntry {
  offer: ProductOfferDTO;
  quantity: number;
  customResalePrice?: number;
}
