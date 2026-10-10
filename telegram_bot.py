import logging
from typing import Any, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
import MetaTrader5 as mt5

from config import (
    DEFAULT_LOT,
    MAX_DAILY_DRAWDOWN_PERCENT,
    MAX_OPEN_TRADES,
    MAX_TOTAL_DRAWDOWN_PERCENT,
    MIN_STOP_LOSS_POINTS,
    MT5_LOGIN,
    MT5_PASSWORD,
    MT5_SERVER,
    RISK_PERCENT,
    TELEGRAM_BOT_TOKEN,
)
from strategy import generate_signal, supported_symbols
from ftmo_controller import FTMORiskController
from trade_logger import TradeLogger

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

ftmo_controller = FTMORiskController(initial_balance=200000)
trade_logger = TradeLogger()

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
        tick = mt5.symbol_info_tick(normalized)
        if tick is None:
            raise RuntimeError(f"Symbol {normalized} not available in MT5")
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
        tick = mt5.symbol_info_tick(normalized)
        if tick is None:
            raise RuntimeError(f"Symbol {normalized} not available in MT5")
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
        return mt5.positions_get() or []

    def close_all_positions(self):
        if not self.connected:
            return []
        positions = mt5.positions_get() or []
        closed = []
        for pos in positions:
            symbol = pos.symbol
            tick = mt5.symbol_info_tick(symbol)
            if pos.type == mt5.ORDER_TYPE_BUY:
                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": float(pos.volume),
                    "type": mt5.ORDER_TYPE_SELL,
                    "price": tick.bid,
                    "deviation": 10,
                    "magic": 123456,
                    "comment": "Close BUY",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
            else:
                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": float(pos.volume),
                    "type": mt5.ORDER_TYPE_BUY,
                    "price": tick.ask,
                    "deviation": 10,
                    "magic": 123456,
                    "comment": "Close SELL",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
            result = mt5.order_send(req)
            closed.append({"ticket": pos.ticket, "symbol": symbol, "result": result})
        return closed


mt5_client = MT5Client(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)


def build_signal_message(signal_info: Dict[str, Any]) -> str:
    symbol = signal_info["symbol"]
    side = signal_info["signal"]
    price = signal_info["price"]
    sl = signal_info["sl"]
    tp = signal_info["tp"]
    rsi = signal_info["rsi"]
    ema_short = signal_info["ema_short"]
    ema_long = signal_info["ema_long"]
    ema_trend = signal_info["ema_trend"]
    macd = signal_info.get("macd", 0)
    atr = signal_info.get("atr", 0)

    return (
        f"📡 *AUTO SIGNAL*\n\n"
        f"Symbol: {symbol}\n"
        f"Direction: {side}\n"
        f"Price: {price:.5f}\n"
        f"SL: {sl:.5f}\n"
        f"TP: {tp:.5f}\n"
        f"RSI: {rsi:.2f}\n"
        f"EMA20: {ema_short:.5f}\n"
        f"EMA50: {ema_long:.5f}\n"
        f"EMA200: {ema_trend:.5f}\n"
        f"MACD: {macd:.5f}\n"
        f"ATR: {atr:.5f}\n\n"
        "Use the buttons below to confirm or reject this signal."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥 *FTMO PRO SIGNAL BOT*\n\n"
        "• /connect\n"
        "• /status\n"
        "• /scan\n"
        "• /manual BUY GOLD 0.02 60 120\n"
        "• /manual SELL USDJPY 0.10 80 160\n"
        "• /closeall\n\n"
        "🛡️ FTMO protections:\n"
        "• Max 3 positions\n"
        f"• Risk per trade: {RISK_PERCENT}%\n"
        f"• Min SL: {MIN_STOP_LOSS_POINTS} points\n"
        f"• Max daily drawdown: {MAX_DAILY_DRAWDOWN_PERCENT}%\n"
        f"• Max total drawdown: {MAX_TOTAL_DRAWDOWN_PERCENT}%"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def connect_mt5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mt5_client.connect()
        await update.message.reply_text("✅ MT5 connection successful.")
    except Exception as e:
        await update.message.reply_text(f"❌ MT5 connection failed: {e}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 is not connected. Use /connect first.")
        return
    info = mt5_client.account_info()
    if not info:
        await update.message.reply_text("❌ Could not read account info.")
        return
    ftmo_text = ftmo_controller.format_status(info)
    positions = mt5_client.positions()
    pos_text = "No active positions."
    if positions:
        pos_text = "\n".join(
            [f"- {p.symbol} | {p.type} | Vol: {p.volume} | P/L: ${p.profit:.2f}" for p in positions]
        )
    text = f"{ftmo_text}\n\n📊 Active positions:\n{pos_text}"
    await update.message.reply_text(text, parse_mode="Markdown")


async def manual_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 not connected. Use /connect first.")
        return
    if len(context.args) < 5:
        await update.message.reply_text("Use: /manual BUY GOLD 0.02 60 120\nOr\n/manual SELL USDJPY 0.10 80 160")
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
    ok, msg = ftmo_controller.validate_trade(info, len(mt5_client.positions()), volume, sl_points, tp_points)
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
        await update.message.reply_text("Use BUY or SELL.")
        return
    if result is None or result.retcode not in (0, 10009, 10008):
        await update.message.reply_text(f"❌ Order failed: {result.comment if result else 'Unknown error'}")
        return
    trade_logger.log_trade({
        "event": "manual_trade",
        "symbol": normalized,
        "direction": side,
        "volume": volume,
        "sl": sl_value,
        "tp": tp_value,
    })
    await update.message.reply_text(f"✅ Manual {side} order executed for {normalized}.")


async def scan_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 not connected. Use /connect first.")
        return
    found_signal = False
    for symbol in supported_symbols():
        signal = generate_signal(symbol)
        if signal is None:
            continue
        trade_logger.log_signal({"symbol": signal["symbol"], "signal": signal["signal"], "price": signal["price"], "rsi": signal["rsi"], "ema_short": signal["ema_short"], "ema_long": signal["ema_long"], "ema_trend": signal["ema_trend"]})
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{signal['symbol']}|{signal['signal']}|{signal['volume']}|{signal['sl_points']}|{signal['tp_points']}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject|{signal['symbol']}|{signal['signal']}"),
            ]
        ])
        await update.message.reply_text(build_signal_message(signal), parse_mode="Markdown", reply_markup=keyboard)
        found_signal = True
    if not found_signal:
        await update.message.reply_text("📡 No valid signal found right now.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    parts = data.split("|")
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
            await query.edit_message_text(f"❌ {symbol} not available in MT5.")
            return
        info = mt5_client.account_info()
        ok, msg = ftmo_controller.validate_trade(info, len(mt5_client.positions()), volume, sl_points, tp_points)
        if not ok:
            await query.edit_message_text(f"❌ {msg}")
            return
        if side == "BUY":
            sl_value = market["ask"] - (sl_points * 0.0001)
            tp_value = market["ask"] + (tp_points * 0.0001)
            result = mt5_client.buy(symbol, volume, sl=sl_value, tp=tp_value, comment="AUTO CONFIRMED BUY")
            final_text = f"✅ Auto BUY executed for {symbol}."
        else:
            sl_value = market["bid"] + (sl_points * 0.0001)
            tp_value = market["bid"] - (tp_points * 0.0001)
            result = mt5_client.sell(symbol, volume, sl=sl_value, tp=tp_value, comment="AUTO CONFIRMED SELL")
            final_text = f"✅ Auto SELL executed for {symbol}."
        if result is None or result.retcode not in (0, 10009, 10008):
            await query.edit_message_text(f"❌ Trade failed: {result.comment if result else 'Unknown error'}")
            return
        trade_logger.log_trade({
            "event": "auto_confirmed_trade",
            "symbol": symbol,
            "direction": side,
            "volume": volume,
            "sl": sl_value,
            "tp": tp_value,
        })
        await query.edit_message_text(final_text)


async def close_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 not connected. Use /connect first.")
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
    print("FTMO Pro Signal Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
