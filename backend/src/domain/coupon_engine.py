"""Only confirmed eligible coupons affect the advertised payable price."""
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Coupon:
    code: str
    amount_off: Decimal
    minimum_spend: Decimal = Decimal("0")
    confirmed: bool = False

def apply_coupon(price: Decimal, coupon: Coupon) -> Decimal:
    if price < 0 or coupon.amount_off < 0 or coupon.minimum_spend < 0:
        raise ValueError("negative monetary value")
    if not coupon.confirmed or price < coupon.minimum_spend:
        return price
    return max(Decimal("0"), price - coupon.amount_off)
