"""Streamlit GUI for backtesting."""

from datetime import date
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# Ensure project root is importable even when app is started from gui/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.config import BACKTEST_END_DATE, BACKTEST_START_DATE, START_CAPITAL, STOCK_SYMBOLS
from services.trading_service import (
    fetch_live_overview,
    get_default_signal_window,
    get_signal_overview,
    pair_backtest_trades,
    parse_symbols,
    run_backtests,
)


def _to_date(value: str) -> date:
    """Converts YYYY-MM-DD to date object for Streamlit widgets."""
    return date.fromisoformat(value)


st.set_page_config(page_title="Trading Bot GUI", layout="wide")
if "watchlist" not in st.session_state:
    st.session_state.watchlist = list(STOCK_SYMBOLS)

if "live_overview" not in st.session_state:
    st.session_state.live_overview = {
        "connected": False,
        "account_summary": None,
        "positions": [],
    }

if "last_backtest_results" not in st.session_state:
    st.session_state.last_backtest_results = {}

if "signal_table" not in st.session_state:
    st.session_state.signal_table = []


st.title("Trading Bot - Decision Dashboard")
st.caption("Bruk Signal Monitor for hva du bor vurdere a kjope/selge na, og Backtest for historiske BUY/SELL-datoer.")

with st.sidebar:
    st.header("Watchlist Setup")

    add_symbol = st.text_input("Add symbol", value="")
    if st.button("Add to watchlist") and add_symbol.strip():
        new_symbol = add_symbol.strip().upper()
        if new_symbol not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_symbol)
            st.success(f"Added {new_symbol}")

    watchlist_csv = st.text_area(
        "Watchlist (comma separated)",
        value=",".join(st.session_state.watchlist),
        height=100,
    )
    if st.button("Update watchlist"):
        updated = parse_symbols(watchlist_csv)
        if updated:
            st.session_state.watchlist = updated
            st.success("Watchlist updated")
        else:
            st.error("Watchlist cannot be empty")

    st.divider()
    st.subheader("Capital Plan")
    planned_capital = st.number_input(
        "Planned deposit",
        min_value=0.0,
        value=float(START_CAPITAL),
        step=100.0,
    )
    st.caption(f"Planned start capital: {planned_capital:.2f}")

tab_backtest, tab_signals, tab_portfolio, tab_setup = st.tabs(
    ["Backtest", "Signal Monitor", "Portfolio", "Setup"]
)

with tab_backtest:
    st.subheader("Historical trade timing")
    st.caption("Dette viser pa hvilke datoer modellen historisk kjopte og solgte hvert symbol.")

    with st.form("backtest_form"):
        symbols_input = st.text_input(
            "Symbols (comma separated)",
            value=",".join(st.session_state.watchlist),
        )
        start_input = st.date_input("Start date", value=_to_date(BACKTEST_START_DATE))
        end_input = st.date_input("End date", value=_to_date(BACKTEST_END_DATE))
        capital_input = st.number_input(
            "Start capital",
            min_value=100.0,
            value=float(planned_capital),
            step=100.0,
        )
        submitted = st.form_submit_button("Run backtest")

    if submitted:
        symbols = parse_symbols(symbols_input)
        if not symbols:
            st.error("Please provide at least one symbol.")
        elif start_input > end_input:
            st.error("Start date cannot be after end date.")
        elif start_input > date.today():
            st.error("Start date cannot be in the future.")
        else:
            with st.spinner("Running backtests..."):
                try:
                    st.session_state.last_backtest_results = run_backtests(
                        symbols=symbols,
                        start_date=start_input.isoformat(),
                        end_date=end_input.isoformat(),
                        initial_capital=float(capital_input),
                    )
                except ValueError as exc:
                    st.session_state.last_backtest_results = {}
                    st.error(str(exc))

    results = st.session_state.last_backtest_results
    if results:
        summary_rows = []
        for symbol, result in results.items():
            summary_rows.append(
                {
                    "symbol": symbol,
                    "return_pct": result["total_return_pct"],
                    "final_capital": result["final_capital"],
                    "trades": result["total_trades"],
                    "win_rate_pct": result["win_rate_pct"],
                }
            )

        summary_df = pd.DataFrame(summary_rows)
        st.subheader("Summary")
        st.dataframe(summary_df, width="stretch")

        best_row = summary_df.sort_values("return_pct", ascending=False).iloc[0]
        st.caption(
            f"Best return in this run: {best_row['symbol']} ({best_row['return_pct']:.2f}%)."
        )

        st.subheader("Per Symbol Details")
        for symbol, result in results.items():
            st.markdown(f"### {symbol}")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Return %", f"{result['total_return_pct']:.2f}")
            col2.metric("Win rate %", f"{result['win_rate_pct']:.2f}")
            col3.metric("Trades", int(result["total_trades"]))
            col4.metric("Final capital", f"{result['final_capital']:.2f}")

            signal_counts = result.get("signal_counts", {})
            if signal_counts:
                st.caption(f"Signal counts in selected period: {signal_counts}")

            if int(result["total_trades"]) == 0 and signal_counts.get(1, 0) == 0:
                st.info(
                    "No BUY signals in the selected period, so the strategy had no entry opportunities."
                )

            trades = result.get("trades", [])
            if trades:
                trades_df = pd.DataFrame(trades)
                st.markdown("Raw trades")
                st.dataframe(trades_df, width="stretch")

                paired = pair_backtest_trades(trades)
                if paired:
                    paired_df = pd.DataFrame(paired)
                    st.markdown("Buy -> Sell pairs")
                    st.dataframe(paired_df, width="stretch")
            else:
                st.info("No trades for this symbol in selected period.")

with tab_signals:
    st.subheader("What should I buy or sell now?")
    default_start, default_end = get_default_signal_window(180)
    col_a, col_b = st.columns(2)
    signal_start = col_a.date_input("Signal window start", value=_to_date(default_start))
    signal_end = col_b.date_input("Signal window end", value=_to_date(default_end))

    manual_owned_input = st.text_input(
        "Owned symbols override (optional, comma separated)",
        value="",
        help="If empty, app uses symbols from live portfolio when available.",
    )

    if st.button("Analyze watchlist signals"):
        live_positions = st.session_state.live_overview.get("positions", [])
        owned_from_live = [pos.get("symbol", "") for pos in live_positions]
        manual_owned = parse_symbols(manual_owned_input) if manual_owned_input.strip() else []
        effective_owned = manual_owned if manual_owned else owned_from_live

        if signal_start > signal_end:
            st.error("Signal window start date cannot be after end date.")
        elif signal_start > date.today():
            st.error("Signal window start date cannot be in the future.")
        else:
            with st.spinner("Analyzing latest signals..."):
                try:
                    st.session_state.signal_table = get_signal_overview(
                        symbols=st.session_state.watchlist,
                        start_date=signal_start.isoformat(),
                        end_date=signal_end.isoformat(),
                        owned_symbols=effective_owned,
                    )
                except ValueError as exc:
                    st.session_state.signal_table = []
                    st.error(str(exc))

    signal_rows = st.session_state.signal_table
    if signal_rows:
        signal_df = pd.DataFrame(signal_rows)
        st.dataframe(signal_df, width="stretch")

        buy_now = signal_df[signal_df["recommended_action"] == "BUY_NOW"]
        sell_now = signal_df[signal_df["recommended_action"] == "SELL_NOW"]

        st.markdown("Action list")
        if not buy_now.empty:
            st.success(
                "BUY_NOW: "
                + ", ".join(buy_now["symbol"].astype(str).tolist())
            )
        if not sell_now.empty:
            st.warning(
                "SELL_NOW: "
                + ", ".join(sell_now["symbol"].astype(str).tolist())
            )
        if buy_now.empty and sell_now.empty:
            st.info("No immediate BUY_NOW or SELL_NOW recommendations now.")
    else:
        st.info("Run signal analysis to get concrete buy/sell recommendations.")

with tab_portfolio:
    st.subheader("Live Portfolio (IBKR)")
    st.caption("Use this to verify what you already own before acting on BUY/SELL signals.")

    if st.button("Refresh portfolio from IBKR"):
        with st.spinner("Connecting to IBKR..."):
            st.session_state.live_overview = fetch_live_overview()

    overview = st.session_state.live_overview
    if overview.get("connected"):
        st.success("Connected to IBKR")
    else:
        st.warning("Not connected to IBKR. Check TWS/Gateway and env settings.")

    positions = overview.get("positions", [])
    if positions:
        positions_df = pd.DataFrame(positions)
        st.dataframe(positions_df, width="stretch")
    else:
        st.info("No open positions found.")

with tab_setup:
    st.subheader("Readiness checklist")
    st.write("Before funding your account, verify the points below:")

    st.checkbox("I have tested strategy in backtest", value=False, key="setup_backtest")
    st.checkbox("I can refresh and read live IBKR positions", value=False, key="setup_portfolio")
    st.checkbox("I understand BUY_NOW / SELL_NOW logic in Signal Monitor", value=False, key="setup_logic")
    st.checkbox("I will start with paper account before real money", value=True, key="setup_paper")

    st.markdown("Current watchlist")
    st.write(", ".join(st.session_state.watchlist) if st.session_state.watchlist else "Empty")
