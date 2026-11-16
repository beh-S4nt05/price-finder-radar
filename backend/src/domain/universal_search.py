"""Typed search contracts shared by future category-specific connectors.

This module defines contracts only. It does not claim any provider is integrated
or that an offer/coupon has been verified.
"""
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


class Category(str, Enum):
    PRODUCT = "product"
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    FLIGHT = "flight"
    CRUISE = "cruise"
    STAY = "stay"
    PACKAGE = "package"


class Verification(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Money(BaseModel):
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="BRL", min_length=3, max_length=3)


class Range(BaseModel):
    minimum: Decimal | None = Field(default=None, ge=0)
    maximum: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum must not exceed maximum")
        return self


class SearchBase(BaseModel):
    query: str | None = Field(default=None, max_length=300)
    price: Range = Field(default_factory=Range)


class VehicleSearch(SearchBase):
    category: Literal[Category.CAR, Category.MOTORCYCLE]
    make: str | None = None
    model: str | None = None
    color: str | None = None
    manufacture_year: int | None = Field(default=None, ge=1900, le=2100)
    model_year: int | None = Field(default=None, ge=1900, le=2100)
    mileage_km: Range = Field(default_factory=Range)


class FlightSearch(SearchBase):
    category: Literal[Category.FLIGHT] = Category.FLIGHT
    origin: str
    destination: str
    departure_date: str
    return_date: str | None = None
    passengers: int = Field(default=1, ge=1, le=20)
    max_stops: int | None = Field(default=None, ge=0)


class CruiseSearch(SearchBase):
    category: Literal[Category.CRUISE] = Category.CRUISE
    departure_port: str | None = None
    destination: str | None = None
    departure_date: str | None = None
    nights: int | None = Field(default=None, ge=1)
    cabin_type: str | None = None
    passengers: int = Field(default=2, ge=1, le=20)


class StaySearch(SearchBase):
    category: Literal[Category.STAY] = Category.STAY
    destination: str
    check_in: str
    check_out: str
    guests: int = Field(default=2, ge=1, le=30)


class ProductSearch(SearchBase):
    category: Literal[Category.PRODUCT] = Category.PRODUCT
    brand: str | None = None


class PackageSearch(SearchBase):
    category: Literal[Category.PACKAGE] = Category.PACKAGE
    origin: str | None = None
    destination: str
    departure_date: str | None = None
    travelers: int = Field(default=2, ge=1, le=20)


SearchRequest = Annotated[
    VehicleSearch | FlightSearch | CruiseSearch | StaySearch | ProductSearch | PackageSearch,
    Field(discriminator="category"),
]


class SourceRecord(BaseModel):
    name: str
    domain: str
    verification: Verification = Verification.UNVERIFIED
    checked_at: datetime | None = None


class OfferRecord(BaseModel):
    category: Category
    title: str
    source: str
    url: str
    price: Money
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verification: Verification = Verification.UNVERIFIED

    @model_validator(mode="after")
    def validate_url(self):
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("offer URL must be absolute HTTPS")
        if parsed.username or parsed.password:
            raise ValueError("credentials in offer URL are forbidden")
        return self


class CouponRecord(BaseModel):
    code: str | None = None
    source: str
    discount_percent: Decimal | None = Field(default=None, ge=0, le=100)
    discount_amount: Money | None = None
    verification: Verification = Verification.UNVERIFIED
    checked_at: datetime | None = None


def final_price(base: Decimal, discount: Decimal = Decimal("0"), fees: Decimal = Decimal("0")) -> Decimal:
    """Payable amount; cashback is intentionally excluded."""
    if min(base, discount, fees) < 0:
        raise ValueError("negative monetary values are forbidden")
    return max(Decimal("0"), base - discount) + fees
