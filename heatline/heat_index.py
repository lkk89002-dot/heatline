"""NOAA heat index (Rothfusz regression).

Reference: US National Weather Service, "The Heat Index Equation"
(https://www.weather.gov/safety/heat-index). The regression is valid for
temperatures at or above 80 °F; below that the simpler Steadman formula is
used, following NWS practice. Stated regression error is ±1.3 °F.
"""

from __future__ import annotations

import math


def c_to_f(temp_c: float) -> float:
    return temp_c * 9.0 / 5.0 + 32.0


def f_to_c(temp_f: float) -> float:
    return (temp_f - 32.0) * 5.0 / 9.0


def heat_index_f(temp_f: float, rh_pct: float) -> float:
    """Heat index in °F for an air temperature (°F) and relative humidity (%)."""
    if not 0.0 <= rh_pct <= 100.0:
        raise ValueError(f"relative humidity must be between 0 and 100, got {rh_pct}")

    simple = 0.5 * (temp_f + 61.0 + (temp_f - 68.0) * 1.2 + rh_pct * 0.094)
    if (simple + temp_f) / 2.0 < 80.0:
        return simple

    hi = (
        -42.379
        + 2.04901523 * temp_f
        + 10.14333127 * rh_pct
        - 0.22475541 * temp_f * rh_pct
        - 6.83783e-3 * temp_f ** 2
        - 5.481717e-2 * rh_pct ** 2
        + 1.22874e-3 * temp_f ** 2 * rh_pct
        + 8.5282e-4 * temp_f * rh_pct ** 2
        - 1.99e-6 * temp_f ** 2 * rh_pct ** 2
    )

    if rh_pct < 13.0 and 80.0 <= temp_f <= 112.0:
        hi -= ((13.0 - rh_pct) / 4.0) * math.sqrt((17.0 - abs(temp_f - 95.0)) / 17.0)
    elif rh_pct > 85.0 and 80.0 <= temp_f <= 87.0:
        hi += ((rh_pct - 85.0) / 10.0) * ((87.0 - temp_f) / 2.0)

    return hi


def heat_index_c(temp_c: float, rh_pct: float) -> float:
    """Heat index in °C for an air temperature (°C) and relative humidity (%)."""
    return f_to_c(heat_index_f(c_to_f(temp_c), rh_pct))
