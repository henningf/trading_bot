#!/usr/bin/env python3
"""Daglig signal-bot: ingen auto-handler, kun varsler."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from config.config import (
    DAILY_BOT_STATE_FILE,
    DAILY_SIGNAL_LOOKBACK_DAYS,
    DISCORD_WEBHOOK_URL,
    MONTHLY_REBALANCE_DAY,
    STOCK_SYMBOLS,
)
from services.trading_service import fetch_live_overview, get_signal_overview
from utils.discord_notifier import send_discord_message
from utils.logger import logger


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")


def _month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def _is_monthly_rebalance_due(today: date, state: dict) -> bool:
    if today.day < MONTHLY_REBALANCE_DAY:
        return False

    return state.get("last_rebalance_alert_month") != _month_key(today)


def _build_message(today: date, signal_rows: list[dict], rebalance_due: bool) -> str:
    buy_now = [row["symbol"] for row in signal_rows if row.get("recommended_action") == "BUY_NOW"]
    sell_now = [row["symbol"] for row in signal_rows if row.get("recommended_action") == "SELL_NOW"]
    hold_pos = [row["symbol"] for row in signal_rows if row.get("recommended_action") == "HOLD_POSITION"]

    lines = [
        f"Daily Signal Report - {today.isoformat()}",
        "",
        "No automatic orders are sent. This is advisory only.",
        "",
        f"BUY_NOW: {', '.join(buy_now) if buy_now else 'None'}",
        f"SELL_NOW: {', '.join(sell_now) if sell_now else 'None'}",
        f"HOLD_POSITION: {', '.join(hold_pos) if hold_pos else 'None'}",
        "",
        "Per-symbol summary:",
    ]

    for row in signal_rows:
        lines.append(
            "- "
            + f"{row.get('symbol')}: action={row.get('recommended_action')}, "
            + f"signal={row.get('latest_signal')}, in_position={row.get('in_position')}"
        )

    if rebalance_due:
        lines.extend(
            [
                "",
                "Monthly rebalance reminder:",
                "- Review current positions vs watchlist and risk budget.",
                "- Consider trimming overweight names and adding new BUY_NOW candidates.",
            ]
        )

    return "\n".join(lines)


def run_daily_signal_bot() -> int:
    today = date.today()
    start = today - timedelta(days=DAILY_SIGNAL_LOOKBACK_DAYS)

    state_path = Path(DAILY_BOT_STATE_FILE)
    state = _load_state(state_path)

    overview = fetch_live_overview()
    owned_symbols = [p.get("symbol", "").upper() for p in overview.get("positions", [])]

    signal_rows = get_signal_overview(
        symbols=STOCK_SYMBOLS,
        start_date=start.isoformat(),
        end_date=today.isoformat(),
        owned_symbols=owned_symbols,
    )

    rebalance_due = _is_monthly_rebalance_due(today, state)
    message = _build_message(today, signal_rows, rebalance_due)

    logger.info("Daily signal report generated")
    print("\n" + message + "\n")

    if DISCORD_WEBHOOK_URL:
        sent_ok = send_discord_message(DISCORD_WEBHOOK_URL, message)
        if sent_ok:
            logger.info("Discord alert sent")
        else:
            logger.error("Failed to send Discord alert")
    else:
        logger.warning("DISCORD_WEBHOOK_URL is empty; report printed locally only")

    if rebalance_due:
        state["last_rebalance_alert_month"] = _month_key(today)
        _save_state(state_path, state)

    return 0


if __name__ == "__main__":
    raise SystemExit(run_daily_signal_bot())
