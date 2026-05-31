import pandas as pd
from config.config import (
    START_CAPITAL,
    RISK_PER_TRADE,
    MAX_POSITION_SIZE,
    IBKR_COMMISSION_PERCENT,
    IBKR_COMMISSION_MINIMUM,
)
from utils.logger import logger

class PositionSizer:
    """Beregner posisjonstørrelse basert på risikostyring"""
    
    def __init__(self, capital: float = START_CAPITAL):
        self.capital = capital
        self.logger = logger
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """
        Beregner posisjonstørrelse basert på risiko per trade
        
        Args:
            entry_price: Inngang pris
            stop_loss: Stop loss pris
        
        Returns:
            Antall aksjer å kjøpe
        """
        # Risiko i NOK
        risk_amount = self.capital * RISK_PER_TRADE
        
        # Pris-differanse per aksje
        price_diff = abs(entry_price - stop_loss)
        
        if price_diff == 0:
            self.logger.warning("Price difference er 0, kan ikke beregne posisjon")
            return 0
        
        # Antall aksjer
        shares = risk_amount / price_diff
        
        # Maksimum posisjonstørrelse
        max_position_value = self.capital * MAX_POSITION_SIZE
        max_shares = max_position_value / entry_price
        
        # Bruk den minste verdien
        shares = min(shares, max_shares)
        
        # Avrund ned til hele aksjer
        shares = int(shares)
        
        self.logger.info(
            f"Posisjonsstørrelse: {shares} aksjer @ {entry_price} NOK "
            f"(risiko: {risk_amount} NOK, maks: {max_shares} aksjer)"
        )
        
        return shares
    
    def calculate_kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Kelly Criterion - optimal posisjonsstørrelse basert på historisk performance
        
        Formula: f = (bp * p - q) / b
        hvor:
        - p = win_rate
        - q = loss_rate (1 - p)
        - b = ratio av gjennomsnitt gevinst/tap
        """
        if avg_loss == 0:
            return 0
        
        loss_rate = 1 - win_rate
        b = avg_win / avg_loss
        
        kelly_fraction = (b * win_rate - loss_rate) / b
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap på 25%
        
        self.logger.info(f"Kelly Fraction: {kelly_fraction:.2%}")
        
        return kelly_fraction
    
    def estimate_commission(self, order_value: float) -> float:
        """
        Estimerer IBKR kurtasje (prosentbasert, med et gulv på minimumskurtasjen)
        """
        commission = max(
            order_value * IBKR_COMMISSION_PERCENT,
            IBKR_COMMISSION_MINIMUM
        )
        return commission
