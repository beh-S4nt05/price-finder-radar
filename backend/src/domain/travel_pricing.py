"""Compare travel prices by payable total, not headline fare."""
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class TravelQuote:
    base_fare: Decimal
    mandatory_taxes: Decimal = Decimal("0")
    baggage: Decimal = Decimal("0")
    port_fees: Decimal = Decimal("0")
    required_gratuities: Decimal = Decimal("0")

    def payable_total(self) -> Decimal:
        values = (self.base_fare, self.mandatory_taxes, self.baggage,
                  self.port_fees, self.required_gratuities)
        if any(v < 0 for v in values):
            raise ValueError("negative charge")
        return sum(values, Decimal("0"))
