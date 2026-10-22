"""Domain Value Object: SearchCriteria (Immutable Query & Filtering Specification)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ProductCategory(str, Enum):
    ALL = "all"
    INFORMATICA = "informatica"
    ESCRITORIO = "escritorio"
    ELETRICA = "eletrica"


class SortCriterion(str, Enum):
    LOWEST_PIX = "lowest_pix"
    LOWEST_INSTALLMENT = "lowest_installment"
    SELLER_RELIABILITY = "seller_reliability"
    BIGGEST_DISCOUNT = "biggest_discount"
    PRICE_BUG_PROBABILITY = "price_bug_probability"


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    """Immutable Value Object encapsulating search parameters across all adapters."""

    query: str
    category: ProductCategory = ProductCategory.ALL
    sort_by: SortCriterion = SortCriterion.LOWEST_PIX
    enabled_engines: List[str] = field(default_factory=list)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    exclude_used_and_refurbished: bool = True
    only_free_shipping: bool = False
    only_anomalies: bool = False
    only_national_stores: bool = False
    max_results_per_engine: int = 18

    @property
    def normalized_query(self) -> str:
        return " ".join(self.query.strip().split())
