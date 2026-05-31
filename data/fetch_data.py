import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from utils.logger import logger

class DataFetcher:
    """Henter historisk prisdata for aksjer og ETF-er"""
    
    def __init__(self):
        self.logger = logger
    
    def _normalize_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Flater ut eventuelle MultiIndex-kolonner fra yfinance."""
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            data = data.loc[:, ~data.columns.duplicated()]
        return data
    
    def fetch_data(self, symbol: str, start_date: str, end_date: str, interval: str = '1d') -> pd.DataFrame:
        """
        Henter prisdata fra Yahoo Finance
        
        Args:
            symbol: Ticker symbol (f.eks. 'AAPL')
            start_date: Start dato (YYYY-MM-DD)
            end_date: Slutt dato (YYYY-MM-DD)
            interval: Tidsinterval ('1d', '1h', '5m', etc)
        
        Returns:
            DataFrame med OHLCV-data
        """
        try:
            self.logger.info(f"Henter data for {symbol} fra {start_date} til {end_date}")
            
            data = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False
            )
            
            if data.empty:
                self.logger.error(f"Ingen data funnet for {symbol}")
                return pd.DataFrame()
            
            data = self._normalize_columns(data)
            self.logger.info(f"Hentet {len(data)} rader for {symbol}")
            return data
            
        except Exception as e:
            self.logger.error(f"Feil ved henting av data for {symbol}: {e}")
            return pd.DataFrame()
    
    def fetch_multiple(self, symbols: list, start_date: str, end_date: str) -> dict:
        """
        Henter data for flere symboler
        
        Args:
            symbols: Liste med ticker symbols
            start_date: Start dato
            end_date: Slutt dato
        
        Returns:
            Dict med symbol som nøkkel og DataFrame som verdi
        """
        data = {}
        for symbol in symbols:
            data[symbol] = self.fetch_data(symbol, start_date, end_date)
        return data
    
    def get_latest_price(self, symbol: str) -> float:
        """
        Henter siste pris for et symbol
        """
        try:
            data = yf.download(symbol, period='1d', progress=False)
            if data.empty:
                self.logger.error(f"Ingen data funnet for {symbol}")
                return None

            data = self._normalize_columns(data)
            latest_price = float(data['Close'].iloc[-1])
            self.logger.info(f"Siste pris for {symbol}: {latest_price}")
            return latest_price
        except Exception as e:
            self.logger.error(f"Feil ved henting av siste pris for {symbol}: {e}")
            return None
