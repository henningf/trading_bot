#!/usr/bin/env python3
"""
Trading Bot - Main Orchestrator

Denne filen orkestrerer hele systemet:
1. Henter data
2. Genererer signaler
3. Backtest (hvis aktivert)
4. Utfører handler (hvis aktivert)
"""

import sys
from utils.logger import logger
from config.config import STOCK_SYMBOLS, BACKTEST_START_DATE, BACKTEST_END_DATE
from data.fetch_data import DataFetcher
from analysis.signals import SignalGenerator
from backtest.backtest import Backtest
from execution.broker import IBKRBroker

def run_backtest():
    """
    Kjører backtest på alle symboler
    """
    logger.info("Starter backtesting...")
    
    for symbol in STOCK_SYMBOLS:
        logger.info(f"\nBacktesting {symbol}...")
        backtest = Backtest()
        results = backtest.run(symbol, BACKTEST_START_DATE, BACKTEST_END_DATE)
        
        if results:
            logger.info(f"\nResultater for {symbol}:")
            logger.info(f"Avkastning: {results['total_return_pct']:.2f}%")
            logger.info(f"Win rate: {results['win_rate_pct']:.2f}%")

def run_live_trading():
    """
    Kjører live trading (krever IBKR tilkobling)
    """
    logger.info("Starter live trading...")
    
    broker = IBKRBroker()
    
    # Koble til IBKR
    if not broker.connect():
        logger.error("Kunne ikke koble til IBKR. Avslutter.")
        return
    
    try:
        # Hent kontooversikt
        broker.get_account_summary()
        
        # Hent aktuelle posisjoner
        positions = broker.get_positions()
        
        logger.info(f"Aktive posisjoner: {len(positions)}")
        
        # Her kan du legge til trading logikk
        # for symbol in STOCK_SYMBOLS:
        #     broker.place_order(symbol, 10, 'BUY')
        
    finally:
        broker.disconnect()

def main():
    """
    Hovedfunksjon
    """
    logger.info("="*50)
    logger.info("Trading Bot - Startet")
    logger.info("="*50)
    
    # Valg mellom backtest og live trading
    print("\n1. Backtest")
    print("2. Live Trading (krever IBKR)")
    print("3. Lukk")
    
    choice = input("\nVelg: ")
    
    if choice == '1':
        run_backtest()
    elif choice == '2':
        run_live_trading()
    elif choice == '3':
        logger.info("Avslutter")
        sys.exit(0)
    else:
        logger.error("Ugyldig valg")
        sys.exit(1)
    
    logger.info("\nTrading Bot - Avsluttet")

if __name__ == '__main__':
    main()
