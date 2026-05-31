import pandas as pd
import numpy as np
from utils.logger import logger

class TechnicalIndicators:
    """Beregner tekniske indikatorer"""
    
    @staticmethod
    def moving_average(data: pd.DataFrame, window: int, column: str = 'Close') -> pd.Series:
        """
        Enkel glidende gjennomsnitt (SMA)
        """
        return data[column].rolling(window=window).mean()
    
    @staticmethod
    def exponential_moving_average(data: pd.DataFrame, window: int, column: str = 'Close') -> pd.Series:
        """
        Eksponentielt glidende gjennomsnitt (EMA)
        """
        return data[column].ewm(span=window, adjust=False).mean()
    
    @staticmethod
    def rsi(data: pd.DataFrame, window: int = 14, column: str = 'Close') -> pd.Series:
        """
        Relative Strength Index (RSI)
        RSI over 70 = overkjøpt (sell signal)
        RSI under 30 = oversolgt (buy signal)
        """
        delta = data[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

        # Når loss == 0 (kun oppgang) er RSI per definisjon 100.
        # Unngå divisjon på null ved å fylle inn direkte i stedet for å regne med inf.
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.where(loss != 0, 100.0)
        return rsi
    
    @staticmethod
    def macd(data: pd.DataFrame, column: str = 'Close', fast: int = 12, slow: int = 26, signal: int = 9):
        """
        MACD (Moving Average Convergence Divergence)
        Returns: (MACD line, Signal line, Histogram)
        """
        ema_fast = data[column].ewm(span=fast, adjust=False).mean()
        ema_slow = data[column].ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(data: pd.DataFrame, window: int = 20, num_std: float = 2.0, column: str = 'Close'):
        """
        Bollinger Bands
        Returns: (Upper band, Middle band, Lower band)
        """
        middle = data[column].rolling(window=window).mean()
        std = data[column].rolling(window=window).std()
        
        upper = middle + (std * num_std)
        lower = middle - (std * num_std)
        
        return upper, middle, lower
