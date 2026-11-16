"""Reference-based price gap; a positive gap is not proof of a safe deal."""
from decimal import Decimal

def discount_vs_reference(reference: Decimal, payable: Decimal) -> Decimal | None:
    if reference <= 0 or payable < 0:
        return None
    return ((reference - payable) / reference * Decimal("100")).quantize(Decimal("0.01"))
