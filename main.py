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
from services.trading_service import fetch_live_overview, run_backtests

def run_backtest():
    """
    Kjører backtest på alle symboler
    """
    run_backtests()

def run_live_trading():
    """
    Kjører live trading (krever IBKR tilkobling)
    """
    logger.info("Starter live trading...")

    overview = fetch_live_overview()
    if not overview["connected"]:
        logger.error("Kunne ikke koble til IBKR. Avslutter.")
        return

    positions = overview["positions"]
    logger.info(f"Aktive posisjoner: {len(positions)}")

    # Her kan du legge til trading logikk
    # for symbol in STOCK_SYMBOLS:
    #     broker.place_order(symbol, 10, 'BUY')

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
