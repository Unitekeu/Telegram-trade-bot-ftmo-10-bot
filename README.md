# Universal MT5 Signal Bot

Telegram + MetaTrader 5 signal and execution bot. It scans **visible, tradable instruments in MT5 Market Watch**, using broker-provided symbol specifications rather than hard-coded pip/point assumptions.

> **Risk warning:** this software is not guaranteed profitable and is not certified to comply with FTMO or another prop firm's rules. Test on a demo account and validate every instrument, order size, spread, stop level, swap, commission and execution mode before considering live use.

## Instrument coverage

The bot can scan any instrument exposed as visible and tradable by the connected MT5 broker, including (if your broker provides them) forex pairs, metals, indices, energies, shares, ETFs, futures, CFDs and cryptocurrencies. Availability, trading hours and symbol names depend on the broker. Enable the desired instruments in MT5 Market Watch first. Some instruments may not have enough history or may not support the same order features.

## Strategy

- Configurable timeframe (default M15).
- EMA 20/50/200 trend alignment, Wilder RSI(14), correctly constructed MACD(12,26,9).
- ATR-based stop distance and configurable reward/risk ratio.
- Uses the last **closed** candle, not the live forming candle.
- SL/TP are price distances derived from each instrument's ATR, not a universal fixed number of points.
- Position size is calculated using MT5's `order_calc_profit` and the broker's volume minimum/maximum/step, aiming to keep estimated SL loss within the configured equity risk.

These are baseline rules, not proof of an edge. The same parameters will not perform equally across every asset class; build and validate separate backtests by instrument and timeframe.

## Safety controls

- Only positions tagged with this bot's magic number are counted/targeted by the bot's close command.
- Trade size is blocked if the broker minimum lot would exceed the configured risk budget.
- The bot blocks orders if it cannot calculate risk, cannot obtain a quote, sees invalid SL/TP geometry, or sees excessive spread relative to the stop.
- Restrict Telegram commands with `TELEGRAM_ALLOWED_USER_IDS`.
- This version does **not** yet implement a persistent, rule-accurate daily/overall drawdown engine. Do not use it on a prop challenge or funded account until those limits are implemented and tested against the firm's current rules.

## Setup

1. Install Python 3.10+, MetaTrader 5 terminal, and the packages:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your own credentials and numeric Telegram user ID.
3. Keep `.env` private; never commit credentials or bot tokens.
4. Open MT5, sign in to the intended demo account, enable instruments in Market Watch, and ensure the terminal can trade.
5. Start the modular bot:
   ```bash
   python bot.py
   ```
6. In Telegram, run `/connect`, then `/status` and `/scan`.

## Commands

- `/start` — show commands.
- `/connect` — connect to MT5.
- `/status` — account status and positions opened by this bot.
- `/scan` — scan visible tradable Market Watch symbols.
- `/manual BUY SYMBOL VOLUME SL_PRICE TP_PRICE` — place a manual order using explicit prices, subject to the configured risk cap.
- `/closeall` — request closure of positions carrying the bot's magic number only.

Example manual command (replace with the exact symbol and prices for your broker):
```
/manual BUY EURUSD 0.01 1.08000 1.08400
```

## Important limitations

- Broker-specific execution modes, market sessions, margin rules and contract specifications differ. Validate on demo for each asset class.
- The risk estimate does not fully account for gaps, slippage, spread changes, commissions or execution failures.
- This version does not yet implement a persistent daily/maximum drawdown lock, trailing stop, economic calendar/news filter, portfolio correlation cap, or backtesting harness.
- `telegram_bot.py` is a legacy entry point; use `bot.py` for the modular implementation.
