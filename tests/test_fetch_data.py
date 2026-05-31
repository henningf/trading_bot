"""Tester for datainnhenting (yfinance er mocket — ingen nettverk)."""
import pandas as pd
import pytest

import data.fetch_data as fetch_module
from data.fetch_data import DataFetcher


def _multiindex_frame():
    """Etterligner yfinance-svar med MultiIndex-kolonner (Price, Ticker)."""
    index = pd.date_range("2023-01-01", periods=3, freq="D")
    columns = pd.MultiIndex.from_product(
        [["Open", "High", "Low", "Close", "Volume"], ["AAPL"]]
    )
    return pd.DataFrame(
        [[1, 2, 0, 1.5, 100], [2, 3, 1, 2.5, 200], [3, 4, 2, 3.5, 300]],
        index=index,
        columns=columns,
    )


def test_fetch_flattens_multiindex(monkeypatch):
    monkeypatch.setattr(fetch_module.yf, "download", lambda *a, **k: _multiindex_frame())
    df = DataFetcher().fetch_data("AAPL", "2023-01-01", "2023-01-04")
    assert not isinstance(df.columns, pd.MultiIndex)
    assert "Close" in df.columns
    assert len(df) == 3


def test_fetch_empty_returns_empty_frame(monkeypatch):
    monkeypatch.setattr(fetch_module.yf, "download", lambda *a, **k: pd.DataFrame())
    df = DataFetcher().fetch_data("AAPL", "2023-01-01", "2023-01-04")
    assert df.empty


def test_fetch_handles_exception(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("nettverksfeil")

    monkeypatch.setattr(fetch_module.yf, "download", boom)
    df = DataFetcher().fetch_data("AAPL", "2023-01-01", "2023-01-04")
    assert df.empty


def test_get_latest_price_handles_multiindex(monkeypatch):
    # Bug 1.7: skal flate ut MultiIndex og returnere en skalar float
    monkeypatch.setattr(fetch_module.yf, "download", lambda *a, **k: _multiindex_frame())
    price = DataFetcher().get_latest_price("AAPL")
    assert isinstance(price, float)
    assert price == pytest.approx(3.5)  # siste Close


def test_get_latest_price_empty_returns_none(monkeypatch):
    monkeypatch.setattr(fetch_module.yf, "download", lambda *a, **k: pd.DataFrame())
    assert DataFetcher().get_latest_price("AAPL") is None


def test_fetch_multiple_returns_dict(monkeypatch):
    monkeypatch.setattr(fetch_module.yf, "download", lambda *a, **k: _multiindex_frame())
    result = DataFetcher().fetch_multiple(["AAPL", "MSFT"], "2023-01-01", "2023-01-04")
    assert set(result.keys()) == {"AAPL", "MSFT"}
    assert all(isinstance(v, pd.DataFrame) for v in result.values())
