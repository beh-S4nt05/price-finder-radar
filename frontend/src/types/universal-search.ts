/** Search UI contracts; API wiring and actual UI are pending. */
export type Category = 'product' | 'car' | 'motorcycle' | 'flight' | 'cruise' | 'stay' | 'package';
export type Verification = 'unverified' | 'verified' | 'rejected';
export interface MoneyRange { minimum?: number; maximum?: number }
export interface VehicleFilters {
  category: 'car' | 'motorcycle';
  make?: string;
  model?: string;
  manufacture_year?: number;
  model_year?: number;
  color?: string;
  price?: MoneyRange;
  mileage_km?: MoneyRange;
}
export interface OfferSummary {
  category: Category;
  title: string;
  source: string;
  url: string;
  price: number;
  currency: string;
  verification: Verification;
  collected_at: string;
}
