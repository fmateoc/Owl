"""
The smile starts at an age of the younger spouse (fork, 2026-10-10).

A smile_delay counted from "this year" moved the curve one year later, relative to the
household's ages, every year the same case was run again. The plan now keeps the younger
spouse's age when the smile starts (smile_start_age); a delay is converted to it once.

Tests freeze the date at 2026-01-01 (tests/conftest.py), so ages below are 2026 minus birth year.
"""

import io

import numpy as np
import pytest

import owlplanner as owl
from owlplanner import spending
from owlplanner.config import config_to_plan, config_to_ui, default_config, plan_to_config, ui_to_config


def _single(born, expectancy=95):
    return owl.Plan(["A"], [f"{born}-01-15"], [expectancy], "smile", verbose=False, logstreams=[io.StringIO()])


def _by_age(p):
    ages = p.year_n - int(np.max(p.yobs))
    return dict(zip(ages.tolist(), p.xi_n.tolist(), strict=True))


def test_negative_delay_is_the_tail_of_a_smile_started_before_the_plan():
    """delay = -5: the plan sees the smile from its sixth year on."""
    early = spending.gen_spending_profile("smile", 1.0, 40, 40, delay=-5)
    full = spending.gen_spending_profile("smile", 1.0, 45, 45, delay=0)
    np.testing.assert_allclose(early / early[0], full[5:] / full[5], rtol=1e-12)


def test_a_delay_is_converted_to_the_same_curve_and_an_age():
    p_delay, p_age = _single(1971), _single(1971)  # 55 in 2026
    p_delay.setSpendingProfile("smile", 60, 15, 12, delay=10)
    p_age.setSpendingProfile("smile", 60, 15, 12, start_age=65)
    assert p_delay.smileStartAge == 65 and p_age.smileDelay == 10
    np.testing.assert_allclose(p_delay.xi_n, p_age.xi_n, rtol=1e-12)


def test_the_curve_stays_at_the_same_ages_a_year_later():
    """Someone born a year earlier is the same household run again a year later."""
    now, later = _single(1971), _single(1970, expectancy=96)  # same last year of life, one year older today
    now.setSpendingProfile("smile", 60, 15, 12, start_age=65)
    later.setSpendingProfile("smile", 60, 15, 12, start_age=65)
    a, b = _by_age(now), _by_age(later)
    common = sorted(set(a) & set(b))
    ref = common[0]
    np.testing.assert_allclose([a[k] / a[ref] for k in common], [b[k] / b[ref] for k in common], rtol=1e-12)
    # The old reading (10 years from now for both) would have put the second curve a year later.
    later.setSpendingProfile("smile", 60, 15, 12, delay=10)
    c = _by_age(later)
    assert not np.allclose([a[k] / a[ref] for k in common], [c[k] / c[ref] for k in common])


def test_a_smile_that_started_before_the_plan():
    p = _single(1956)  # 70 in 2026
    p.setSpendingProfile("smile", 60, 15, 12, start_age=65)
    assert p.smileDelay == -5
    full = spending.gen_spending_profile("smile", 1.0, p.N_n + 5, p.N_n + 5, delay=0)
    np.testing.assert_allclose(p.xi_n / p.xi_n[0], full[5:] / full[5], rtol=1e-12)
    diconf = _config(smile_start_age=65)
    diconf["basic_info"]["date_of_birth"] = ["1956-01-15"]
    op = plan_to_config(_plan(diconf))["optimization_parameters"]
    assert (op["smile_start_age"], op["smile_delay"]) == (65, 0)


def test_the_younger_spouse_sets_the_age():
    p = owl.Plan(["A", "B"], ["1960-03-01", "1966-07-01"], [90, 92], "c", verbose=False, logstreams=[io.StringIO()])
    p.setSpendingProfile("smile", 60, 15, 12, start_age=65)
    assert p._youngerAgeAtStart() == 60 and p.smileDelay == 5


def test_start_age_outside_range_refused():
    with pytest.raises(ValueError, match="start age"):
        _single(1971).setSpendingProfile("smile", 60, 15, 12, start_age=130)


def _config(**op):
    diconf = default_config(ni=1)
    diconf["case_name"] = "smile-age"
    diconf["basic_info"]["names"] = ["A"]
    diconf["basic_info"]["date_of_birth"] = ["1971-01-15"]
    diconf["basic_info"]["life_expectancy"] = [95]
    diconf["optimization_parameters"].update(op)
    return diconf


def _plan(diconf):
    return config_to_plan(diconf, verbose=False, logstreams=[io.StringIO()], loadHFP=False)


def test_config_start_age_wins_over_delay():
    p = _plan(_config(smile_delay=3, smile_start_age=65))
    assert (p.smileStartAge, p.smileDelay) == (65, 10)


def test_config_without_start_age_is_converted_and_written_back():
    p = _plan(_config(smile_delay=10))
    op = plan_to_config(p)["optimization_parameters"]
    assert (op["smile_start_age"], op["smile_delay"]) == (65, 10)


def test_clone_with_another_lifespan_keeps_the_start_age():
    p = _plan(_config(smile_start_age=65))
    c = owl.clone(p, expectancy=[100], verbose=False, logstreams=[io.StringIO()])
    assert c.smileStartAge == 65
    a, b = _by_age(p), _by_age(c)
    np.testing.assert_allclose([b[k] / b[55] for k in a], [a[k] / a[55] for k in a], rtol=1e-12)


def test_interface_round_trip_keeps_the_start_age():
    back = ui_to_config(config_to_ui(_config(smile_start_age=67)))
    op = back["optimization_parameters"]
    assert (op["smile_start_age"], op["smile_delay"]) == (67, 12)


def test_interface_converts_an_old_delay():
    ui = config_to_ui(_config(smile_delay=4))
    assert ui["smileStartAge"] == 59
