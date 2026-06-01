import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Interactive Brokers
IBKR_ACCOUNT_ID = os.getenv('IBKR_ACCOUNT_ID', '')
IBKR_HOST = os.getenv('IBKR_HOST', '127.0.0.1')
IBKR_PORT = int(os.getenv('IBKR_PORT', 7497))
IBKR_CLIENT_ID = int(os.getenv('IBKR_CLIENT_ID', 1))

# Trading Parameters
START_CAPITAL = float(os.getenv('START_CAPITAL', 5000))
MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', 0.1))  # 10%
RISK_PER_TRADE = float(os.getenv('RISK_PER_TRADE', 0.02))  # 2%

# Strategy
STOCK_SYMBOLS = [
	symbol.strip()
	for symbol in os.getenv('STOCK_SYMBOLS', 'AAPL,MSFT').split(',')
	if symbol.strip()
]
BACKTEST_START_DATE = os.getenv('BACKTEST_START_DATE', '2023-01-01')
BACKTEST_END_DATE = os.getenv('BACKTEST_END_DATE', '2024-01-01')
STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PCT', 0.05))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/trading_bot.log')

# Kurtasje (IBKR typisk ~0.4% eller $1 minimum)
IBKR_COMMISSION_PERCENT = float(os.getenv('IBKR_COMMISSION_PERCENT', 0.004))
IBKR_COMMISSION_MINIMUM = float(os.getenv('IBKR_COMMISSION_MINIMUM', 1.0))  # USD

# Daily signal bot
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')
DAILY_SIGNAL_LOOKBACK_DAYS = int(os.getenv('DAILY_SIGNAL_LOOKBACK_DAYS', 180))
MONTHLY_REBALANCE_DAY = int(os.getenv('MONTHLY_REBALANCE_DAY', 1))
DAILY_BOT_STATE_FILE = os.getenv('DAILY_BOT_STATE_FILE', '.state/daily_signal_bot_state.json')
