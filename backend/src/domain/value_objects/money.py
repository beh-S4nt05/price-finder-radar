"""Domain Value Object: Money (BRL Currency with exact decimal semantics)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, Union


@dataclass(frozen=True, slots=True)
class Money:
    """Immutable Value Object representing monetary amounts (DDD Value Object).

    Enforces non-negative monetary values, exact two-decimal rounding,
    and resilient parsing of Brazilian Real strings (e.g., 'R$ 1.299,90').
    """

    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        normalized = Decimal(str(self.amount)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if normalized < Decimal("0"):
            raise ValueError(f"Monetary amount cannot be negative: {normalized}")
        object.__setattr__(self, "amount", normalized)

    @classmethod
    def from_raw(cls, raw: Union[str, int, float, Decimal, None]) -> Optional["Money"]:
        """Parse Brazilian or numeric price strings into a Money VO, or None if unparseable."""
        if raw is None:
            return None
        if isinstance(raw, (int, float, Decimal)):
            try:
                val = Decimal(str(raw))
                return cls(val) if val > Decimal("0") else None
            except InvalidOperation:
                return None

        text = str(raw).strip()
        if not text:
            return None

        # Extract first monetary pattern like 1.299,90 or 1299.90 or 997,00
        match = re.search(r"(\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2}|\d+\.\d{2}|\d+)", text)
        if not match:
            return None

        token = match.group(1)
        if "," in token and "." in token:
            token = token.replace(".", "").replace(",", ".")
        elif "," in token:
            token = token.replace(",", ".")

        try:
            val = Decimal(token)
            return cls(val) if val > Decimal("0") else None
        except InvalidOperation:
            return None

    @property
    def as_float(self) -> float:
        return float(self.amount)

    def formatted_brl(self) -> str:
        """Format value in Brazilian Real standard: R$ 1.299,90."""
        us_fmt = f"{self.amount:,.2f}"
        br_fmt = us_fmt.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {br_fmt}"

    def discount_percentage_from(self, reference: "Money") -> float:
        """Compute percentage discount relative to a higher reference price."""
        if reference.amount <= Decimal("0") or self.amount >= reference.amount:
            return 0.0
        pct = ((reference.amount - self.amount) / reference.amount) * Decimal("100")
        return round(float(pct), 1)
