import math

import MetaTrader5 as mt5


def supported_symbols():
    return ["XAUUSD", "USDJPY", "BTCUSD"]


def ema(values, period):
    if not values:
        return 0.0
    k = 2 / (period + 1)
    out = values[0]
    for v in values[1:]:
        out = (v * k) + (out * (1 - k))
    return out


def rsi(values, period=14):
    if len(values) < period + 1:
        return 50.0
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values, fast=12, slow=26, signal=9):
    if len(values) < slow + signal:
        return 0.0, 0.0, 0.0
    fast_ema = ema(values[-fast:], fast)
    slow_ema = ema(values[-slow:], slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(list(values[-(slow + signal):]), signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def atr(values, period=14):
    if len(values) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(values)):
        high = values[i][0]
        low = values[i][1]
        prev_close = values[i - 1][2]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    if len(trs) < period:
        return 0.0
    return sum(trs[-period:]) / period


def get_recent_prices(symbol, count=250):
    if not mt5.initialize():
        return []
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, count)
    if rates is None or len(rates) == 0:
        return []
    return [float(r[4]) for r in rates]


def get_recent_bars(symbol, count=250):
    if not mt5.initialize():
        return []
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, count)
    if rates is None or len(rates) == 0:
        return []
    return [[float(r[2]), float(r[3]), float(r[4])] for r in rates]


def generate_signal(symbol: str):
    symbol = (symbol or "").upper().replace(" ", "")
    aliases = {
        "GOLD": "XAUUSD",
        "XAU": "XAUUSD",
        "USDJPY": "USDJPY",
        "USD/JPY": "USDJPY",
        "BTC": "BTCUSD",
        "BTCUSD": "BTCUSD",
        "BTC/USD": "BTCUSD",
    }
    symbol = aliases.get(symbol, symbol)
    prices = get_recent_prices(symbol, count=300)
    bars = get_recent_bars(symbol, count=300)
    if len(prices) < 150 or len(bars) < 150:
        return None

    ema_fast = ema(prices, 20)
    ema_mid = ema(prices, 50)
    ema_long = ema(prices, 200)
    rsi_value = rsi(prices, 14)
    macd_line, signal_line, hist = macd(prices, fast=12, slow=26, signal=9)
    atr_value = atr(bars, period=14)
    last_price = prices[-1]
    point = 0.0001
    if symbol in ("XAUUSD", "BTCUSD"):
        point = 0.01
    elif symbol == "USDJPY":
        point = 0.01

    buy_score = 0
    sell_score = 0

    if ema_fast > ema_mid > ema_long:
        buy_score += 2
    if ema_fast < ema_mid < ema_long:
        sell_score += 2

    if rsi_value > 55:
        buy_score += 2
    if rsi_value < 45:
        sell_score += 2

    if macd_line > signal_line and hist > 0:
        buy_score += 2
    if macd_line < signal_line and hist < 0:
        sell_score += 2

    if last_price > ema_long:
        buy_score += 1
    if last_price < ema_long:
        sell_score += 1

    if atr_value > 0:
        buy_score += 1
        sell_score += 1

    if buy_score >= sell_score + 3:
        side = "BUY"
        sl_points = 60
        tp_points = 120
        sl = last_price - (sl_points * point)
        tp = last_price + (tp_points * point)
    elif sell_score >= buy_score + 3:
        side = "SELL"
        sl_points = 60
        tp_points = 120
        sl = last_price + (sl_points * point)
        tp = last_price - (tp_points * point)
    else:
        return None

    return {
        "symbol": symbol,
        "signal": side,
        "price": last_price,
        "sl": sl,
        "tp": tp,
        "rsi": rsi_value,
        "ema_short": ema_fast,
        "ema_long": ema_mid,
        "ema_trend": ema_long,
        "macd": macd_line,
        "macd_signal": signal_line,
        "atr": atr_value,
        "volume": 0.02,
        "sl_points": sl_points,
        "tp_points": tp_points,
    }


if __name__ == "__main__":
    print(generate_signal("XAUUSD"))
