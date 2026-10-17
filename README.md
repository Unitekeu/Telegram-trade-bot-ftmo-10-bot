# FTMO Pro Bot 🚀

Telegram bot for automated trading on **MetaTrader 5 (MT5)** with **FTMO-compliant** risk management.

It generates trading signals, sends confirmation buttons on Telegram, and executes trades on MT5 while enforcing strict risk rules.

## Features

- Auto signal generation and execution
- Telegram confirmation buttons before trade
- FTMO-safe risk controls
- MT5 integration (Gold, USDJPY, BTCUSD)
- Trade & signal logging
- Manual trade commands
- Status and scan commands

## Supported Symbols

- **XAUUSD** (Gold)
- **USDJPY**
- **BTCUSD**

## Strategy

Signals are generated on the **M15** timeframe using:

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

1. **Clone the repository**
   ```bash
   git clone https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot.git
   cd Telegram-trade-bot-ftmo-10-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create environment file**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and fill in:
   - `TELEGRAM_BOT_TOKEN`
   - `MT5_LOGIN`
   - `MT5_PASSWORD`
   - `MT5_SERVER`

4. **Run the bot**
   ```bash
   python telegram_bot.py
   ```

## Telegram Commands

| Command                              | Description                          |
|--------------------------------------|--------------------------------------|
| `/start`                             | Start the bot                        |
| `/connect`                           | Connect to MT5                       |
| `/status`                            | Show current status & open trades    |
| `/scan`                              | Scan for new signals                 |
| `/manual BUY GOLD 0.02 60 120`       | Manual buy trade                     |
| `/manual SELL USDJPY 0.10 80 160`    | Manual sell trade                    |
| `/closeall`                          | Close all open positions             |

## Important Warning

> **Use on demo account first.**  
> This bot is for educational purposes. Trading involves risk. Past performance does not guarantee future results. The developer is not responsible for any financial losses.

## Requirements

- Python 3.10+
- MetaTrader 5 terminal installed and logged in
- Telegram Bot Token

## License

MIT (add a license file if needed)
