"""Felles fixtures for testpakken.

Alle fixtures lager syntetiske prisserier slik at testene er deterministiske
og ikke avhenger av nettverk eller eksterne tjenester.
"""
import numpy as np
import pandas as pd
import pytest


def _ohlcv_from_close(close: np.ndarray) -> pd.DataFrame:
    """Bygger en realistisk OHLCV-DataFrame fra en close-serie."""
    close = np.asarray(close, dtype=float)
    n = len(close)
    index = pd.date_range("2023-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": np.full(n, 1_000_000),
        },
        index=index,
    )


@pytest.fixture
def uptrend():
    """Jevnt stigende marked."""
    return _ohlcv_from_close(np.linspace(100, 160, 120))


@pytest.fixture
def downtrend():
    """Jevnt fallende marked."""
    return _ohlcv_from_close(np.linspace(160, 100, 120))


@pytest.fixture
def flat():
    """Flatt marked."""
    return _ohlcv_from_close(np.full(120, 100.0))


@pytest.fixture
def oscillating():
    """Svingende marked med svak oppgang — gir blandede signaler og moderat RSI."""
    x = np.arange(120)
    close = 100 + 0.25 * x + 3 * np.sin(x / 2)
    return _ohlcv_from_close(close)


@pytest.fixture
def make_ohlcv():
    """Factory: lar en test bygge OHLCV fra en egendefinert close-liste."""
    return _ohlcv_from_close
