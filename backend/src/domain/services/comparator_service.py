"""Domain Service: CrossStoreComparatorService — Exact-Model Ranking, Filtering & Bug Detection."""
from __future__ import annotations

import re
import statistics
import unicodedata
from dataclasses import dataclass
from typing import List, Optional

from src.domain.entities.product_offer import AnomalyClassification, ProductOffer
from src.domain.value_objects.search_criteria import SearchCriteria, SortCriterion

USED_KEYWORDS = (
    "usado", "recondicionado", "seminovo", "vitrine", "open box",
    "openbox", "defeito", "sucata", "pecas de reposicao",
)

ACCESSORY_NOISE_WORDS = (
    "pelicula", "capinha", "capa ", "case ", "gaveta", "adaptador",
    "baia ", "suporte ", "adesivo", "parafuso", "pasta termica",
)

INTERNATIONAL_STORES = ("aliexpress", "ebay", "techinn", "tradeinn", "shein", "banggood", "tiendamia")

CANONICAL_STORES = {
    "kabum": "KaBuM!",
    "kabum!": "KaBuM!",
    "amazon": "Amazon.com.br",
    "amazon.com.br": "Amazon.com.br",
    "mercado livre": "Mercado Livre",
    "mercadolivre": "Mercado Livre",
    "terabyte": "Terabyteshop",
    "terabyteshop": "Terabyteshop",
    "magalu": "Magazine Luiza",
    "magazine luiza": "Magazine Luiza",
    "webcontinental": "WebContinental",
    "kalunga": "Kalunga",
    "pichau": "Pichau",
    "copafer": "Copafer",
}


def _normalize_text(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text.lower())
    clean = "".join(ch for ch in norm if not unicodedata.combining(ch))
    # Collapse common unit spacing so '1 tb' matches '1tb', '20 a' matches '20a', '500 gb' matches '500gb'
    clean = re.sub(r"(\d+)\s+(tb|gb|mb|w|va|kv|v|a|mm|pol|hz)\b", r"\1\2", clean)
    return clean


def _canonicalize_store(store_name: str, engine_id: str) -> str:
    s = store_name.strip()
    low = s.lower()
    if low.startswith("compare em") or re.match(r"^(?:em\s*)?\d+\s*lojas?$", low):
        return "Buscapé Multi-Lojas" if "buscape" in engine_id else "Zoom Multi-Lojas"
    return CANONICAL_STORES.get(low, s)


@dataclass(frozen=True, slots=True)
class MarketComparisonSummary:
    total_offers: int
    unique_stores: List[str]
    lowest_pix: Optional[float]
    lowest_installment: Optional[float]
    median_pix: Optional[float]
    highest_pix: Optional[float]
    potential_bugs_count: int
    good_deals_count: int
    max_savings_vs_median_brl: float


class CrossStoreComparatorService:
    """Stateless DDD Domain Service orchestrating exact-model multi-store comparison & bug detection."""

    def process_and_rank(
        self, raw_offers: List[ProductOffer], criteria: SearchCriteria
    ) -> tuple[List[ProductOffer], MarketComparisonSummary]:
        query_norm = _normalize_text(criteria.normalized_query)
        stop_words = {"de", "do", "da", "dos", "das", "com", "para", "por", "em", "no", "na", "e", "ou"}
        query_tokens = [
            tok for tok in re.split(r"[\s\-_/]+", query_norm)
            if len(tok) >= 2 and tok not in stop_words
        ]
        # Spec/model tokens containing digits (e.g. 'nv3', '1tb', '4060', '20a', '16gb') are strict identifiers!
        spec_tokens = [tok for tok in query_tokens if any(ch.isdigit() for ch in tok)]
        query_is_accessory = any(w.strip() in query_norm for w in ACCESSORY_NOISE_WORDS)

        deduped_map: dict[str, ProductOffer] = {}
        for offer in raw_offers:
            offer.store_name = _canonicalize_store(offer.store_name, offer.scraper_engine)
            if criteria.only_national_stores and any(
                intl in offer.store_name.lower() for intl in INTERNATIONAL_STORES
            ):
                continue
            title_norm = _normalize_text(offer.title)

            # 1. Exclude used/refurbished items if requested
            if criteria.exclude_used_and_refurbished:
                if any(w in title_norm for w in USED_KEYWORDS):
                    continue

            # 2. Exclude accessory mismatches (e.g. 'Adaptador para SSD') when searching main product
            if not query_is_accessory and any(w in title_norm for w in ACCESSORY_NOISE_WORDS):
                continue

            # 3. Enforce strict model/spec token matching + strong overall token recall
            if query_tokens:
                if spec_tokens and not all(st in title_norm for st in spec_tokens):
                    continue
                matched = sum(1 for tok in query_tokens if tok in title_norm)
                min_required = (
                    len(query_tokens)
                    if len(query_tokens) <= 2
                    else max(2, len(query_tokens) - 1)
                )
                if matched < min_required:
                    continue

            # 4. Explicit price & shipping filters
            pix_val = offer.pix_price.as_float
            if criteria.min_price is not None and pix_val < criteria.min_price:
                continue
            if criteria.max_price is not None and pix_val > criteria.max_price:
                continue
            if criteria.only_free_shipping and not offer.free_shipping:
                continue

            # Deduplicate identical store + normalized title prefix keeping lowest PIX
            dedup_key = f"{_normalize_text(offer.store_name)}::{title_norm[:68]}"
            existing = deduped_map.get(dedup_key)
            if existing is None or offer.pix_price.amount < existing.pix_price.amount:
                deduped_map[dedup_key] = offer

        offers = list(deduped_map.values())
        if not offers:
            empty_summary = MarketComparisonSummary(
                total_offers=0,
                unique_stores=[],
                lowest_pix=None,
                lowest_installment=None,
                median_pix=None,
                highest_pix=None,
                potential_bugs_count=0,
                good_deals_count=0,
                max_savings_vs_median_brl=0.0,
            )
            return [], empty_summary

        reference_pool = [o.pix_price.as_float for o in offers]
        median_pix = round(statistics.median(reference_pool), 2)

        for offer in offers:
            pix_val = offer.pix_price.as_float
            deviation = (
                round(((median_pix - pix_val) / median_pix) * 100.0, 1)
                if median_pix > 0
                else 0.0
            )
            offer.deviation_from_median_pct = deviation
            store_drop = offer.listed_discount_pct
            plausible_same_tier = pix_val >= (median_pix * 0.20)

            if plausible_same_tier and (
                (len(reference_pool) >= 3 and deviation >= 35.0 and offer.reliability.score >= 75)
                or (store_drop >= 42.0 and offer.reliability.score >= 80)
            ):
                offer.anomaly_level = AnomalyClassification.POTENTIAL_PRICE_BUG
                if deviation >= 35.0:
                    offer.anomaly_reason = (
                        f"{deviation:.0f}% abaixo da mediana real do mercado (R$ {median_pix:,.2f}) em loja confiável"
                    )
                else:
                    offer.anomaly_reason = (
                        f"Queda abrupta de -{store_drop:.0f}% sobre tabela original em loja oficial"
                    )
            elif plausible_same_tier and (deviation >= 15.0 or store_drop >= 20.0):
                offer.anomaly_level = AnomalyClassification.GOOD_DEAL
                best_pct = max(deviation, store_drop)
                offer.anomaly_reason = f"Oportunidade real (-{best_pct:.0f}% de economia verificada)"
            else:
                offer.anomaly_level = AnomalyClassification.NORMAL
                offer.anomaly_reason = None

        if criteria.only_anomalies:
            offers = [o for o in offers if o.anomaly_level != AnomalyClassification.NORMAL]

        ranked = self._sort_offers(offers, criteria.sort_by)

        all_pix = [o.pix_price.as_float for o in ranked]
        all_inst = [o.effective_installment_total.as_float for o in ranked]
        unique_stores = sorted({o.store_name for o in ranked})
        bugs_count = sum(
            1 for o in ranked if o.anomaly_level == AnomalyClassification.POTENTIAL_PRICE_BUG
        )
        deals_count = sum(
            1 for o in ranked if o.anomaly_level == AnomalyClassification.GOOD_DEAL
        )
        lowest_pix = min(all_pix) if all_pix else None
        max_savings = round(max(0.0, median_pix - lowest_pix), 2) if lowest_pix is not None else 0.0

        summary = MarketComparisonSummary(
            total_offers=len(ranked),
            unique_stores=unique_stores,
            lowest_pix=lowest_pix,
            lowest_installment=min(all_inst) if all_inst else None,
            median_pix=median_pix,
            highest_pix=max(all_pix) if all_pix else None,
            potential_bugs_count=bugs_count,
            good_deals_count=deals_count,
            max_savings_vs_median_brl=max_savings,
        )
        return ranked, summary

    @staticmethod
    def _sort_offers(offers: List[ProductOffer], criterion: SortCriterion) -> List[ProductOffer]:
        if criterion == SortCriterion.LOWEST_INSTALLMENT:
            return sorted(
                offers,
                key=lambda o: (o.effective_installment_total.amount, -o.reliability.score),
            )
        if criterion == SortCriterion.SELLER_RELIABILITY:
            return sorted(
                offers,
                key=lambda o: (-o.reliability.score, o.pix_price.amount),
            )
        if criterion == SortCriterion.BIGGEST_DISCOUNT:
            return sorted(
                offers,
                key=lambda o: (
                    -max(o.deviation_from_median_pct, o.listed_discount_pct),
                    o.pix_price.amount,
                ),
            )
        if criterion == SortCriterion.PRICE_BUG_PROBABILITY:
            priority = {
                AnomalyClassification.POTENTIAL_PRICE_BUG: 0,
                AnomalyClassification.GOOD_DEAL: 1,
                AnomalyClassification.NORMAL: 2,
            }
            return sorted(
                offers,
                key=lambda o: (
                    priority[o.anomaly_level],
                    -max(o.deviation_from_median_pct, o.listed_discount_pct),
                    o.pix_price.amount,
                ),
            )
        return sorted(
            offers,
            key=lambda o: (o.pix_price.amount, -o.reliability.score),
        )
