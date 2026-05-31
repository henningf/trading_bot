"""Tjenestelag for gjenbrukbar backtest- og trading-logikk."""

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from analysis.signals import SignalGenerator
from backtest.backtest import Backtest
from config.config import (
    BACKTEST_END_DATE,
    BACKTEST_START_DATE,
    START_CAPITAL,
    STOCK_SYMBOLS,
)
from data.fetch_data import DataFetcher
from execution.broker import IBKRBroker
from utils.logger import logger


def parse_symbols(raw_symbols: str | list[str] | tuple[str, ...] | None) -> list[str]:
    """Normaliserer symbol-input til en ryddig liste uten tomme elementer."""
    if raw_symbols is None:
        return list(STOCK_SYMBOLS)

    if isinstance(raw_symbols, str):
        candidates = raw_symbols.split(",")
    else:
        candidates = list(raw_symbols)

    return [symbol.strip().upper() for symbol in candidates if symbol and symbol.strip()]


def run_backtests(
    symbols: str | list[str] | tuple[str, ...] | None = None,
    start_date: str = BACKTEST_START_DATE,
    end_date: str = BACKTEST_END_DATE,
    initial_capital: float = START_CAPITAL,
) -> dict[str, dict[str, Any]]:
    """Kjører backtest for en symbol-liste og returnerer resultater per symbol."""
    normalized_symbols = parse_symbols(symbols)
    if not normalized_symbols:
        return {}

    _validate_date_range(start_date, end_date)

    logger.info("Starter backtesting...")
    results_by_symbol: dict[str, dict[str, Any]] = {}

    for symbol in normalized_symbols:
        logger.info(f"\nBacktesting {symbol}...")
        backtest = Backtest(initial_capital=initial_capital)
        results = backtest.run(symbol, start_date, end_date)

        if results:
            logger.info(f"\nResultater for {symbol}:")
            logger.info(f"Avkastning: {results['total_return_pct']:.2f}%")
            logger.info(f"Win rate: {results['win_rate_pct']:.2f}%")
            results_by_symbol[symbol] = results
        else:
            logger.warning(f"Ingen resultater for {symbol}")

    return results_by_symbol


def fetch_live_overview() -> dict[str, Any]:
    """Henter enkel live-oversikt fra IBKR (konto + posisjoner)."""
    broker = IBKRBroker()
    if not broker.connect():
        return {
            "connected": False,
            "account_summary": None,
            "positions": [],
        }

    try:
        account_summary = broker.get_account_summary()
        positions = broker.get_positions()
        serialized_positions = [_serialize_position(pos) for pos in positions]
        return {
            "connected": True,
            "account_summary": account_summary,
            "positions": serialized_positions,
        }
    finally:
        broker.disconnect()


def get_default_signal_window(days_back: int = 180) -> tuple[str, str]:
    """Returnerer et fornuftig default-vindu for signalvurdering."""
    end = date.today()
    start = end - timedelta(days=days_back)
    return start.isoformat(), end.isoformat()


def get_signal_overview(
    symbols: str | list[str] | tuple[str, ...] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    owned_symbols: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Analyserer symbols og returnerer siste signal + anbefalt handling."""
    normalized_symbols = parse_symbols(symbols)
    if not normalized_symbols:
        return []

    if start_date is None or end_date is None:
        start_date, end_date = get_default_signal_window()

    _validate_date_range(start_date, end_date)

    owned_set = {symbol.upper() for symbol in (owned_symbols or [])}
    data_fetcher = DataFetcher()
    signal_generator = SignalGenerator()

    overview: list[dict[str, Any]] = []
    for symbol in normalized_symbols:
        try:
            overview.append(
                _analyze_symbol_signal(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    owned_set=owned_set,
                    data_fetcher=data_fetcher,
                    signal_generator=signal_generator,
                )
            )
        except Exception as exc:
            logger.error(f"Signalanalyse feilet for {symbol}: {exc}")
            overview.append(_build_error_signal_row(symbol, symbol in owned_set, str(exc)))

    return overview


def pair_backtest_trades(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parer BUY/SELL-trades slik at man ser foreslått inn/ut-dato tydelig."""
    pairs: list[dict[str, Any]] = []
    open_trade: dict[str, Any] | None = None

    for trade in trades:
        trade_type = trade.get("type")
        if trade_type == "BUY":
            open_trade = trade
            continue

        if trade_type == "SELL" and open_trade:
            buy_price = float(open_trade.get("price", 0.0))
            sell_price = float(trade.get("price", 0.0))
            shares = int(open_trade.get("shares", 0))

            buy_commission = float(open_trade.get("commission", 0.0))
            sell_commission = float(trade.get("commission", 0.0))
            gross_pnl = (sell_price - buy_price) * shares
            net_pnl = gross_pnl - buy_commission - sell_commission

            pairs.append(
                {
                    "symbol": open_trade.get("symbol"),
                    "buy_date": _to_iso_datetime(open_trade.get("date")),
                    "sell_date": _to_iso_datetime(trade.get("date")),
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "shares": shares,
                    "gross_pnl": gross_pnl,
                    "net_pnl": net_pnl,
                    "profit_pct": trade.get("profit_pct"),
                }
            )
            open_trade = None

    return pairs


def _serialize_position(position: Any) -> dict[str, Any]:
    """Konverterer IB-insync position-objekt til en enkel dict for GUI."""
    try:
        contract = position.contract
        return {
            "symbol": contract.symbol,
            "currency": getattr(contract, "currency", ""),
            "exchange": getattr(contract, "exchange", ""),
            "position": float(position.position),
            "avg_cost": float(position.avgCost),
        }
    except Exception:
        return {
            "symbol": "UNKNOWN",
            "currency": "",
            "exchange": "",
            "position": 0.0,
            "avg_cost": 0.0,
        }


def _signal_to_label(signal_value: int) -> str:
    if signal_value == 1:
        return "BUY"
    if signal_value == -1:
        return "SELL"
    return "HOLD"


def _recommend_action(signal_value: int, in_position: bool) -> str:
    if signal_value == 1 and not in_position:
        return "BUY_NOW"
    if signal_value == 1 and in_position:
        return "HOLD_POSITION"
    if signal_value == -1 and in_position:
        return "SELL_NOW"
    if signal_value == -1 and not in_position:
        return "WAIT"
    return "HOLD"


def _build_signal_reason(
    close: float | None,
    sma_20: float | None,
    sma_50: float | None,
    rsi: float | None,
    signal_value: int,
    in_position: bool,
) -> str:
    conditions: list[str] = []
    if close is not None and sma_20 is not None:
        conditions.append(f"Close>SMA20={close > sma_20}")
    if sma_20 is not None and sma_50 is not None:
        conditions.append(f"SMA20>SMA50={sma_20 > sma_50}")
    if rsi is not None:
        conditions.append(f"30<RSI<70={30 < rsi < 70}")
        conditions.append(f"RSI>70={rsi > 70}")

    signal_label = _signal_to_label(signal_value)
    position_label = "IN_POSITION" if in_position else "NO_POSITION"
    return f"{signal_label} | {position_label} | " + ", ".join(conditions)


def _to_iso_datetime(value: Any) -> str:
    """Sikker serialisering av pandas Timestamp/datetime til string."""
    try:
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)
    except Exception:
        return ""


def _analyze_symbol_signal(
    symbol: str,
    start_date: str,
    end_date: str,
    owned_set: set[str],
    data_fetcher: DataFetcher,
    signal_generator: SignalGenerator,
) -> dict[str, Any]:
    """Returnerer signalrad for ett symbol."""
    data = data_fetcher.fetch_data(symbol, start_date, end_date)
    in_position = symbol in owned_set
    if data.empty:
        return _build_no_data_signal_row(symbol, in_position)

    signal_data = signal_generator.generate_signals(data)
    latest = signal_data.iloc[-1]

    signal_value = int(latest["Signal"])
    signal_label = _signal_to_label(signal_value)
    action = _recommend_action(signal_value, in_position)

    latest_close = _safe_float(latest.get("Close"))
    latest_rsi = _safe_float(latest.get("RSI"))
    latest_sma_20 = _safe_float(latest.get("SMA_20"))
    latest_sma_50 = _safe_float(latest.get("SMA_50"))

    return {
        "symbol": symbol,
        "status": "OK",
        "latest_date": signal_data.index[-1].date().isoformat(),
        "latest_close": latest_close,
        "latest_signal": signal_label,
        "recommended_action": action,
        "in_position": in_position,
        "rsi": latest_rsi,
        "sma_20": latest_sma_20,
        "sma_50": latest_sma_50,
        "reason": _build_signal_reason(
            latest_close,
            latest_sma_20,
            latest_sma_50,
            latest_rsi,
            signal_value,
            in_position,
        ),
    }


def _build_no_data_signal_row(symbol: str, in_position: bool) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "status": "NO_DATA",
        "latest_signal": "NO_DATA",
        "recommended_action": "WAIT",
        "reason": "No market data for selected period",
        "in_position": in_position,
    }


def _build_error_signal_row(symbol: str, in_position: bool, error_text: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "status": "ERROR",
        "latest_signal": "ERROR",
        "recommended_action": "WAIT",
        "reason": error_text,
        "in_position": in_position,
    }


def _safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _validate_date_range(start_date: str, end_date: str) -> None:
    """Validerer at datoformat er korrekt og at start <= slutt."""
    try:
        start = datetime.fromisoformat(start_date).date()
        end = datetime.fromisoformat(end_date).date()
    except ValueError as exc:
        raise ValueError("Dates must be valid ISO format YYYY-MM-DD") from exc

    if start > end:
        raise ValueError(
            f"Start date ({start.isoformat()}) cannot be after end date ({end.isoformat()})"
        )

    today = date.today()
    if start > today:
        raise ValueError(
            f"Start date ({start.isoformat()}) cannot be in the future (today is {today.isoformat()})"
        )
