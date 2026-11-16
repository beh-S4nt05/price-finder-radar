"""Pure vehicle filters, suitable for real offers after provider normalization."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Vehicle:
    make: str
    model: str
    manufacture_year: int
    model_year: int
    color: str
    price: float
    mileage_km: int

def matches_vehicle(vehicle: Vehicle, *, make=None, model=None, color=None,
                    manufacture_year=None, model_year=None, max_price=None,
                    max_mileage_km=None):
    checks = [
        make is None or vehicle.make.casefold() == make.casefold(),
        model is None or model.casefold() in vehicle.model.casefold(),
        color is None or vehicle.color.casefold() == color.casefold(),
        manufacture_year is None or vehicle.manufacture_year == manufacture_year,
        model_year is None or vehicle.model_year == model_year,
        max_price is None or vehicle.price <= max_price,
        max_mileage_km is None or vehicle.mileage_km <= max_mileage_km,
    ]
    return all(checks)
