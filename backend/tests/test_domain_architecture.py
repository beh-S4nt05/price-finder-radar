"""Unit Tests strictly isolated in tests/ to validate DDD Entities, SOLID Services & CSV Export."""
from src.application.use_cases import ExportOffersCsvUseCase
from src.domain.entities.product_offer import AnomalyClassification, ProductOffer
from src.domain.services.comparator_service import CrossStoreComparatorService
from src.domain.services.dork_builder import AdvancedSearchDorkBuilder
from src.domain.value_objects.money import Money
from src.domain.value_objects.search_criteria import (
    ProductCategory,
    SearchCriteria,
    SortCriterion,
)
from src.domain.value_objects.seller_reliability import SellerReliability, TrustTier


def test_money_value_object_parsing_and_formatting():
    m1 = Money.from_raw("R$ 1.299,90 à vista")
    assert m1 is not None
    assert m1.as_float == 1299.90
    assert m1.formatted_brl() == "R$ 1.299,90"

    m_ref = Money.from_raw(1600)
    assert m_ref is not None
    assert m1.discount_percentage_from(m_ref) == 18.8


def test_seller_reliability_official_vs_marketplace():
    amz = SellerReliability.evaluate("Amazon.com.br", "Amazon.com.br", rating=4.9, review_count=500)
    assert amz.trust_tier == TrustTier.OFFICIAL_DIRECT
    assert amz.score >= 95

    ml = SellerReliability.evaluate("Mercado Livre", "Loja Oficial", rating=4.7)
    assert ml.trust_tier == TrustTier.VERIFIED_MARKETPLACE
    assert ml.score >= 88


def test_comparator_ranking_and_price_bug_anomaly_detection():
    svc = CrossStoreComparatorService()
    offers = [
        ProductOffer(
            title="SSD Kingston NV3 1TB M.2 NVMe PCIe 4.0",
            url="https://terabyteshop.com.br/p/1",
            pix_price=Money(1099.90),
            installment_price=Money(1294.00),
            store_name="Terabyteshop",
            scraper_engine="test",
            reliability=SellerReliability.evaluate("Terabyteshop"),
        ),
        ProductOffer(
            title="SSD Kingston NV3 1TB M.2 NVMe PCIe 4.0",
            url="https://kabum.com.br/p/2",
            pix_price=Money(1149.90),
            installment_price=Money(1352.00),
            store_name="KaBuM!",
            scraper_engine="test",
            reliability=SellerReliability.evaluate("KaBuM!"),
        ),
        ProductOffer(
            title="SSD Kingston NV3 1TB M.2 NVMe PCIe 4.0",
            url="https://amazon.com.br/dp/B0DBR3DZWG",
            pix_price=Money(599.00),  # ~45% below median -> real price bug candidate!
            installment_price=Money(599.00),
            store_name="Amazon.com.br",
            scraper_engine="test",
            reliability=SellerReliability.evaluate("Amazon.com.br", rating=4.9),
        ),
    ]

    ranked, summary = svc.process_and_rank(
        offers, SearchCriteria(query="SSD Kingston NV3 1TB", sort_by=SortCriterion.LOWEST_PIX)
    )
    assert len(ranked) == 3
    assert ranked[0].store_name == "Amazon.com.br"
    assert ranked[0].anomaly_level == AnomalyClassification.POTENTIAL_PRICE_BUG
    assert summary.potential_bugs_count == 1
    assert summary.lowest_pix == 599.00


def test_advanced_dork_builder_and_csv_export():
    dorks = AdvancedSearchDorkBuilder().build_dorks("Disjuntor WEG", ProductCategory.ELETRICA)
    assert len(dorks) >= 4
    assert any("copafer.com.br" in d.dork_query for d in dorks)

    csv_str = ExportOffersCsvUseCase().generate_csv(
        [
            {
                "title": "Disjuntor Bipolar WEG 20A",
                "store_name": "Copafer",
                "pix_price": 24.90,
                "installment_price": 27.50,
                "quantity": 10,
                "url": "https://www.copafer.com.br/p",
            }
        ]
    )
    assert "Disjuntor Bipolar WEG 20A" in csv_str
    assert "249,00" in csv_str
