"""Tester for signalgenerering."""
import pytest

from analysis.signals import SignalGenerator


@pytest.fixture
def gen():
    return SignalGenerator()


def test_signal_values_are_valid(gen, oscillating):
    result = gen.generate_signals(oscillating)
    assert set(result["Signal"].unique()).issubset({-1, 0, 1})


def test_downtrend_ends_with_sell(gen, downtrend):
    assert gen.get_latest_signal(downtrend) == -1


def test_buy_and_sell_conditions_mutually_exclusive(gen, oscillating):
    # Rekonstruer rå-betingelsene og verifiser at de aldri er sanne samtidig,
    # slik at salg aldri overskriver et gyldig kjøp.
    data = gen.generate_signals(oscillating)
    buy = (
        (data["Close"] > data["SMA_20"])
        & (data["SMA_20"] > data["SMA_50"])
        & (data["RSI"] < 70)
        & (data["RSI"] > 30)
    )
    sell = (
        (data["Close"] < data["SMA_20"])
        | (data["SMA_20"] < data["SMA_50"])
        | (data["RSI"] > 70)
    )
    assert not (buy & sell).any()


def test_get_latest_signal_matches_last_row(gen, oscillating):
    full = gen.generate_signals(oscillating)
    assert gen.get_latest_signal(oscillating) == full["Signal"].iloc[-1]


def test_does_not_mutate_input(gen, oscillating):
    before = oscillating.copy()
    gen.generate_signals(oscillating)
    # generate_signals jobber på en kopi og skal ikke endre originalen
    assert list(oscillating.columns) == list(before.columns)
    assert "Signal" not in oscillating.columns
