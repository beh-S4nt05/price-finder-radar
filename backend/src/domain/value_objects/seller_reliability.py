"""Domain Value Object: SellerReliability (Trust Score & Official Store Classification)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TrustTier(str, Enum):
    OFFICIAL_DIRECT = "OFFICIAL_DIRECT"          # Direct official e-commerce (Amazon, KaBuM!, Kalunga, Terabyte, Pichau, Copafer)
    VERIFIED_MARKETPLACE = "VERIFIED_MARKETPLACE" # Verified high-volume marketplace (Mercado Livre, Magalu, Carrefour, Casas Bahia)
    AGGREGATOR_VERIFIED = "AGGREGATOR_VERIFIED"  # Verified via Buscapé / Zoom / MeuPC.net partner stores
    THIRD_PARTY_SELLER = "THIRD_PARTY_SELLER"    # General third-party marketplace seller


OFFICIAL_DIRECT_STORES = {
    "amazon", "amazon.com.br", "kabum", "kabum!", "terabyte", "terabyteshop",
    "pichau", "kalunga", "copafer", "dell", "lenovo", "samsung", "acer",
    "asus", "logitech", "weg", "tramontina", "gigantec", "fgtec", "leroy merlin",
    "fast shop", "fastshop",
}

VERIFIED_MARKETPLACES = {
    "mercado livre", "mercadolivre", "magazine luiza", "magalu",
    "casas bahia", "ponto", "extra", "carrefour", "americanas",
    "webcontinental", "vitrine informatica", "vitrine informática",
}


@dataclass(frozen=True, slots=True)
class SellerReliability:
    """Immutable Value Object encapsulating seller trust evaluation."""

    store_name: str
    seller_name: str
    trust_tier: TrustTier
    score: int  # 0 to 100
    rating: Optional[float] = None  # 0.0 to 5.0
    review_count: Optional[int] = None

    @classmethod
    def evaluate(
        cls,
        store_name: str,
        seller_name: Optional[str] = None,
        rating: Optional[float] = None,
        review_count: Optional[int] = None,
        via_trusted_aggregator: bool = False,
    ) -> "SellerReliability":
        """Domain factory assessing seller reliability score (0..100)."""
        clean_store = (store_name or "Loja Web").strip()
        clean_seller = (seller_name or clean_store).strip()
        norm_store = clean_store.lower()
        norm_seller = clean_seller.lower()

        if any(s in norm_store for s in OFFICIAL_DIRECT_STORES):
            # Official store selling directly gets highest base score
            is_1p = norm_seller in norm_store or norm_store in norm_seller
            base_score = 94 if is_1p else 86
            tier = TrustTier.OFFICIAL_DIRECT if is_1p else TrustTier.VERIFIED_MARKETPLACE
        elif any(m in norm_store for m in VERIFIED_MARKETPLACES):
            base_score = 85
            tier = TrustTier.VERIFIED_MARKETPLACE
        elif via_trusted_aggregator:
            base_score = 80
            tier = TrustTier.AGGREGATOR_VERIFIED
        else:
            base_score = 68
            tier = TrustTier.THIRD_PARTY_SELLER

        # Refine with real customer review signals when available
        bonus = 0
        if rating is not None and rating > 0:
            if rating >= 4.7:
                bonus += 5
            elif rating >= 4.3:
                bonus += 2
            elif rating < 3.8:
                bonus -= 10

        if review_count is not None and review_count >= 100:
            bonus += 1

        final_score = max(35, min(99, base_score + bonus))
        return cls(
            store_name=clean_store,
            seller_name=clean_seller,
            trust_tier=tier,
            score=final_score,
            rating=round(rating, 1) if rating else None,
            review_count=review_count,
        )

    @property
    def badge_label(self) -> str:
        if self.trust_tier == TrustTier.OFFICIAL_DIRECT:
            return "Loja Oficial"
        if self.trust_tier == TrustTier.VERIFIED_MARKETPLACE:
            return "Marketplace Oficial"
        if self.trust_tier == TrustTier.AGGREGATOR_VERIFIED:
            return "Parceiro Verificado"
        return "Vendedor Externo"
