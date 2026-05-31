import yfinance as yf
import pandas as pd
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

    def _symbol_candidates(self, symbol: str) -> list[str]:
        """Bygger kandidatliste for tickers (inkl. Oslo Bors fallback)."""
        normalized = symbol.strip().upper()
        if not normalized:
            return []

        if not self._is_supported_symbol(normalized):
            self.logger.error(
                f"Unsupported ticker market for {normalized}. Supported now: US tickers (AAPL) and Norwegian tickers (.OL)."
            )
            return []

        candidates = [normalized]

        # Yahoo Finance bruker ofte .OL for Oslo Bors (f.eks. NONG.OL).
        if "." not in normalized:
            candidates.append(f"{normalized}.OL")

        return candidates

    def _is_supported_symbol(self, symbol: str) -> bool:
        """Stotter forelopig kun US tickere (uten suffix) og norske (.OL)."""
        if "." not in symbol:
            return True
        return symbol.endswith(".OL")

    def _download_first_available(self, candidates: list[str], **download_kwargs) -> tuple[pd.DataFrame, str | None]:
        """Returnerer første ikke-tomme datasett blant ticker-kandidater."""
        for candidate in candidates:
            data = yf.download(candidate, progress=False, **download_kwargs)
            if not data.empty:
                return data, candidate
        return pd.DataFrame(), None
    
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

            candidates = self._symbol_candidates(symbol)
            if not candidates:
                return pd.DataFrame()

            data, resolved_symbol = self._download_first_available(
                candidates,
                start=start_date,
                end=end_date,
                interval=interval,
            )

            if data.empty:
                self.logger.error(f"Ingen data funnet for {symbol}. Prøvde: {candidates}")
                return pd.DataFrame()

            data = self._normalize_columns(data)
            if resolved_symbol and resolved_symbol != symbol.upper():
                self.logger.info(f"Bruker ticker {resolved_symbol} for forespurt symbol {symbol}")

            self.logger.info(f"Hentet {len(data)} rader for {resolved_symbol or symbol}")
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
    
    def get_latest_price(self, symbol: str) -> float | None:
        """
        Henter siste pris for et symbol
        """
        try:
            candidates = self._symbol_candidates(symbol)
            if not candidates:
                return None

            data, resolved_symbol = self._download_first_available(candidates, period='1d')
            if data.empty:
                self.logger.error(f"Ingen data funnet for {symbol}. Prøvde: {candidates}")
                return None

            data = self._normalize_columns(data)
            latest_price = float(data['Close'].iloc[-1])
            self.logger.info(f"Siste pris for {resolved_symbol or symbol}: {latest_price}")
            return latest_price
        except Exception as e:
            self.logger.error(f"Feil ved henting av siste pris for {symbol}: {e}")
            return None
