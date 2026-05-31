from ib_insync import *
from config.config import IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, IBKR_ACCOUNT_ID
from utils.logger import logger

class IBKRBroker:
    """Integrasjon med Interactive Brokers"""
    
    def __init__(self):
        self.ib = IB()
        self.logger = logger
        self.connected = False
    
    def connect(self) -> bool:
        """
        Koble til IBKR TWS eller Gateway
        
        OBS: TWS/Gateway må kjøre lokalt på port 7497 (live) eller 7496 (paper)
        """
        try:
            self.ib.connect(IBKR_HOST, IBKR_PORT, clientId=IBKR_CLIENT_ID)
            self.connected = True
            self.logger.info(f"Tilkoblet IBKR på {IBKR_HOST}:{IBKR_PORT}")
            return True
        except Exception as e:
            self.logger.error(f"Feil ved tilkobling til IBKR: {e}")
            self.logger.info("Sjekk at TWS eller Gateway kjører og at port er riktig")
            return False
    
    def disconnect(self):
        """Koble fra IBKR"""
        try:
            self.ib.disconnect()
            self.connected = False
            self.logger.info("Frakoblet IBKR")
        except Exception as e:
            self.logger.error(f"Feil ved frakobling: {e}")
    
    def get_account_summary(self):
        """Henter kontooversikt"""
        if not self.connected:
            self.logger.error("Ikke tilkoblet IBKR")
            return None
        
        try:
            account = self.ib.accountSummary(IBKR_ACCOUNT_ID)
            self.logger.info(f"Konto: {IBKR_ACCOUNT_ID}")
            return account
        except Exception as e:
            self.logger.error(f"Feil ved henting av kontooversikt: {e}")
            return None
    
    def place_order(self, symbol: str, quantity: int, order_type: str = 'BUY') -> bool:
        """
        Plasserer ordre
        
        Args:
            symbol: Ticker symbol
            quantity: Antall aksjer
            order_type: 'BUY' eller 'SELL'
        """
        if not self.connected:
            self.logger.error("Ikke tilkoblet IBKR")
            return False
        
        try:
            # Opprett kontrakt
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Opprett ordre
            action = order_type.upper()
            order = MarketOrder(action, quantity)
            
            # Send ordre
            trade = self.ib.placeOrder(contract, order)
            
            self.logger.info(f"Ordre plassert: {action} {quantity} {symbol}")
            self.logger.info(f"Trade ID: {trade.order.orderId}")
            
            # Vent på order å bli fylt
            while not trade.isDone():
                self.ib.sleep(0.1)
            
            self.logger.info(f"Ordre fyllt: {trade.orderStatus.status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Feil ved plassering av ordre: {e}")
            return False
    
    def get_positions(self):
        """Henter aktuelle posisjoner"""
        if not self.connected:
            self.logger.error("Ikke tilkoblet IBKR")
            return []
        
        try:
            positions = self.ib.positions()
            self.logger.info(f"Posisjoner: {len(positions)}")
            for pos in positions:
                self.logger.info(f"{pos.contract.symbol}: {pos.position} @ {pos.avgCost}")
            return positions
        except Exception as e:
            self.logger.error(f"Feil ved henting av posisjoner: {e}")
            return []
