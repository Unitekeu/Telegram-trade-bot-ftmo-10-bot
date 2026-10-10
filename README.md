# FTMO Pro Bot

This project includes:
- auto signal execution workflow
- pending confirmation buttons
- FTMO-safe risk validation
- MT5 integration for Gold, USDJPY, BTCUSD
- logging for signals and trade execution

## Setup

1. Install requirements
```
pip install -r requirements.txt
```

2. Create `.env` from `.env.example`
3. Run
```
python telegram_bot.py
```

## Commands
- /start
- /connect
- /status
- /scan
- /manual BUY GOLD 0.02 60 120
- /manual SELL USDJPY 0.10 80 160
- /closeall

## Safety
- 3 max open trades
- 0.5% risk cap per trade
- min SL = 50 points
- max daily drawdown = 5%
- max total drawdown = 4%

## Important
Use on demo first. This is not a guarantee of profit.
