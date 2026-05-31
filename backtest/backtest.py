import pandas as pd
import numpy as np
from datetime import timedelta
from data.fetch_data import DataFetcher
from analysis.signals import SignalGenerator
from risk.position_sizing import PositionSizer
from config.config import START_CAPITAL, STOP_LOSS_PCT
from utils.logger import logger

class Backtest:
    """Backtester trading strategier på historisk data"""
    
    def __init__(self, initial_capital: float = START_CAPITAL):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.data_fetcher = DataFetcher()
        self.signal_generator = SignalGenerator()
        self.position_sizer = PositionSizer(initial_capital)
        self.logger = logger
        self.trades = []
        self.portfolio_values = []
        self.period_signal_counts = {}
    
    def run(self, symbol: str, start_date: str, end_date: str) -> dict:
        """
        Kjører backtest på historisk data
        
        Args:
            symbol: Ticker symbol
            start_date: Start dato (YYYY-MM-DD)
            end_date: Slutt dato (YYYY-MM-DD)
        
        Returns:
            Dict med resultater
        """
        self.logger.info(f"Starter backtest for {symbol} fra {start_date} til {end_date}")
        self.period_signal_counts = {}
        
        # Hent ekstra historikk for indikator-warmup (SMA50/RSI etc.)
        start_dt = pd.to_datetime(start_date)
        warmup_start_date = (start_dt - timedelta(days=120)).date().isoformat()

        data = self.data_fetcher.fetch_data(symbol, warmup_start_date, end_date)
        if data.empty:
            return {}
        
        # Generer signaler
        data = self.signal_generator.generate_signals(data)

        # Simuler handler kun i etterspurt periode, men med indikatorer basert på warmup-data
        data = data[data.index >= start_dt]
        if data.empty:
            self.logger.warning(f"Ingen data i valgt periode for {symbol}")
            return {}

        self.period_signal_counts = data['Signal'].value_counts().to_dict()
        
        # Simuler trades
        position = 0
        entry_price = 0
        
        for idx, row in data.iterrows():
            signal = row['Signal']
            price = row['Close']
            
            # KJØP
            if signal == 1 and position == 0:
                position, entry_price = self._handle_buy(signal_date=idx, symbol=symbol, price=price)
            
            # SELG
            elif signal == -1 and position > 0:
                self._handle_sell(signal_date=idx, symbol=symbol, position=position, entry_price=entry_price, price=price)
                position = 0
            
            # Tracker portfolio verdi
            portfolio_value = self.capital + (position * price)
            self.portfolio_values.append({
                'date': idx,
                'value': portfolio_value
            })
        
        # Lukk eventuell åpen posisjon
        if position > 0:
            self._handle_sell(
                signal_date=data.index[-1],
                symbol=symbol,
                position=position,
                entry_price=entry_price,
                price=data['Close'].iloc[-1],
            )
            position = 0
        
        return self._calculate_metrics()

    def _handle_buy(self, signal_date, symbol: str, price: float) -> tuple[int, float]:
        """Utfører kjøpslogikk og returnerer ny posisjon + entry price."""
        shares = self.position_sizer.calculate_position_size(price, price * (1 - STOP_LOSS_PCT))

        # Reduser antall aksjer til vi faktisk har råd (inkl. kurtasje)
        while shares > 0 and shares * price + self.position_sizer.estimate_commission(shares * price) > self.capital:
            shares -= 1

        if shares <= 0:
            return 0, 0

        commission = self.position_sizer.estimate_commission(shares * price)
        self.capital -= (shares * price + commission)

        self.trades.append({
            'date': signal_date,
            'type': 'BUY',
            'symbol': symbol,
            'price': price,
            'shares': shares,
            'commission': commission
        })
        self.logger.info(f"BUY: {shares} @ {price}")
        return shares, price

    def _handle_sell(self, signal_date, symbol: str, position: int, entry_price: float, price: float) -> None:
        """Utfører salgslogikk for en åpen posisjon."""
        revenue = position * price
        commission = self.position_sizer.estimate_commission(revenue)
        self.capital += (revenue - commission)

        profit = revenue - (position * entry_price)
        profit_pct = (profit / (position * entry_price)) * 100

        self.trades.append({
            'date': signal_date,
            'type': 'SELL',
            'symbol': symbol,
            'price': price,
            'shares': position,
            'commission': commission,
            'profit': profit,
            'profit_pct': profit_pct
        })

        self.logger.info(f"SELL: {position} @ {price} (Profit: {profit_pct:.2f}%)")
    
    def _calculate_metrics(self) -> dict:
        """
        Beregner ytelsesmålinger
        """
        trades_df = pd.DataFrame(self.trades)

        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        # Ingen trades: returner nullstilte metrics uten å indeksere manglende kolonner
        if trades_df.empty:
            metrics = {
                'initial_capital': self.initial_capital,
                'final_capital': self.capital,
                'total_return_pct': total_return,
                'total_return_nok': self.capital - self.initial_capital,
                'signal_counts': self.period_signal_counts,
                'total_trades': 0,
                'profitable_trades': 0,
                'losing_trades': 0,
                'win_rate_pct': 0,
                'trades': []
            }
            self.logger.info("Ingen trades utført i backtesten")
            return metrics

        total_trades = len(trades_df[trades_df['type'] == 'BUY'])

        # Lønnsomme vs ulønnsom trades
        profitable_trades = trades_df[trades_df['profit'] > 0].shape[0] if 'profit' in trades_df.columns else 0
        losing_trades = trades_df[trades_df['profit'] < 0].shape[0] if 'profit' in trades_df.columns else 0
        
        win_rate = (profitable_trades / (profitable_trades + losing_trades) * 100) if (profitable_trades + losing_trades) > 0 else 0
        
        metrics = {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return_pct': total_return,
            'total_return_nok': self.capital - self.initial_capital,
            'signal_counts': self.period_signal_counts,
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'losing_trades': losing_trades,
            'win_rate_pct': win_rate,
            'trades': trades_df.to_dict('records')
        }
        
        self.logger.info("="*50)
        self.logger.info("Backtest Resultater:")
        self.logger.info(f"Initial kapital: {self.initial_capital} NOK")
        self.logger.info(f"Final kapital: {self.capital:.2f} NOK")
        self.logger.info(f"Total avkastning: {total_return:.2f}%")
        self.logger.info(f"Total trades: {total_trades}")
        self.logger.info(f"Win rate: {win_rate:.2f}%")
        self.logger.info("="*50)
        
        return metrics
