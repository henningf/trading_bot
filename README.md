# Trading Bot

Python-basert decision-dashboard for aksjer via Yahoo Finance (analyse/backtest) og Interactive Brokers (live portefoljeoversikt).

Prosjektet er laget for trygg overgang fra backtest til reell handel, med fokus pa signaler, risikostyring og tydelig visning av hva modellen faktisk foreslar.

## Hva du far i dag

- Backtest per symbol og periode
- Signal Monitor med anbefalt handling per symbol:
  - BUY_NOW
  - SELL_NOW
  - HOLD_POSITION
  - WAIT
- Portfolio-fane som henter apne posisjoner fra IBKR
- Setup-fane med enkel readiness-sjekk
- Watchlist som kan oppdateres direkte i GUI
- Tydelig forklaring nar en periode gir 0 handler (for eksempel ingen BUY-signaler)

## Markedsstotte (forelopig)

Forelopig er dette bevisst begrenset til:

- Amerikanske tickere uten suffix (for eksempel AAPL, MSFT)
- Norske tickere pa Yahoo-format med .OL (for eksempel NONG.OL)

Praktisk i appen:

- Hvis du skriver NONG, prover systemet automatisk NONG og deretter NONG.OL
- Andre markedssuffix (som .ST, .CO) avvises forelopig

## Struktur

```text
trading_bot/
├── analysis/               # Indikatorer og signalregler
├── backtest/               # Backtestmotor
├── config/                 # Miljo-/app-konfigurasjon
├── data/                   # Datainnhenting (Yahoo Finance)
├── execution/              # IBKR-klient
├── gui/                    # Streamlit-app
├── risk/                   # Posisjonsstorrelse og kurtasje
├── services/               # Tjenestelag brukt av CLI + GUI
├── tests/                  # Pytest tester
├── utils/                  # Logger osv
├── main.py                 # Enkel CLI-entry
├── requirements.txt
└── .env.example
```

## Kom i gang

1. Klon repoet

```bash
git clone https://github.com/henningf/trading_bot.git
cd trading_bot
```

2. Opprett virtuelt miljo

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Installer avhengigheter

```bash
pip install -r requirements.txt
```

4. Opprett lokal konfig

```bash
cp .env.example .env
```

5. Rediger .env ved behov (IBKR-innstillinger, symboler, kapital osv)

## Kjoring

### GUI (anbefalt)

Fra prosjektrot:

```bash
streamlit run gui/app.py
```

Eller fra gui-mappe:

```bash
streamlit run app.py
```

### CLI

```bash
python main.py
```

### Daglig signal-bot (ingen auto-handler)

Kjor en gang per dag (daily candles) og fa varsler om hva som bor vurderes:

```bash
python daily_signal_bot.py
```

Boten:

- Henter signaler for watchlist (`STOCK_SYMBOLS`)
- Tar hensyn til hva du faktisk eier (fra IBKR hvis tilgjengelig)
- Sender forslag som BUY_NOW / SELL_NOW / HOLD_POSITION
- Sender manedlig rebalanserings-paminnelse
- Plasserer ingen ordre automatisk

## GUI-arbeidsflyt

1. Setup watchlist i sidebar
2. Kjor Backtest for valgt periode
3. Se Buy -> Sell pairs i resultatet for historisk timing
4. Oppdater Portfolio-fane mot IBKR for hva du faktisk eier
5. Kjor Signal Monitor for konkrete BUY_NOW/SELL_NOW-forslag

## Signalregler (na)

Signalgeneratoren bruker en enkel regelkombinasjon:

- BUY nar pris > SMA20, SMA20 > SMA50, og RSI er mellom 30 og 70
- SELL nar pris < SMA20, eller SMA20 < SMA50, eller RSI > 70

Merk: Dette er en enkel baseline-strategi og ikke investeringsradgivning.

## Dato-validering

Appen validerer perioder tydelig:

- Startdato kan ikke vaere etter sluttdato
- Startdato kan ikke vaere i fremtiden

Ved ugyldig periode faar du tydelig feilmelding i GUI i stedet for uklar runtime-feil.

## Discord-varsler

Legg webhook i `.env`:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Relevante bot-variabler i `.env`:

```env
DAILY_SIGNAL_LOOKBACK_DAYS=180
MONTHLY_REBALANCE_DAY=1
DAILY_BOT_STATE_FILE=.state/daily_signal_bot_state.json
```

Hvis `DISCORD_WEBHOOK_URL` er tom, skriver boten bare rapporten lokalt.

## Schedulering (1 kjoring per dag)

Eksempel med cron (Mac/Linux):

```bash
crontab -e
```

Legg til for kjoring hver dag kl 18:00:

```cron
0 18 * * * cd /path/to/trading_bot && /path/to/trading_bot/.venv/bin/python daily_signal_bot.py >> logs/daily_signal_bot.log 2>&1
```

Dette gir deg daglig rapport/varsel uten auto-trading.

## Testing

Kjor alle tester:

```bash
python -m pytest -q
```

Prosjektet har regresjonstester for backtest, signaler, datahenting, risikomodul og indikatorer.

## Viktig risiko

- Kun for laering og eksperimentering
- Trading innebaerer risiko for tap
- Bruk paper-konto forst
- Start med sma belop

## Ressurser

- Interactive Brokers Python API
  - https://ibkr-api.ibkr.info/
- ib_insync
  - https://ib-insync.readthedocs.io/

## Lisens

MIT License
