"""Tester for posisjonsstørrelse og risikostyring."""
import math

import pytest

from risk.position_sizing import PositionSizer
from config.config import (
    RISK_PER_TRADE,
    MAX_POSITION_SIZE,
    IBKR_COMMISSION_PERCENT,
    IBKR_COMMISSION_MINIMUM,
)


def test_position_size_respects_risk_per_trade():
    # Stort gap mellom entry og stop -> risiko per trade er begrensningen
    capital = 10_000
    sizer = PositionSizer(capital)
    entry, stop = 100.0, 50.0  # price_diff = 50

    shares = sizer.calculate_position_size(entry, stop)

    risk_amount = capital * RISK_PER_TRADE
    expected = int(min(risk_amount / abs(entry - stop), capital * MAX_POSITION_SIZE / entry))
    assert shares == expected


def test_position_size_capped_by_max_position():
    # Lite gap -> maks posisjonsstørrelse er begrensningen
    capital = 10_000
    sizer = PositionSizer(capital)
    entry, stop = 100.0, 99.0  # price_diff = 1, risiko-shares blir stort

    shares = sizer.calculate_position_size(entry, stop)

    max_shares = capital * MAX_POSITION_SIZE / entry
    assert shares == int(max_shares)


def test_position_size_zero_when_no_price_diff():
    sizer = PositionSizer(10_000)
    assert sizer.calculate_position_size(100.0, 100.0) == 0


def test_position_size_returns_whole_shares():
    sizer = PositionSizer(10_000)
    shares = sizer.calculate_position_size(33.33, 30.0)
    assert isinstance(shares, int)
    assert shares == math.floor(shares)


def test_commission_uses_minimum_floor():
    # Bug 1.1: liten ordre skal ende på minimumskurtasjen, ikke prosenten
    sizer = PositionSizer(5_000)
    small_order = 10.0  # 10 * 0.004 = 0.04 < minimum
    assert sizer.estimate_commission(small_order) == IBKR_COMMISSION_MINIMUM


def test_commission_uses_percentage_for_large_order():
    sizer = PositionSizer(5_000)
    big_order = 1_000.0
    assert sizer.estimate_commission(big_order) == pytest.approx(big_order * IBKR_COMMISSION_PERCENT)


def test_kelly_zero_when_avg_loss_zero():
    sizer = PositionSizer(5_000)
    assert sizer.calculate_kelly_fraction(win_rate=0.6, avg_win=100, avg_loss=0) == 0


def test_kelly_capped_at_25_percent():
    sizer = PositionSizer(5_000)
    # Svært gunstig edge skal likevel begrenses til 25 %
    frac = sizer.calculate_kelly_fraction(win_rate=0.99, avg_win=1000, avg_loss=1)
    assert frac == pytest.approx(0.25)


def test_kelly_zero_on_negative_edge():
    sizer = PositionSizer(5_000)
    # Lav win-rate med dårlig payoff -> negativ Kelly skal klippes til 0
    frac = sizer.calculate_kelly_fraction(win_rate=0.2, avg_win=1, avg_loss=2)
    assert frac == 0
