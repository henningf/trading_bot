"""Tester for backtest-motoren."""
import pandas as pd
import pytest

from backtest.backtest import Backtest


def test_empty_data_returns_empty_dict(monkeypatch):
    bt = Backtest(10_000)
    monkeypatch.setattr(bt.data_fetcher, "fetch_data", lambda *a, **k: pd.DataFrame())
    assert bt.run("AAPL", "2023-01-01", "2024-01-01") == {}


def test_metrics_without_trades_does_not_crash():
    # Bug 1.4: tomt trade-sett skal gi nullstilte metrics, ikke KeyError
    bt = Backtest(10_000)
    metrics = bt._calculate_metrics()
    assert metrics["total_trades"] == 0
    assert metrics["profitable_trades"] == 0
    assert metrics["losing_trades"] == 0
    assert metrics["win_rate_pct"] == 0
    assert metrics["trades"] == []
    assert metrics["final_capital"] == 10_000


def test_run_with_no_signals_makes_no_trades(monkeypatch, make_ohlcv):
    bt = Backtest(10_000)
    data = make_ohlcv([100.0] * 20)
    data["Signal"] = 0
    monkeypatch.setattr(bt.data_fetcher, "fetch_data", lambda *a, **k: make_ohlcv([100.0] * 20))
    monkeypatch.setattr(bt.signal_generator, "generate_signals", lambda d: data)

    result = bt.run("AAPL", "2023-01-01", "2024-01-01")
    assert result["total_trades"] == 0
    assert result["final_capital"] == 10_000


def test_profitable_trade_accounts_for_commission(monkeypatch, make_ohlcv):
    # Kjøp på bar 5 @ 100, salg på bar 10 @ 120
    close = [100.0] * 20
    close[10] = 120.0
    data = make_ohlcv(close)
    data["Signal"] = 0
    data.iloc[5, data.columns.get_loc("Signal")] = 1
    data.iloc[10, data.columns.get_loc("Signal")] = -1

    bt = Backtest(10_000)
    monkeypatch.setattr(bt.data_fetcher, "fetch_data", lambda *a, **k: data)
    monkeypatch.setattr(bt.signal_generator, "generate_signals", lambda d: data)

    result = bt.run("AAPL", "2023-01-01", "2024-01-01")

    assert result["total_trades"] == 1
    assert result["profitable_trades"] == 1
    assert result["win_rate_pct"] == pytest.approx(100.0)
    # Gevinst skal være positiv, men redusert av to kurtasjer
    assert result["final_capital"] > 10_000
    sells = [t for t in result["trades"] if t["type"] == "SELL"]
    assert sells and sells[0]["commission"] > 0


def test_capital_never_goes_negative(monkeypatch, make_ohlcv):
    # Bug 1.3: gjentatte tap skal aldri presse kapitalen under null
    n = 60
    close = [100.0 - i for i in range(n)]  # kraftig fall
    close = [max(p, 1.0) for p in close]
    data = make_ohlcv(close)
    data["Signal"] = 0
    # Kjøp/salg annenhver bar
    for i in range(5, n - 1, 4):
        data.iloc[i, data.columns.get_loc("Signal")] = 1
        data.iloc[i + 1, data.columns.get_loc("Signal")] = -1

    bt = Backtest(10_000)
    monkeypatch.setattr(bt.data_fetcher, "fetch_data", lambda *a, **k: data)
    monkeypatch.setattr(bt.signal_generator, "generate_signals", lambda d: data)

    result = bt.run("AAPL", "2023-01-01", "2024-01-01")
    assert result["final_capital"] >= 0
    assert all(pv["value"] >= 0 for pv in bt.portfolio_values)


def test_open_position_closed_with_commission(monkeypatch, make_ohlcv):
    # Bug 1.5: åpen posisjon ved slutt skal lukkes som en SELL-trade med kurtasje
    close = [100.0] * 20
    data = make_ohlcv(close)
    data["Signal"] = 0
    data.iloc[5, data.columns.get_loc("Signal")] = 1  # kjøper, selger aldri

    bt = Backtest(10_000)
    monkeypatch.setattr(bt.data_fetcher, "fetch_data", lambda *a, **k: data)
    monkeypatch.setattr(bt.signal_generator, "generate_signals", lambda d: data)

    result = bt.run("AAPL", "2023-01-01", "2024-01-01")
    sells = [t for t in result["trades"] if t["type"] == "SELL"]
    assert len(sells) == 1
    assert sells[0]["commission"] > 0
