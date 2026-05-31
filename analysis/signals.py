import pandas as pd
from analysis.indicators import TechnicalIndicators
from utils.logger import logger

class SignalGenerator:
    """Genererer kjøps- og salgsignaler basert på teknisk analyse"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.logger = logger
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Genererer signaler basert på enkle regler
        
        Signal: 1 = KJØp, 0 = HOLD, -1 = SELG
        """
        data = data.copy()
        
        # Beregn indikatorer
        data['SMA_20'] = self.indicators.moving_average(data, 20)
        data['SMA_50'] = self.indicators.moving_average(data, 50)
        data['RSI'] = self.indicators.rsi(data, 14)
        
        # Generer signaler
        data['Signal'] = 0
        
        # Kjøpsignal: Pris over SMA20 og SMA20 > SMA50 og RSI < 70
        buy_condition = (
            (data['Close'] > data['SMA_20']) &
            (data['SMA_20'] > data['SMA_50']) &
            (data['RSI'] < 70) &
            (data['RSI'] > 30)
        )
        data.loc[buy_condition, 'Signal'] = 1
        
        # Salgsignal: Pris under SMA20 og SMA20 < SMA50 eller RSI > 70
        sell_condition = (
            (data['Close'] < data['SMA_20']) |
            (data['SMA_20'] < data['SMA_50']) |
            (data['RSI'] > 70)
        )
        data.loc[sell_condition, 'Signal'] = -1
        
        self.logger.info(f"Signaler generert: {data['Signal'].value_counts().to_dict()}")
        
        return data
    
    def get_latest_signal(self, data: pd.DataFrame) -> int:
        """
        Returnerer siste signal
        """
        signals = self.generate_signals(data)
        latest_signal = signals['Signal'].iloc[-1]
        return latest_signal
