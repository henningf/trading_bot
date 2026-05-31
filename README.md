# Trading Bot

En Python-basert trading bot for aksjer og ETF-er via Interactive Brokers.

## 📋 Beskrivelse

Denne boten automatiserer trading av aksjer og ETF-er med følgende features:
- Datainnhenting fra markedet
- Teknisk analyse og signalgenerering
- Backtesting av strategier
- Automatisk handel via IBKR API
- Risikostyring og posisjonsstørrelse

## 🎯 Mål
- Småskalert trading (5000 NOK startkapital)
- 1-10 trades per måned (fokus på kvalitet)
- Minimale kurtasjer

## 🏗️ Struktur

```
trading_bot/
├── config/                 # Konfigurasjoner
│   ├── config.py          # Innstillinger
│   └── secrets.py         # API-nøkler (ALDRI commit!)
│
├── data/
│   └── fetch_data.py      # Henter prisdata (Yahoo Finance, etc)
│
├── analysis/
│   ├── indicators.py      # Tekniske indikatorer
│   └── signals.py         # Kjøps-/salgslogikk
│
├── backtest/
│   └── backtest.py        # Backtesting med historisk data
│
├── execution/
│   └── broker.py          # IBKR API-integrasjon
│
├── risk/
│   └── position_sizing.py # Posisjonstørrelse & risikostyring
│
├── utils/
│   └── logger.py          # Logging
│
├── main.py                # Orkestrering av hele systemet
├── requirements.txt       # Dependencies
├── .env.example           # Template for miljøvariabler
└── .gitignore             # Ekskluder sensitive filer
```

## 🚀 Kom i gang

### Installasjon

1. Klon repositoriet:
   ```bash
   git clone https://github.com/henningf/trading_bot.git
   cd trading_bot
   ```

2. Opprett virtuelt miljø:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   venv\Scripts\activate     # Windows
   ```

3. Installer dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Konfigurer IBKR-credentials:
   ```bash
   cp .env.example .env
   # Rediger .env med dine IBKR-detaljer
   ```

### Kjør boten

```bash
python main.py
```

## ⚠️ VIKTIG - Risikodisklaimer

- **Denne koden er for læringsformål**
- Trading innebærer risiko - du kan tape penger
- Test ALLTID på papirportefølje først
- Start med små beløp
- Vær oppmerksom på kurtasjer og skatter

## 📚 Ressurser

- [Interactive Brokers Python API](https://ibkr-api.ibkr.info/)
- [ib_insync dokumentasjon](https://ib-insync.readthedocs.io/)
- [Backtrader dokumentasjon](https://www.backtrader.com/)

## 📝 Lisens

MIT License
