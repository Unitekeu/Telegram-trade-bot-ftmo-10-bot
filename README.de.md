# FTMO Pro Bot 🚀

![FTMO Pro Bot](https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot/raw/main/screenshot.png)

**Telegram + MetaTrader 5** Bot für automatisierten Handel, entwickelt für **FTMO-Challenges** und finanzierte Konten.

Er generiert Signale, sendet Bestätigungsbuttons auf Telegram, führt Trades auf MT5 aus und hält sich strikt an die FTMO-Risikoregeln.

## Sprachen

- [English](README.md)
- [Deutsch](README.de.md)
- [Shqip](README.sq.md)
- Français, Italiano, Ελληνικά, Español — bald

## Funktionen

| Funktion                   | Beschreibung                                     |
|----------------------------|--------------------------------------------------|
| Telegram-Kontrolle         | Volle Kontrolle, Alerts und Bestätigungsbuttons   |
| Automatischer MT5-Handel   | Direkte Verbindung zu MetaTrader 5               |
| FTMO-Risikoregeln-Engine   | Integrierte Drawdown- und Positionslimits        |
| Challenge-sicher           | Entwickelt, um FTMO-Regeln zu bestehen           |
| Echtzeit-Benachrichtigungen| Sofortige Alerts für Entries, Exits und Risiken  |
| Einfaches Setup            | Einfache Konfiguration mit `.env`                |

## Unterstützte Symbole

- **XAUUSD** (Gold)
- **USDJPY**
- **BTCUSD**

## Strategie

Signale auf dem **M15**-Timeframe generiert mit:

- EMA 20 / 50 / 200
- RSI (14)
- MACD (12, 26, 9)
- ATR (14)

## Risikomanagement (FTMO-Regeln)

| Regel                      | Wert           |
|----------------------------|----------------|
| Max offene Trades          | 3              |
| Risiko pro Trade           | 0.5%           |
| Minimaler Stop Loss        | 50 Punkte      |
| Max täglicher Drawdown     | 5%             |
| Max Gesamtdrawdown         | 4%             |

## Installation

1. Repository klonen
   ```bash
   git clone https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot.git
   cd Telegram-trade-bot-ftmo-10-bot
   ```

2. Abhängigkeiten installieren
   ```bash
   pip install -r requirements.txt
   ```

3. `.env` erstellen und bearbeiten
   ```bash
   cp .env.example .env
   ```

4. Starten
   ```bash
   python telegram_bot.py
   ```

## Telegram-Befehle

| Befehl                               | Beschreibung                         |
|--------------------------------------|--------------------------------------|
| `/start`                             | Bot starten                          |
| `/connect`                           | Mit MT5 verbinden                    |
| `/status`                            | Status und offene Trades anzeigen    |
| `/scan`                              | Nach neuen Signalen scannen          |
| `/manual BUY GOLD 0.02 60 120`       | Manueller Buy-Trade                  |
| `/manual SELL USDJPY 0.10 80 160`    | Manueller Sell-Trade                 |
| `/closeall`                          | Alle Positionen schließen            |

## Warnung

> Zuerst auf einem **Demo-Konto** verwenden. Handel birgt Verlustrisiko. Dies ist keine Finanzberatung.

## Anforderungen

- Python 3.10+
- MetaTrader 5
- Telegram Bot Token
