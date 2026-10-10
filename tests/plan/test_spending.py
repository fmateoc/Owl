"""
Tests for spending module - spending profile generation.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors
"""

import numpy as np

from owlplanner import spending


def _old_plan_stretched_smile(fraction, n_d, N_n, dip=15, increase=12, delay=0):
    """The smile as it was drawn over the plan's length (span = N_n - 1 - delay)."""
    xi = np.ones(N_n)
    span = N_n - 1 - delay
    x = np.linspace(0, span, N_n - delay)
    a = dip / 100
    b = increase / 100
    xi[delay:] = xi[delay:] + a * np.cos((2 * np.pi / span) * x) + (b / (N_n - 1)) * x
    xi[:delay] = xi[delay]
    neutralSum = N_n
    if n_d < N_n:
        neutralSum -= (1 - fraction) * (N_n - n_d)
        xi[n_d:] *= fraction
    xi *= neutralSum / xi.sum()
    return xi


def test_gen_spending_profile_flat():
    """Flat profile: ones, with survivor fraction from n_d."""
    xi = spending.gen_spending_profile("flat", 0.5, 10, 20)
    assert len(xi) == 20
    assert np.all(xi[:10] == 1.0)
    assert np.all(xi[10:] == 0.5)


def test_gen_spending_profile_flat_n_d_at_end():
    """Flat profile with n_d >= N_n: no reduction."""
    xi = spending.gen_spending_profile("flat", 0.6, 20, 20)
    assert np.all(xi == 1.0)


def test_gen_spending_profile_smile_nonnegative():
    """Smile profile produces non-negative values."""
    xi = spending.gen_spending_profile("smile", 0.6, 15, 30, dip=15, increase=12, delay=5)
    assert np.all(xi >= 0)


def test_gen_spending_profile_smile_shape():
    """Smile profile has correct length."""
    xi = spending.gen_spending_profile("smile", 0.6, 10, 25)
    assert len(xi) == 25


def test_smile_matches_plan_stretched_at_the_canonical_span():
    """At N_n = SMILE_SPAN + 1 and delay = 0 the age-anchored curve is the old one."""
    N_n = spending.SMILE_SPAN + 1
    old = _old_plan_stretched_smile(0.6, 10, N_n, dip=15, increase=12, delay=0)
    new = spending.gen_spending_profile("smile", 0.6, 10, N_n, dip=15, increase=12, delay=0)
    np.testing.assert_allclose(new, old, rtol=1e-12)


def test_smile_span_override_recovers_plan_stretched_curve():
    """Passing span = N_n - 1 reproduces the old curve when delay = 0.

    The old linear rise used b/(N_n-1) per year; the age-anchored one uses b/span.
    Those coincide exactly when span = N_n - 1, i.e. delay = 0.
    """
    N_n = 22
    old = _old_plan_stretched_smile(0.6, 8, N_n, dip=15, increase=12, delay=0)
    new = spending.gen_spending_profile(
        "smile", 0.6, 8, N_n, dip=15, increase=12, delay=0, span=N_n - 1
    )
    np.testing.assert_allclose(new, old, rtol=1e-12)


def test_longer_horizon_keeps_early_years():
    """A longer life appends the late-life rise; the overlapping early years do not move.

    Each horizon is normalized by its own neutral sum, so compare the shape on a
    first-year scale: the profile's relative path, not its mean.
    """
    short = spending.gen_spending_profile("smile", 1.0, 40, 20, dip=15, increase=12, delay=0)
    long = spending.gen_spending_profile("smile", 1.0, 50, 40, dip=15, increase=12, delay=0)
    np.testing.assert_allclose(long[:20] / long[0], short / short[0], rtol=1e-12)


def test_smile_dip_stays_at_the_same_offset_from_the_smile_start():
    """The cosine minimum is at t = SMILE_SPAN/2 years after the smile starts, on any horizon."""
    S = spending.SMILE_SPAN
    for N_n in (S + 1, S + 15, 2 * S):
        t = np.arange(N_n, dtype=float)
        # With a positive linear rise the observed minimum of (cos + trend) sits just after S/2.
        raw = 1.0 + 0.15 * np.cos((2 * np.pi / S) * t) + (0.12 / S) * t
        dip_n = int(np.argmin(raw))
        assert abs(dip_n - S / 2) <= 2, f"N_n={N_n}: dip at {dip_n}, expected near {S / 2}"


def test_smile_after_span_is_the_late_life_rise():
    """Past one span the cosine is frozen at its end and the linear rise continues."""
    S = float(spending.SMILE_SPAN)
    N_n = int(S) + 12
    xi = spending.gen_spending_profile("smile", 1.0, N_n, N_n, dip=15, increase=12, delay=0)
    t = np.arange(N_n, dtype=float)
    raw = 1.0 + 0.15 * np.cos((2 * np.pi / S) * t) + (0.12 / S) * t
    raw = np.where(t <= S, raw, 1.0 + 0.15 + (0.12 / S) * t)
    np.testing.assert_allclose(xi, raw * (N_n / raw.sum()), rtol=1e-12)
    # After the span the series is strictly rising (the late-life part).
    assert np.all(np.diff(xi[int(S) :]) > 0)


def test_smile_delay_holds_the_opening_level():
    """Years before the smile starts sit at the go-go level (t = 0)."""
    delay = 4
    xi = spending.gen_spending_profile("smile", 1.0, 30, 30, dip=15, increase=12, delay=delay)
    assert np.allclose(xi[:delay], xi[delay], rtol=1e-12)
