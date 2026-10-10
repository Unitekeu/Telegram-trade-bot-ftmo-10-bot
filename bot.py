import logging
from typing import Dict, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
import MetaTrader5 as mt5

from config import (
    DEFAULT_LOT,
    MAX_OPEN_TRADES,
    MAX_DAILY_DRAWDOWN_PERCENT,
    MAX_TOTAL_DRAWDOWN_PERCENT,
    MIN_STOP_LOSS_POINTS,
    MT5_LOGIN,
    MT5_PASSWORD,
    MT5_SERVER,
    RISK_PERCENT,
    TELEGRAM_BOT_TOKEN,
)
from strategy import generate_signal, supported_symbols

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

pending_signals: Dict[int, Dict[str, Any]] = {}


class MT5Client:
    def __init__(self, login, password, server):
        self.login = login
        self.password = password
        self.server = server
        self.connected = False

    def normalize_symbol(self, symbol: str):
        s = (symbol or "").strip().upper().replace(" ", "")
        aliases = {
            "GOLD": "XAUUSD",
            "XAU": "XAUUSD",
            "XAUUSD": "XAUUSD",
            "USDJPY": "USDJPY",
            "USD/JPY": "USDJPY",
            "BTC": "BTCUSD",
            "BTCUSD": "BTCUSD",
            "BTC/USD": "BTCUSD",
            "BITCOIN": "BTCUSD",
        }
        return aliases.get(s, s)

    def connect(self):
        if self.login == 0 or not self.password or not self.server:
            raise RuntimeError("MT5 login/password/server missing. Check .env")
        if not mt5.initialize(login=self.login, password=self.password, server=self.server):
            raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
        self.connected = True
        return True

    def account_info(self):
        if not self.connected:
            return None
        info = mt5.account_info()
        if info is None:
            return None
        return {
            "login": info.login,
            "balance": float(info.balance),
            "equity": float(info.equity),
            "margin": float(info.margin),
            "free_margin": float(info.margin_free),
            "profit": float(info.profit),
            "currency": info.currency,
        }

    def get_symbol_info(self, symbol):
        if not self.connected:
            return None
        return mt5.symbol_info(symbol)

    def market_price(self, symbol):
        if not self.connected:
            return None
        normalized = self.normalize_symbol(symbol)
        tick = mt5.symbol_info_tick(normalized)
        if tick is None:
            return None
        return {
            "symbol": normalized,
            "ask": float(tick.ask),
            "bid": float(tick.bid),
            "last": float(tick.last),
        }

    def buy(self, symbol, volume, sl=None, tp=None, comment="AUTO BUY"):
        if not self.connected:
            raise RuntimeError("MT5 not connected")
        normalized = self.normalize_symbol(symbol)
        if self.get_symbol_info(normalized) is None:
            raise RuntimeError(f"Symbol {normalized} not found in MT5")
        tick = mt5.symbol_info_tick(normalized)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": normalized,
            "volume": float(volume),
            "type": mt5.ORDER_TYPE_BUY,
            "price": tick.ask,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 123456,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        return mt5.order_send(request)

    def sell(self, symbol, volume, sl=None, tp=None, comment="AUTO SELL"):
        if not self.connected:
            raise RuntimeError("MT5 not connected")
        normalized = self.normalize_symbol(symbol)
        if self.get_symbol_info(normalized) is None:
            raise RuntimeError(f"Symbol {normalized} not found in MT5")
        tick = mt5.symbol_info_tick(normalized)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": normalized,
            "volume": float(volume),
            "type": mt5.ORDER_TYPE_SELL,
            "price": tick.bid,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 123456,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        return mt5.order_send(request)

    def positions(self):
        if not self.connected:
            return []
        return mt5.positions_get()

    def close_all_positions(self):
        if not self.connected:
            return []
        positions = mt5.positions_get()
        closed = []
        for pos in positions or []:
            symbol = pos.symbol
            type_order = pos.type
            volume = pos.volume
            tick = mt5.symbol_info_tick(symbol)
            if type_order == mt5.ORDER_TYPE_BUY:
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": float(volume),
                    "type": mt5.ORDER_TYPE_SELL,
                    "price": tick.bid,
                    "deviation": 10,
                    "magic": 123456,
                    "comment": "Close BUY",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
            else:
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": float(volume),
                    "type": mt5.ORDER_TYPE_BUY,
                    "price": tick.ask,
                    "deviation": 10,
                    "magic": 123456,
                    "comment": "Close SELL",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
            result = mt5.order_send(request)
            closed.append({"ticket": pos.ticket, "symbol": symbol, "result": result})
        return closed


mt5_client = MT5Client(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)


def validate_trade_dimensions(account_info, positions_count, volume, sl_points, tp_points):
    if not account_info:
        return False, "Account info unavailable."
    if positions_count >= MAX_OPEN_TRADES:
        return False, f"Max open trades reached: {MAX_OPEN_TRADES}."
    if sl_points < MIN_STOP_LOSS_POINTS:
        return False, f"Stop loss too small. Minimum is {MIN_STOP_LOSS_POINTS} points."
    if tp_points <= sl_points:
        return False, "Take profit must be bigger than stop loss."
    if volume <= 0:
        return False, "Volume must be greater than zero."

    balance = account_info["balance"]
    profit = account_info["profit"]
    daily_limit = balance * (MAX_DAILY_DRAWDOWN_PERCENT / 100.0)
    total_limit = balance * (MAX_TOTAL_DRAWDOWN_PERCENT / 100.0)
    if profit <= -daily_limit:
        return False, f"Daily drawdown limit reached: {MAX_DAILY_DRAWDOWN_PERCENT}%"
    if profit <= -total_limit:
        return False, f"Total drawdown limit reached: {MAX_TOTAL_DRAWDOWN_PERCENT}%"
    return True, "OK"


def build_signal_message(signal_info: Dict[str, Any]) -> str:
    if not signal_info:
        return "No valid signal detected."
    symbol = signal_info["symbol"]
    side = signal_info["signal"]
    price = signal_info["price"]
    stop = signal_info["sl"]
    take = signal_info["tp"]
    rsi = signal_info["rsi"]
    ema_short = signal_info["ema_short"]
    ema_long = signal_info["ema_long"]
    ema_trend = signal_info["ema_trend"]
    return (
        f"📡 *AUTO SIGNAL*\n\n"
        f"Symbol: {symbol}\n"
        f"Direction: {side}\n"
        f"Price: {price:.5f}\n"
        f"SL: {stop:.5f}\n"
        f"TP: {take:.5f}\n"
        f"RSI(14): {rsi:.2f}\n"
        f"EMA20: {ema_short:.5f}\n"
        f"EMA50: {ema_long:.5f}\n"
        f"EMA200: {ema_trend:.5f}\n\n"
        f"Use the buttons below to confirm or reject."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥 *AUTO SIGNAL FTMO BOT*\n\n"
        "• /connect\n"
        "• /status\n"
        "• /scan\n"
        "• /manual BUY GOLD 0.02 60 120\n"
        "• /manual SELL USDJPY 0.10 80 160\n"
        "• /closeall\n\n"
        "This bot generates automatic trade signals from EMA + RSI logic and allows manual confirmation before executing."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def connect_mt5(update, context):
    try:
        mt5_client.connect()
        await update.message.reply_text("✅ MT5 connected.")
    except Exception as e:
        await update.message.reply_text(f"❌ MT5 connection failed: {e}")


async def status(update, context):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 not connected. Use /connect")
        return
    info = mt5_client.account_info()
    if not info:
        await update.message.reply_text("❌ Could not read account info.")
        return
    positions = mt5_client.positions()
    pos_text = "No active positions."
    if positions:
        pos_text = "\n".join(
            [f"- {p.symbol} | {p.type} | Vol: {p.volume} | P/L: {p.profit}" for p in positions]
        )
    text = (
        "📊 *ACCOUNT STATUS*\n\n"
        f"Balance: ${info['balance']:.2f}\n"
        f"Equity: ${info['equity']:.2f}\n"
        f"Profit: ${info['profit']:.2f}\n"
        f"Margin: ${info['margin']:.2f}\n"
        f"Free Margin: ${info['free_margin']:.2f}\n\n"
        f"Positions:\n{pos_text}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def manual_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 not connected. /connect first.")
        return
    if len(context.args) < 5:
        await update.message.reply_text("Use: /manual BUY GOLD 0.02 60 120 \nor\n /manual SELL USDJPY 0.10 80 160")
        return
    side = context.args[0].upper()
    symbol = context.args[1].upper()
    volume = float(context.args[2])
    sl_points = int(context.args[3])
    tp_points = int(context.args[4])
    normalized = mt5_client.normalize_symbol(symbol)
    market = mt5_client.market_price(normalized)
    if not market:
        await update.message.reply_text(f"❌ {normalized} is not available in MT5.")
        return
    info = mt5_client.account_info()
    ok, msg = validate_trade_dimensions(info, len(mt5_client.positions() or []), volume, sl_points, tp_points)
    if not ok:
        await update.message.reply_text(f"❌ {msg}")
        return
    if side == "BUY":
        sl_value = market["ask"] - (sl_points * 0.0001)
        tp_value = market["ask"] + (tp_points * 0.0001)
        result = mt5_client.buy(normalized, volume, sl=sl_value, tp=tp_value, comment="MANUAL BUY")
    elif side == "SELL":
        sl_value = market["bid"] + (sl_points * 0.0001)
        tp_value = market["bid"] - (tp_points * 0.0001)
        result = mt5_client.sell(normalized, volume, sl=sl_value, tp=tp_value, comment="MANUAL SELL")
    else:
        await update.message.reply_text("Use BUY or SELL")
        return
    if result is None or result.retcode not in (0, 10009, 10008):
        await update.message.reply_text(f"❌ Order failed: {result.comment if result else 'Unknown error'}")
        return
    await update.message.reply_text(f"✅ Manual {side} order executed for {normalized}.")


async def scan_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 not connected. Use /connect")
        return
    results = []
    for symbol in supported_symbols():
        signal_info = generate_signal(symbol)
        if signal_info and signal_info["signal"] in ("BUY", "SELL"):
            results.append(signal_info)
    if not results:
        await update.message.reply_text("📡 No valid auto-signal found right now.")
        return
    for item in results[:3]:
        message = build_signal_message(item)
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{item['symbol']}|{item['signal']}|{item['volume']}|{item['sl_points']}|{item['tp_points']}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject|{item['symbol']}|{item['signal']}"),
            ]]
        )
        pending_signals[update.effective_chat.id] = item
        await update.message.reply_text(message, parse_mode="Markdown", reply_markup=keyboard)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    parts = data.split("|")
    if not parts:
        return
    action = parts[0]
    if action == "reject":
        await query.edit_message_text("❌ Signal rejected.")
        return
    if action == "confirm":
        if len(parts) < 6:
            await query.edit_message_text("❌ Invalid signal payload.")
            return
        symbol = parts[1]
        side = parts[2]
        volume = float(parts[3])
        sl_points = int(parts[4])
        tp_points = int(parts[5])
        market = mt5_client.market_price(symbol)
        if not market:
            await query.edit_message_text(f"❌ {symbol} unavailable in MT5.")
            return
        info = mt5_client.account_info()
        ok, msg = validate_trade_dimensions(info, len(mt5_client.positions() or []), volume, sl_points, tp_points)
        if not ok:
            await query.edit_message_text(f"❌ {msg}")
            return
        if side == "BUY":
            sl_value = market["ask"] - (sl_points * 0.0001)
            tp_value = market["ask"] + (tp_points * 0.0001)
            result = mt5_client.buy(symbol, volume, sl=sl_value, tp=tp_value, comment="AUTO SIGNAL BUY")
            success_text = f"✅ Auto BUY executed for {symbol}."
        else:
            sl_value = market["bid"] + (sl_points * 0.0001)
            tp_value = market["bid"] - (tp_points * 0.0001)
            result = mt5_client.sell(symbol, volume, sl=sl_value, tp=tp_value, comment="AUTO SIGNAL SELL")
            success_text = f"✅ Auto SELL executed for {symbol}."
        if result is None or result.retcode not in (0, 10009, 10008):
            await query.edit_message_text(f"❌ Trade rejected by MT5: {result.comment if result else 'Unknown error'}")
            return
        await query.edit_message_text(success_text)


async def close_all(update, context):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 not connected.")
        return
    mt5_client.close_all_positions()
    await update.message.reply_text("✅ All positions closed.")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing. Add it in .env")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("connect", connect_mt5))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("scan", scan_signals))
    app.add_handler(CommandHandler("manual", manual_trade))
    app.add_handler(CommandHandler("closeall", close_all))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("Auto signal bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
