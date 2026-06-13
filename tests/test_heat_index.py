"""Heat index regression — checked against published NWS chart values."""

import pytest

from heatline.heat_index import c_to_f, f_to_c, heat_index_c, heat_index_f


def test_temperature_conversions():
    assert c_to_f(37.0) == pytest.approx(98.6, abs=0.05)
    assert f_to_c(212.0) == pytest.approx(100.0, abs=0.05)


@pytest.mark.parametrize(
    "temp_f, rh, expected_f",
    [
        (80, 40, 80),    # NWS chart: ~80
        (90, 70, 106),   # NWS chart: ~106
        (100, 60, 129),  # NWS chart: ~129
        (94, 85, 135),   # Rothfusz regression output (verified by hand)
    ],
)
def test_heat_index_matches_nws_chart(temp_f, rh, expected_f):
    # NWS states the regression carries ±1.3 °F error; allow a small margin.
    assert heat_index_f(temp_f, rh) == pytest.approx(expected_f, abs=3.0)


def test_heat_index_rises_with_humidity():
    # At a fixed hot temperature, more humidity must never lower the heat index.
    values = [heat_index_f(95, rh) for rh in range(20, 95, 5)]
    assert values == sorted(values)


def test_low_temperature_uses_simple_formula():
    # Below 80 °F apparent temperature the simple formula is returned unchanged.
    assert heat_index_f(70, 50) == pytest.approx(69.65, abs=1.0)


def test_celsius_wrapper_roundtrips_units():
    hi_c = heat_index_c(35.0, 60.0)
    hi_f = heat_index_f(c_to_f(35.0), 60.0)
    assert hi_c == pytest.approx(f_to_c(hi_f), abs=0.01)
    assert hi_c > 35.0  # humidity makes it feel hotter than air temperature


def test_invalid_humidity_rejected():
    with pytest.raises(ValueError):
        heat_index_f(90, 150)
    with pytest.raises(ValueError):
        heat_index_f(90, -1)
