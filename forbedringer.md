# Forbedringer — Trading Bot

Dette dokumentet er en arbeidsliste for forbedring av trading-boten. Gjennomgang gjort 2026-05-31.
Strukturen (modulær oppdeling i `data/`, `analysis/`, `backtest/`, `execution/`, `risk/`) er god.
Hovedmanglene er: noen reelle bugs, blanding av valuta, manglende tester, og ingen GUI.

Status-koder: 🔴 kritisk (feil/risiko) · 🟡 bør fikses · 🟢 nice-to-have · ✅ ferdig

## Fremdrift
- ✅ **2026-05-31:** Alle bugs i seksjon 1 (1.1–1.8) fikset og verifisert i venv.
- ✅ **2026-05-31:** Testpakke opprettet (`tests/`, `pytest.ini`) — 35 tester, alle grønne, ingen nettverk. Hver bugfiks har en regresjonstest.
- ✅ **2026-05-31:** Punkt 2.8 del 1 ferdig: gjenbrukbart tjenestelag lagt til i `services/trading_service.py`, og `main.py` bruker nå tjenestelaget.
- ✅ **2026-05-31:** GUI MVP v1 ferdig: `gui/app.py` med Streamlit-backtestside (inputs + summary + trades).
- ⬜ Neste: konfigurerbare strategiparametre (2.4) + GUI-fane for live-status (read-only) + risiko-metrics (2.3).

---

## 1. Bugs (fiks først) — ✅ ALLE FIKSET 2026-05-31

### ✅ 1.1 `estimate_commission` bruker feil minimum
[risk/position_sizing.py:80-83](risk/position_sizing.py#L80-L83)
```python
commission = max(
    order_value * IBKR_COMMISSION_PERCENT,
    IBKR_COMMISSION_PERCENT,        # <-- feil: dette er 0.004, ikke minimumskurtasjen
)
```
Skal være `IBKR_COMMISSION_MINIMUM` (1.0 USD). Slik det står nå er gulvet 0.004, så minimumskurtasjen blir aldri brukt.

### ✅ 1.2 Backtest ignorerer minimumskurtasje
[backtest/backtest.py:58](backtest/backtest.py#L58), [backtest/backtest.py:74](backtest/backtest.py#L74)
Backtesten regner kun `shares * price * IBKR_COMMISSION_PERCENT` og ser bort fra `IBKR_COMMISSION_MINIMUM`.
For en bot med 5000 NOK og 1–10 trades/mnd er minimumskurtasjen ($1) ofte den dominerende kostnaden — å ignorere den gir for optimistiske resultater. Bruk `PositionSizer.estimate_commission()` ett sted i stedet for å duplisere formelen.

### ✅ 1.3 Backtest kan gå i negativ kapital
[backtest/backtest.py:53-59](backtest/backtest.py#L53-L59)
Det sjekkes aldri at `self.capital >= shares * price + commission` før kjøp. `calculate_position_size` begrenser til `MAX_POSITION_SIZE` av *initial* kapital, men etter et tap kan kjøpet likevel overstige tilgjengelig kapital. Legg til en sjekk.

### ✅ 1.4 `_calculate_metrics` krasjer uten trades
[backtest/backtest.py:113-120](backtest/backtest.py#L113-L120)
Hvis ingen trades ble gjort er `trades_df` tom og har ingen `'type'`/`'profit'`-kolonner → `trades_df[trades_df['type'] == 'BUY']` kaster `KeyError`. Håndter tom-tilfellet eksplisitt (returner nullstilte metrics).

### ✅ 1.5 Sluttposisjon lukkes uten kurtasje
[backtest/backtest.py:101-105](backtest/backtest.py#L101-L105)
Når en åpen posisjon tvangslukkes på siste bar legges hele `revenue` til uten å trekke kurtasje. Inkonsistent med resten av simuleringen.

### ✅ 1.6 Feil/byttet portforklaring for IBKR
[execution/broker.py:21](execution/broker.py#L21)
Kommentaren sier "7497 (live) eller 7496 (paper)". Standard er motsatt: **TWS live = 7496, TWS paper = 7497** (Gateway: live 4001, paper 4002). `.env.example` defaulter til 7497, som er paper — det er trygt og riktig, men kommentaren bør rettes så ingen kobler til live ved et uhell.

### ✅ 1.7 `get_latest_price` normaliserer ikke kolonner
[data/fetch_data.py:72-83](data/fetch_data.py#L72-L83)
Nyere `yfinance` returnerer MultiIndex-kolonner. `fetch_data` håndterer dette via `_normalize_columns`, men `get_latest_price` gjør det ikke → `data['Close']` kan gi en DataFrame i stedet for Series, og `.iloc[-1]` returnerer en rad. Kjør samme normalisering, eller bruk `auto_adjust`-eksplisitt og `.item()`.

### ✅ 1.8 RSI deler på null
[analysis/indicators.py:33](analysis/indicators.py#L33)
`rs = gain / loss` gir `inf`/`NaN` når `loss == 0` (kun oppgang i vinduet). Resultatet (RSI=100) er riktig, men pandas logger advarsler. Bruk en liten epsilon eller `.replace`.

---

## 2. Designsvakheter

### 🔴 2.1 Blandet valuta (USD vs NOK)
Prisene fra yfinance for `AAPL/MSFT/TSLA` er i **USD**, men `START_CAPITAL`, kurtasje og all logging er merket **NOK**. Det er ingen valutakonvertering. For en norsk konto via IBKR er dette en reell feilkilde.
- Bestem deg: handle USD-instrumenter med USD-konto, eller konverter eksplisitt.
- Gjør valuta til en eksplisitt parameter (`Stock(symbol, 'SMART', currency)` brukes allerede med 'USD' i [broker.py:73](execution/broker.py#L73)).

### 🟡 2.2 Backtest handler på samme bar som signalet
[backtest/backtest.py:48-53](backtest/backtest.py#L48-L53)
Kjøp/salg skjer på `Close` på samme bar som signalet beregnes fra. Det er en mild form for lookahead — i praksis kan du ikke handle på dagens close basert på dagens close. Vanlig konvensjon: generer signal på bar *t*, utfør på `Open` (eller `Close`) på bar *t+1*. Shift signalet med `.shift(1)`.

### 🟡 2.3 Manglende risiko-metrics i backtest
`_calculate_metrics` mangler det viktigste for å vurdere en strategi:
- **Max drawdown** (du har allerede `portfolio_values`)
- **Sharpe / Sortino ratio**
- **Profit factor** og gjennomsnittlig gevinst/tap
- **Buy & hold-benchmark** (slo strategien bare det å eie aksjen?)
- Antall bars i marked / eksponering

### 🟡 2.4 Hardkodet strategi
[analysis/signals.py:21-43](analysis/signals.py#L21-L43)
SMA-vinduer (20/50), RSI-grenser (30/70) og 5% stop-loss ([backtest.py:54](backtest/backtest.py#L54)) er hardkodet. Flytt til config/parametre så de kan optimaliseres og styres fra GUI-et. Vurder en `Strategy`-baseklasse så flere strategier kan plugges inn.

### 🟡 2.5 `place_order` kan henge for alltid
[execution/broker.py:86-87](execution/broker.py#L86-L87)
`while not trade.isDone(): self.ib.sleep(0.1)` har ingen timeout. En ufylt limit/market-ordre låser tråden. Legg til en maks-ventetid og bruk gjerne kun marketorder for fyllgaranti, eller logg og returner ved timeout.

### 🟡 2.6 Ingen kobling fra signal → ordre i live trading
[main.py:58-60](main.py#L58-L60)
`run_live_trading` henter konto og posisjoner, men selve trading-logikken er bare utkommentert. Det finnes heller ingen kobling mellom `SignalGenerator`, `PositionSizer` og `place_order`. Dette er kjernen som mangler for at boten faktisk skal handle.

### 🟡 2.7 Event loop opprettes i konstruktøren
[execution/broker.py:9-11](execution/broker.py#L9-L11)
`asyncio.new_event_loop()` i `__init__` er skjørt og kan kollidere med en eksisterende loop (særlig i et GUI/web-rammeverk som har sin egen loop). `ib_insync` håndterer dette via `util.startLoop()`. Vurder å bruke deres anbefalte oppsett.

### 🟢 2.8 Forretningslogikk blandet med CLI
[main.py:74-89](main.py#L74-L89)
`input()` gjør koden vanskelig å teste og umulig å gjenbruke fra et GUI. Skill ut en ren API-funksjon (`run_backtest(symbol, start, end) -> dict`) fra presentasjonen, så både CLI, GUI og tester kan kalle samme kjerne.

---

## 3. Avhengigheter & verktøy

### 🟢 3.1 Versjonene i requirements.txt — verifisert
[requirements.txt](requirements.txt)
Sjekket 2026-05-31: `pandas 3.0.3`, `numpy 2.4.6`, `yfinance 1.4.1`, `pytest 9.0.3` er faktisk
installert og fungerer i venv-et (Python 3.14, testpakken kjører grønt). Tidligere bekymring
nedgradert fra 🔴 til 🟢.
- **NB:** Fortsatt verdt å verifisere `backtrader`, `black` og `pytz`-pinningene før du tar dem i bruk,
  og å være obs på at pandas 3.x har copy-on-write som standard hvis du legger til ny kode.

### 🟢 3.2 Mangler dev-verktøyoppsett
Legg til `pyproject.toml` (eller `setup.cfg`) med konfig for `black`, `flake8`/`ruff`, og `pytest`. Vurder `ruff` i stedet for flake8+black (raskere, ett verktøy).

### 🟢 3.3 README nevner `config/secrets.py` som ikke finnes
[README.md:24](README.md#L24)
Koden bruker `.env` via `python-dotenv`, ikke `secrets.py`. Oppdater README (eller fjern referansen) så det er konsistent.

---

## 4. Tester — ✅ GRUNNPAKKE LAGT TIL 2026-05-31

Status: `tests/` opprettet med `pytest.ini` og `conftest.py` (syntetiske OHLCV-fixtures).
**35 tester, alle grønne, ingen nettverk.** Kjør med `venv/bin/python -m pytest`.

Implementert:
- ✅ `tests/test_indicators.py` (SMA/EMA/RSI/MACD/Bollinger, inkl. RSI-divisjon på null)
- ✅ `tests/test_position_sizing.py` (risiko/maks-cap, kurtasje-minimum, Kelly)
- ✅ `tests/test_signals.py` (gyldige signalverdier, gjensidig utelukkende kjøp/salg, ingen mutasjon av input)
- ✅ `tests/test_backtest.py` (tomt datasett, ingen-trades-metrics, kurtasje, negativ kapital, sluttlukking)
- ✅ `tests/test_fetch_data.py` (MultiIndex-flatning, tom/exception-håndtering — `yfinance` mocket)

Hvert bugfiks fra seksjon 1 har en regresjonstest som ville feilet før fiksen.

### Gjenstår å utvide (lavere prioritet)
- `tests/test_broker.py` med mock av `ib_insync.IB` (timeout, ingen ordre uten tilkobling)
- Risiko-metrics i backtest (max drawdown, Sharpe) når seksjon 2.3 implementeres
- CI: GitHub Actions som kjører `pytest` + `ruff` på push
- Mål: ~80% dekning på `analysis/`, `risk/`, `backtest/`

### Detaljer fra opprinnelig plan (referanse)
- **`tests/test_indicators.py`**
  - SMA/EMA mot kjente håndregnede verdier på en liten serie
  - RSI = 100 ved ren oppgang, RSI = 0 ved ren nedgang, ingen kræsj ved `loss == 0`
  - MACD: histogram == macd_line − signal_line
  - Bollinger: middle == SMA, upper/lower symmetrisk rundt middle
  - Riktig antall `NaN` i starten (lik vindusstørrelse − 1)
- **`tests/test_position_sizing.py`**
  - `calculate_position_size` respekterer `RISK_PER_TRADE` og `MAX_POSITION_SIZE`
  - Returnerer 0 når `entry == stop_loss` (price_diff 0)
  - Avrunder ned til hele aksjer
  - `estimate_commission` bruker minimum korrekt (bug 1.1 — skriv testen som feiler nå)
  - Kelly: 0 ved `avg_loss == 0`, cap på 25%, negativt edge → 0
- **`tests/test_signals.py`**
  - Konstruert opptrend gir `Signal == 1`; nedtrend gir `-1`
  - Kjøp og salg er gjensidig utelukkende (ingen bar med begge betingelser sanne)
  - `get_latest_signal` returnerer siste rads signal

### Medium prioritet
- **`tests/test_backtest.py`**
  - Tomt datasett → `{}` uten kræsj
  - Ingen trades → metrics uten `KeyError` (bug 1.4)
  - Kjent prisserie med ett kjøp+salg → forventet `final_capital` (inkl. kurtasje)
  - Kapital går aldri negativ (bug 1.3)
  - Sluttposisjon lukkes med kurtasje (bug 1.5)
- **`tests/test_fetch_data.py`** (med `monkeypatch`/mock av `yf.download`)
  - MultiIndex-kolonner flates ut korrekt
  - Tomt svar → tom DataFrame, ikke exception
  - `get_latest_price` håndterer MultiIndex (bug 1.7)

### Lav prioritet / integrasjon
- **`tests/test_broker.py`** med mock av `ib_insync.IB` — verifiser at `place_order` ikke kalles uten tilkobling, og at timeout respekteres. Aldri test mot ekte IBKR i CI.

### Infrastruktur
- `conftest.py` med fixtures for syntetiske prisserier (trend opp, trend ned, flat, volatil)
- CI: GitHub Actions som kjører `pytest` + `ruff` på push
- Mål: ~80% dekning på `analysis/`, `risk/`, `backtest/`

---

## 5. GUI

Mål: enkelt å kjøre backtest, se resultater/grafer, og (senere) styre live trading.

### Anbefaling: **Streamlit**
Raskest vei fra dagens kode til et brukbart GUI — ren Python, ingen frontend-kode, innebygd graf-/tabellstøtte. Passer perfekt for en personlig trading-bot.

```
gui/
└── app.py        # streamlit run gui/app.py
```

Foreslått funksjonalitet (inkrementelt):
1. **Backtest-fane**
   - Inputs: symbol(er), datointervall, startkapital, strategiparametre (SMA-vinduer, RSI-grenser, stop-loss %)
   - Knapp "Kjør backtest" → kaller den utskilte `run_backtest`-kjernen (se 2.8)
   - Output: nøkkeltall (avkastning, win rate, max drawdown, antall trades) + tabell over trades
   - Grafer: pris med SMA/RSI-overlay, equity-kurve vs. buy & hold (Plotly)
2. **Live/Paper-fane**
   - Statusindikator for IBKR-tilkobling
   - Kontooversikt og åpne posisjoner
   - Tydelig **PAPER vs LIVE**-bryter med bekreftelse før live (unngå utilsiktet ekte handel)
3. **Innstillinger-fane**
   - Rediger config-verdier i UI, lagre til `.env` eller egen `settings.json`

### Forutsetninger i koden før GUI
- Skill logikk fra CLI (2.8) — GUI skal kalle samme funksjoner som tester og CLI
- Gjør strategiparametre til argumenter (2.4)
- IBKR event loop må samspille med Streamlits loop (2.7)

### Status 2026-05-31
- ✅ Logikk separert fra CLI i praksis via `services/trading_service.py`
- ✅ Første web-GUI er på plass i `gui/app.py`
- 🟡 Strategiparametre styres fortsatt delvis via config/env; bør flyttes til eksplisitte runtime-argumenter i signal/backtest-kjeden

### Veien Videre (anbefalt faseplan)
1. **Fase A - Gjør strategien fullt parameterstyrt (kort sikt)**
  - Legg `sma_short`, `sma_long`, `rsi_buy`, `rsi_sell`, `stop_loss_pct` som argumenter i signal/backtest-funksjoner.
  - Bruk samme argumentmodell i CLI, tester og GUI (ett felles kontrakt-objekt / dict).
2. **Fase B - Utvid GUI til beslutningsstotte (kort sikt)**
  - Legg til grafer for equity curve, drawdown og buy-and-hold benchmark.
  - Lagre siste kjoring i en lokal resultattabell (CSV/SQLite) for sammenligning av parameter-sett.
3. **Fase C - Live-status trygt (mellomlang sikt)**
  - Egen Live-fane med tilkoblingsstatus, konto, posisjoner og tydelig PAPER/LIVE-badge.
  - Legg inn `PAPER_ONLY=true` som default-vakt og eksplisitt bekreftelse for live-ordre.
4. **Fase D - API-klar kjerne (mellomlang sikt)**
  - Ekstraher tjenestelaget til et tydelig API-lag (f.eks. FastAPI) uten å endre domenelogikken.
  - Da kan Streamlit beholdes som intern dashboard, eller erstattes av React/frontend senere uten omskriving av trading-kjerne.

### Alternativer
- **FastAPI + enkel HTML/React-frontend** hvis du vil ha noe nettbasert/flerbrukers senere (mer arbeid).
- **Gradio** hvis du vil ha noe enda enklere enn Streamlit (men mindre fleksibelt for dashboards).

---

## 6. Sikkerhet & drift

- 🔴 **Aldri commit `.env`** — er allerede i `.gitignore`. Dobbeltsjekk at ingen nøkler ligger i git-historikken.
- 🟡 Legg til en eksplisitt **`DRY_RUN`/`PAPER_ONLY`-flagg** i config som default `True`, slik at live-handel krever et bevisst valg.
- 🟡 **Ordre-vakter**: maks ordrestørrelse, maks antall trades per dag, kill-switch. Viktig før noe kobles til ekte penger.
- 🟢 Strukturert logging av hver trade til CSV/DB for ettersyn (du logger til fil i dag, men ikke maskinlesbart).

---

## 7. Foreslått rekkefølge

1. Fiks bugs 1.1–1.4 (kritiske, raske) + skriv tester som fanger dem
2. Verifiser `requirements.txt` mot faktisk miljø (3.1)
3. Skill forretningslogikk fra CLI (2.8) + gjør strategiparametre til argumenter (2.4)
4. Bygg testpakken (seksjon 4, høy prioritet)
5. Legg til risiko-metrics i backtest (2.3)
6. Bygg Streamlit-GUI (seksjon 5) på toppen av den rene kjernen
7. Fiks live-trading-kjeden (2.5, 2.6) + ordre-vakter (seksjon 6) — sist, og kun mot paper-konto først
