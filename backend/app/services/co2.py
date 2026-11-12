"""Approximate CO2e — demonstration emission factors, not verified LCA."""

EF_KG_PER_TKM = {
    "rail": 0.028,
    "sea": 0.016,
    "road": 0.095,
    "port_handling": 0.005,
}

ASSUMPTIONS = [
    "Демонстрационные коэффициенты EF кг CO₂e / т·км",
    "Не верифицированный LCA; единицы: кг CO₂e",
    "port_handling использует условный EF на км прокси расстояния",
]


def estimate_leg_co2e_kg(mode: str, distance_km: float, cargo_tonnes: float) -> float:
    ef = EF_KG_PER_TKM.get(mode, 0.05)
    return round(distance_km * ef * cargo_tonnes, 1)


def estimate_route_co2e_kg(legs: list[dict], cargo_tonnes: float) -> float:
    total = 0.0
    for leg in legs:
        total += estimate_leg_co2e_kg(leg["mode"], float(leg.get("distance_km", 0)), cargo_tonnes)
    return round(total, 1)
