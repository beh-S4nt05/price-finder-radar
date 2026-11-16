"""Integration of domain components without external network access.

These tests validate cross-module behavior, not real provider connectivity.
"""
from decimal import Decimal

from src.domain.universal_search import Category, OfferRecord, Verification
from src.domain.source_discovery import SourceCandidate, SourceRegistry, SourceStatus
from src.domain.source_validation import validate_public_https_url
from src.domain.vehicle_matching import Vehicle, matches_vehicle
from src.domain.coupon_engine import Coupon, apply_coupon
from src.domain.opportunity_scoring import discount_vs_reference
from src.domain.travel_pricing import TravelQuote
from src.domain.stay_pricing import StayQuote
from datetime import date


def test_discovery_validation_offer_coupon_and_opportunity():
    registry = SourceRegistry()
    registry.register(SourceCandidate("Example", "example.com", "product", SourceStatus.APPROVED))
    assert len(registry.approved("product")) == 1
    assert validate_public_https_url("https://example.com/item").eligible
    assert not validate_public_https_url("http://localhost/item").eligible

    offer = OfferRecord(category=Category.PRODUCT, title="Test", source="Example",
                        url="https://example.com/item", price={"amount": "100"})
    assert offer.verification == Verification.UNVERIFIED
    assert apply_coupon(offer.price.amount, Coupon("X", Decimal("10"))) == Decimal("100")
    payable = apply_coupon(offer.price.amount, Coupon("X", Decimal("10"), confirmed=True))
    assert payable == Decimal("90")
    assert discount_vs_reference(Decimal("120"), payable) == Decimal("25.00")


def test_vehicle_filter_and_travel_totals():
    vehicle = Vehicle("Honda", "Civic", 2022, 2023, "Preto", 80000, 30000)
    assert matches_vehicle(vehicle, make="honda", model_year=2023, max_mileage_km=40000)
    assert not matches_vehicle(vehicle, manufacture_year=2023)
    assert TravelQuote(Decimal("500"), mandatory_taxes=Decimal("80"),
                       baggage=Decimal("30")).payable_total() == Decimal("610")
    assert StayQuote(date(2026, 12, 10), date(2026, 12, 13),
                     Decimal("200"), Decimal("50")).payable_total() == Decimal("650")
