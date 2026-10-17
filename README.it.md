# FTMO Pro Bot 🚀

![FTMO Pro Bot](https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot/raw/main/screenshot.png)

**Bot Telegram + MetaTrader 5** per il trading automatizzato, progettato per le **sfide FTMO** e gli account finanziati.

Genera segnali, invia pulsanti di conferma su Telegram, esegue trade su MT5 e rispetta rigorosamente le regole di rischio FTMO.

## Lingue

- [English](README.md)
- [Italiano](README.it.md)
- [Shqip](README.sq.md)
- Français, Ελληνικά, Deutsch, Español — presto

## Funzionalità

| Funzionalità                | Descrizione                                      |
|-----------------------------|--------------------------------------------------|
| Controllo Telegram          | Controllo completo, alert e pulsanti di conferma |
| Trading Automatico MT5      | Connessione diretta a MetaTrader 5               |
| Motore Regole FTMO          | Limiti di drawdown e posizioni integrate         |
| Sicuro per Challenge        | Progettato per superare le regole FTMO           |
| Notifiche in tempo reale    | Alert istantanei per entrate, uscite e rischi    |
| Setup facile                | Configurazione semplice con `.env`               |

## Simboli Supportati

- **XAUUSD** (Oro)
- **USDJPY**
- **BTCUSD**

## Strategia

Segnali generati sul timeframe **M15** utilizzando:

- EMA 20 / 50 / 200
- RSI (14)
- MACD (12, 26, 9)
- ATR (14)

## Gestione del Rischio (Regole FTMO)

| Regola                     | Valore         |
|----------------------------|----------------|
| Max trade aperti           | 3              |
| Rischio per trade          | 0.5%           |
| Stop Loss minimo           | 50 punti       |
| Max drawdown giornaliero   | 5%             |
| Max drawdown totale        | 4%             |

## Installazione

1. Clona il repository
   ```bash
   git clone https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot.git
   cd Telegram-trade-bot-ftmo-10-bot
   ```

2. Installa le dipendenze
   ```bash
   pip install -r requirements.txt
   ```

3. Crea e modifica `.env`
   ```bash
   cp .env.example .env
   ```

4. Avvia
   ```bash
   python telegram_bot.py
   ```

## Comandi Telegram

| Comando                              | Descrizione                          |
|--------------------------------------|--------------------------------------|
| `/start`                             | Avvia il bot                         |
| `/connect`                           | Connetti a MT5                       |
| `/status`                            | Mostra stato e trade aperti          |
| `/scan`                              | Scansiona nuovi segnali              |
| `/manual BUY GOLD 0.02 60 120`       | Trade manuale buy                    |
| `/manual SELL USDJPY 0.10 80 160`    | Trade manuale sell                   |
| `/closeall`                          | Chiudi tutte le posizioni            |

## Avviso

> Usa prima su un **account demo**. Il trading comporta rischio di perdita. Non è un consiglio finanziario.

## Requisiti

- Python 3.10+
- MetaTrader 5
- Token Bot Telegram
