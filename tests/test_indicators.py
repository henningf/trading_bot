"""Tester for tekniske indikatorer."""
import numpy as np
import pandas as pd
import pytest

from analysis.indicators import TechnicalIndicators


@pytest.fixture
def ind():
    return TechnicalIndicators()


def test_sma_matches_manual(make_ohlcv):
    data = make_ohlcv([1, 2, 3, 4, 5])
    sma = TechnicalIndicators.moving_average(data, window=3)
    # Første to verdier er NaN, deretter glidende snitt
    assert pd.isna(sma.iloc[0]) and pd.isna(sma.iloc[1])
    assert sma.iloc[2] == pytest.approx(2.0)  # (1+2+3)/3
    assert sma.iloc[3] == pytest.approx(3.0)  # (2+3+4)/3
    assert sma.iloc[4] == pytest.approx(4.0)  # (3+4+5)/3


def test_sma_nan_count_equals_window_minus_one(uptrend):
    sma = TechnicalIndicators.moving_average(uptrend, window=20)
    assert sma.isna().sum() == 19


def test_ema_first_value_equals_first_price(make_ohlcv):
    data = make_ohlcv([10, 11, 12, 13])
    ema = TechnicalIndicators.exponential_moving_average(data, window=2)
    # Med adjust=False starter EMA på første pris
    assert ema.iloc[0] == pytest.approx(10.0)


def test_rsi_pure_uptrend_is_100(make_ohlcv):
    data = make_ohlcv(list(range(1, 40)))
    rsi = TechnicalIndicators.rsi(data, window=14)
    assert rsi.dropna().eq(100.0).all()


def test_rsi_pure_downtrend_is_zero(make_ohlcv):
    data = make_ohlcv(list(range(40, 1, -1)))
    rsi = TechnicalIndicators.rsi(data, window=14)
    assert rsi.dropna().eq(0.0).all()


def test_rsi_has_no_inf_or_nan_after_warmup(make_ohlcv):
    # Bug 1.8: divisjon på null skal ikke gi inf
    data = make_ohlcv(list(range(1, 40)))
    rsi = TechnicalIndicators.rsi(data, window=14).dropna()
    assert np.isfinite(rsi).all()


def test_rsi_bounded_between_0_and_100(oscillating):
    rsi = TechnicalIndicators.rsi(oscillating, window=14).dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all()


def test_macd_histogram_is_difference(oscillating):
    macd_line, signal_line, histogram = TechnicalIndicators.macd(oscillating)
    pd.testing.assert_series_equal(histogram, macd_line - signal_line, check_names=False)


def test_bollinger_middle_equals_sma_and_symmetric(uptrend):
    upper, middle, lower = TechnicalIndicators.bollinger_bands(uptrend, window=20, num_std=2.0)
    sma = TechnicalIndicators.moving_average(uptrend, window=20)
    pd.testing.assert_series_equal(middle, sma, check_names=False)
    # Båndene er symmetriske rundt midten
    pd.testing.assert_series_equal(upper - middle, middle - lower, check_names=False)
