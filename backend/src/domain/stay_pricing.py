"""Normalized total price for stays and travel packages."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass(frozen=True)
class StayQuote:
    check_in: date
    check_out: date
    nightly_rate: Decimal
    mandatory_fees: Decimal = Decimal("0")

    def payable_total(self) -> Decimal:
        nights = (self.check_out - self.check_in).days
        if nights <= 0 or min(self.nightly_rate, self.mandatory_fees) < 0:
            raise ValueError("invalid dates or price")
        return self.nightly_rate * nights + self.mandatory_fees
