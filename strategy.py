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


def get_recent_prices(symbol, count=250):
    if not mt5.initialize():
        return []
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, count)
    if rates is None or len(rates) == 0:
        return []
    return [float(r[4]) for r in rates]


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
    prices = get_recent_prices(symbol, count=250)
    if len(prices) < 120:
        return None
    ema_fast = ema(prices, 20)
    ema_slow = ema(prices, 50)
    ema_trend = ema(prices, 200)
    rsi_value = rsi(prices, 14)
    last_price = prices[-1]
    info = mt5.symbol_info(symbol)
    if info is None:
        return None
    point_size = info.point
    if point_size <= 0:
        point_size = 0.0001

    if ema_fast > ema_slow > ema_trend and rsi_value > 55 and last_price > ema_trend:
        side = "BUY"
        sl_points = 60
        tp_points = 120
        sl = last_price - (sl_points * point_size)
        tp = last_price + (tp_points * point_size)
    elif ema_fast < ema_slow < ema_trend and rsi_value < 45 and last_price < ema_trend:
        side = "SELL"
        sl_points = 60
        tp_points = 120
        sl = last_price + (sl_points * point_size)
        tp = last_price - (tp_points * point_size)
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
        "ema_long": ema_slow,
        "ema_trend": ema_trend,
        "volume": 0.02,
        "sl_points": sl_points,
        "tp_points": tp_points,
    }
