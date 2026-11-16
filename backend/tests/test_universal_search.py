from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from src.domain.universal_search import (
    Category, CouponRecord, FlightSearch, OfferRecord, Range,
    SearchRequest, VehicleSearch, Verification, final_price,
)


def test_vehicle_filters_keep_manufacture_and_model_year_separate():
    request = VehicleSearch(category=Category.CAR, make="Honda", model="Civic",
                            manufacture_year=2022, model_year=2023,
                            mileage_km=Range(maximum=Decimal("60000")))
    assert request.manufacture_year == 2022
    assert request.model_year == 2023


def test_invalid_range_rejected():
    with pytest.raises(ValidationError):
        Range(minimum=Decimal("100"), maximum=Decimal("50"))


def test_discriminated_flight_request():
    result = TypeAdapter(SearchRequest).validate_python({
        "category": "flight", "origin": "MAO", "destination": "GRU",
        "departure_date": "2026-12-10"
    })
    assert isinstance(result, FlightSearch)


def test_offer_requires_https_and_starts_unverified():
    with pytest.raises(ValidationError):
        OfferRecord(category=Category.PRODUCT, title="Item", source="Site",
                    url="http://example.com/item", price={"amount": "50"})
    offer = OfferRecord(category=Category.PRODUCT, title="Item", source="Site",
                        url="https://example.com/item", price={"amount": "50"})
    assert offer.verification == Verification.UNVERIFIED


def test_coupon_is_not_verified_by_default():
    coupon = CouponRecord(code="SAVE10", source="Example", discount_percent=10)
    assert coupon.verification == Verification.UNVERIFIED


def test_final_price_excludes_cashback_and_rejects_negative_inputs():
    assert final_price(Decimal("2500"), Decimal("250"), Decimal("30")) == Decimal("2280")
    with pytest.raises(ValueError):
        final_price(Decimal("-1"))
