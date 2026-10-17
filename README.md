# FTMO Pro Bot 🚀

![BFXTR Logo](https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot/raw/main/logo_main.jpg)

**Telegram + MetaTrader 5** automated trading bot built for **FTMO** challenges and funded accounts. Branding: **@bfxtr**

It generates smart signals, sends confirmation buttons on Telegram, executes trades on MT5, and strictly follows FTMO risk rules.

## Logos

- Main logo: `logo_main.jpg`
- App / Telegram icon: `logo_icon.jpg`
- Banner with Telegram: `logo_telegram.jpg`

## Languages / Gjuhët

- [English](README.md)
- [Français](README.fr.md)
- [Shqip](README.sq.md)
- [Italiano](README.it.md)
- [Ελληνικά](README.el.md)
- [Deutsch](README.de.md)
- [Español](README.es.md)

## Features

| Feature                    | Description                                      |
|----------------------------|--------------------------------------------------|
| Telegram Control           | Full control, alerts, and confirmation buttons   |
| MT5 Automated Trading      | Direct connection to MetaTrader 5                |
| FTMO Risk Rules Engine     | Built-in daily/total drawdown and position limits|
| Challenge & Funded Safe    | Designed to pass FTMO rules                      |
| Real-time Notifications    | Instant alerts for entries, exits, and risks     |
| Easy Setup                 | Simple `.env` configuration                      |

## Supported Symbols

- **XAUUSD** (Gold)
- **USDJPY**
- **BTCUSD**

## Strategy

Signals generated on **M15** timeframe using:

- EMA 20 / 50 / 200
- RSI (14)
- MACD (12, 26, 9)
- ATR (14)

## Risk Management (FTMO Rules)

| Rule                      | Value          |
|---------------------------|----------------|
| Max open trades           | 3              |
| Risk per trade            | 0.5%           |
| Minimum Stop Loss         | 50 points      |
| Max daily drawdown        | 5%             |
| Max total drawdown        | 4%             |

## Setup

1. Clone the repository
   ```bash
   git clone https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot.git
   cd Telegram-trade-bot-ftmo-10-bot
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Create and edit `.env`
   ```bash
   cp .env.example .env
   ```

4. Run
   ```bash
   python telegram_bot.py
   ```

## Telegram Commands

| Command                              | Description                          |
|--------------------------------------|--------------------------------------|
| `/start`                             | Start the bot                        |
| `/connect`                           | Connect to MT5                       |
| `/status`                            | Show status and open trades          |
| `/scan`                              | Scan for new signals                 |
| `/manual BUY GOLD 0.02 60 120`       | Manual buy                           |
| `/manual SELL USDJPY 0.10 80 160`    | Manual sell                          |
| `/closeall`                          | Close all positions                  |

## Warning

> Use on **demo first**. Trading involves risk of loss. This is not financial advice.

## Requirements

- Python 3.10+
- MetaTrader 5
- Telegram Bot Token
