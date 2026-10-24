"""Broker-agnostic MT5 signal generation for any tradable Market Watch symbol.

Signals are research/automation inputs, not a profitability guarantee. Symbols must be
enabled in the user's MT5 Market Watch and the broker must provide sufficient history.
"""
import os
from typing import Optional

import MetaTrader5 as mt5

TIMEFRAME_NAME = os.getenv("STRATEGY_TIMEFRAME", "M15").upper()
TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}
TIMEFRAME = TIMEFRAMES.get(TIMEFRAME_NAME, mt5.TIMEFRAME_M15)
EMA_FAST = int(os.getenv("EMA_FAST", "20"))
EMA_MID = int(os.getenv("EMA_MID", "50"))
EMA_TREND = int(os.getenv("EMA_TREND", "200"))
RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
ATR_PERIOD = int(os.getenv("ATR_PERIOD", "14"))
ATR_SL_MULTIPLIER = float(os.getenv("ATR_SL_MULTIPLIER", "1.5"))
REWARD_RISK_RATIO = float(os.getenv("REWARD_RISK_RATIO", "2.0"))
MIN_SIGNAL_SCORE_GAP = int(os.getenv("MIN_SIGNAL_SCORE_GAP", "3"))
MAX_SYMBOLS_PER_SCAN = int(os.getenv("MAX_SYMBOLS_PER_SCAN", "200"))


def ema_series(values, period):
    """EMA series using an SMA seed; returns a list aligned to values."""
    if period < 1 or len(values) < period:
        return []
    alpha = 2.0 / (period + 1.0)
    seed = sum(values[:period]) / period
    result = [None] * (period - 1) + [seed]
    current = seed
    for value in values[period:]:
        current = alpha * value + (1.0 - alpha) * current
        result.append(current)
    return result


def ema(values, period):
    series = ema_series(values, period)
    return series[-1] if series else 0.0


def rsi(values, period=14):
    """Wilder RSI computed over the complete input series."""
    if len(values) < period + 1:
        return 50.0
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(values, fast=12, slow=26, signal=9):
    """Return the latest MACD, signal and histogram values."""
    if len(values) < slow + signal + 5:
        return 0.0, 0.0, 0.0
    fast_line = ema_series(values, fast)
    slow_line = ema_series(values, slow)
    macd_values = [
        fast_line[i] - slow_line[i]
        for i in range(len(values))
        if fast_line[i] is not None and slow_line[i] is not None
    ]
    signal_values = ema_series(macd_values, signal)
    if not signal_values:
        return 0.0, 0.0, 0.0
    line = macd_values[-1]
    signal_line = signal_values[-1]
    return line, signal_line, line - signal_line


def atr(bars, period=14):
    """ATR from MT5 bars represented as (high, low, close)."""
    if len(bars) < period + 1:
        return 0.0
    true_ranges = []
    for i in range(1, len(bars)):
        high, low, _ = bars[i]
        previous_close = bars[i - 1][2]
        true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    recent = true_ranges[-period:]
    return sum(recent) / len(recent) if recent else 0.0


def supported_symbols():
    """Return tradable symbols currently visible in MT5 Market Watch."""
    if not mt5.terminal_info():
        return []
    symbols = mt5.symbols_get()
    if not symbols:
        return []
    result = []
    for item in symbols:
        if not getattr(item, "visible", False):
            continue
        if getattr(item, "trade_mode", mt5.SYMBOL_TRADE_MODE_DISABLED) == mt5.SYMBOL_TRADE_MODE_DISABLED:
            continue
        result.append(item.name)
    result.sort()
    return result[:MAX_SYMBOLS_PER_SCAN]


def _rates(symbol, count=350):
    if not mt5.terminal_info():
        return None
    if not mt5.symbol_select(symbol, True):
        return None
    # Start at position 1 to avoid using the still-forming candle at index 0.
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 1, count)
    if rates is None or len(rates) < max(EMA_TREND + 5, 220):
        return None
    return rates


def generate_signal(symbol: str) -> Optional[dict]:
    symbol = (symbol or "").strip()
    if not symbol:
        return None
    rates = _rates(symbol)
    if rates is None:
        return None

    closes = [float(row["close"]) for row in rates]
    bars = [(float(row["high"]), float(row["low"]), float(row["close"])) for row in rates]
    fast_value = ema(closes, EMA_FAST)
    mid_value = ema(closes, EMA_MID)
    trend_value = ema(closes, EMA_TREND)
    rsi_value = rsi(closes, RSI_PERIOD)
    macd_line, signal_line, histogram = macd(closes)
    atr_value = atr(bars, ATR_PERIOD)
    last_price = closes[-1]
    symbol_info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if symbol_info is None or tick is None or atr_value <= 0:
        return None

    buy_score = 0
    sell_score = 0
    if fast_value > mid_value > trend_value:
        buy_score += 2
    elif fast_value < mid_value < trend_value:
        sell_score += 2
    if rsi_value > 55:
        buy_score += 2
    elif rsi_value < 45:
        sell_score += 2
    if macd_line > signal_line and histogram > 0:
        buy_score += 2
    elif macd_line < signal_line and histogram < 0:
        sell_score += 2
    if last_price > trend_value:
        buy_score += 1
    elif last_price < trend_value:
        sell_score += 1

    if buy_score >= sell_score + MIN_SIGNAL_SCORE_GAP:
        side = "BUY"
        entry = float(tick.ask)
        sl = entry - ATR_SL_MULTIPLIER * atr_value
        tp = entry + REWARD_RISK_RATIO * (entry - sl)
    elif sell_score >= buy_score + MIN_SIGNAL_SCORE_GAP:
        side = "SELL"
        entry = float(tick.bid)
        sl = entry + ATR_SL_MULTIPLIER * atr_value
        tp = entry - REWARD_RISK_RATIO * (sl - entry)
    else:
        return None

    digits = int(symbol_info.digits)
    sl = round(sl, digits)
    tp = round(tp, digits)
    sl_distance = abs(entry - sl)
    tp_distance = abs(tp - entry)
    if sl_distance <= 0 or tp_distance <= sl_distance:
        return None

    return {
        "symbol": symbol,
        "signal": side,
        "price": entry,
        "sl": sl,
        "tp": tp,
        "rsi": rsi_value,
        "ema_short": fast_value,
        "ema_long": mid_value,
        "ema_trend": trend_value,
        "macd": macd_line,
        "macd_signal": signal_line,
        "atr": atr_value,
        "volume": None,  # The execution layer must calculate volume from monetary risk.
        "sl_points": int(round(sl_distance / symbol_info.point)) if symbol_info.point else 0,
        "tp_points": int(round(tp_distance / symbol_info.point)) if symbol_info.point else 0,
        "timeframe": TIMEFRAME_NAME,
        "buy_score": buy_score,
        "sell_score": sell_score,
    }


if __name__ == "__main__":
    if not mt5.initialize():
        raise SystemExit(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        for instrument in supported_symbols():
            signal = generate_signal(instrument)
            if signal:
                print(signal)
    finally:
        mt5.shutdown()
