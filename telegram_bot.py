import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import MetaTrader5 as mt5

# =========================================
# CONFIG
# =========================================
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
MT5_LOGIN = 0
MT5_PASSWORD = ""
MT5_SERVER = "YOUR_SERVER"

MAX_OPEN_TRADES = 3
MAX_DAILY_DRAWDOWN_PERCENT = 5.0
MAX_TOTAL_DRAWDOWN_PERCENT = 4.0
MIN_STOP_LOSS_POINTS = 50
RISK_PERCENT = 0.5

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# =========================================
# MT5 CLIENT
# =========================================
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
            raise RuntimeError("MT5 login/password/server missing")
        if not mt5.initialize(login=self.login, password=self.password, server=self.server):
            raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
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

    def buy(self, symbol, volume, sl=None, tp=None, comment="BUY"):
        if not self.connected:
            raise RuntimeError("MT5 not connected")
        normalized = self.normalize_symbol(symbol)
        tick = mt5.symbol_info_tick(normalized)
        if tick is None:
            raise RuntimeError(f"Symbol {normalized} not found")
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

    def sell(self, symbol, volume, sl=None, tp=None, comment="SELL"):
        if not self.connected:
            raise RuntimeError("MT5 not connected")
        normalized = self.normalize_symbol(symbol)
        tick = mt5.symbol_info_tick(normalized)
        if tick is None:
            raise RuntimeError(f"Symbol {normalized} not found")
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

# =========================================
# FTMO VALIDATION
# =========================================
def validate_trade_dimensions(account_info, positions_count, volume, sl_points, tp_points):
    if not account_info:
        return False, "Account info unavailable."
    if positions_count >= MAX_OPEN_TRADES:
        return False, f"Max open trades: {MAX_OPEN_TRADES}"
    if volume <= 0:
        return False, "Volume must be > 0"
    if sl_points < MIN_STOP_LOSS_POINTS:
        return False, f"SL too small. Min: {MIN_STOP_LOSS_POINTS} points"
    if tp_points <= sl_points:
        return False, "TP must be > SL"

    balance = account_info["balance"]
    profit = account_info["profit"]
    daily_limit = balance * (MAX_DAILY_DRAWDOWN_PERCENT / 100.0)
    total_limit = balance * (MAX_TOTAL_DRAWDOWN_PERCENT / 100.0)

    if profit <= -daily_limit:
        return False, f"Daily limit reached: {MAX_DAILY_DRAWDOWN_PERCENT}%"
    if profit <= -total_limit:
        return False, f"Total limit reached: {MAX_TOTAL_DRAWDOWN_PERCENT}%"

    return True, "OK"


# =========================================
# FIBO LOGIC
# =========================================
def fib_partial_levels(entry, direction):
    """Calculate TP1, TP2, TP3, SL for Fibo strategy"""
    if direction == "BUY":
        return {
            "TP1": entry + 0.022,
            "TP2": entry + 0.044,
            "TP3": entry + 0.099,
            "SL": entry - 0.060,
        }
    else:  # SELL
        return {
            "TP1": entry - 0.022,
            "TP2": entry - 0.044,
            "TP3": entry - 0.099,
            "SL": entry + 0.060,
        }


def partial_close_split(total_volume):
    """Split volume: 33% / 33% / 34%"""
    v1 = total_volume * 0.33
    v2 = total_volume * 0.33
    v3 = total_volume * 0.34
    return round(v1, 3), round(v2, 3), round(v3, 3)


# =========================================
# TELEGRAM COMMANDS
# =========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🔥 *FIBO FTMO BOT*\n\n"
        "Commands:\n"
        "• /connect\n"
        "• /status\n"
        "• /buyfibo GOLD 0.02\n"
        "• /sellfibo USDJPY 0.10\n"
        "• /closeall\n\n"
        "Fibo targets:\n"
        "TP1 = +0.022\n"
        "TP2 = +0.044\n"
        "TP3 = +0.099\n"
        "SL = -0.060\n\n"
        "Volume split: 33% / 33% / 34%"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def connect_mt5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mt5_client.connect()
        await update.message.reply_text("✅ MT5 connected.")
    except Exception as e:
        await update.message.reply_text(f"❌ MT5 connection failed: {e}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 not connected. Use /connect first.")
        return

    info = mt5_client.account_info()
    if not info:
        await update.message.reply_text("❌ Could not read account info.")
        return

    positions = mt5_client.positions()
    pos_text = "No active positions."
    if positions:
        pos_text = "\n".join(
            [f"• {p.symbol} | {p.type} | Vol: {p.volume} | P/L: ${p.profit:.2f}" for p in positions]
        )

    balance = info["balance"]
    profit = info["profit"]
    daily_pct = (abs(profit) / balance * 100) if profit < 0 else 0
    total_pct = (abs(profit) / balance * 100) if profit < 0 else 0

    status_icon = "🟢" if daily_pct < 80 else "🟡" if daily_pct < 100 else "🔴"

    msg = (
        f"{status_icon} *ACCOUNT STATUS*\n\n"
        f"Balance: ${balance:.2f}\n"
        f"Equity: ${info['equity']:.2f}\n"
        f"Profit: ${profit:.2f}\n"
        f"Margin: ${info['margin']:.2f}\n"
        f"Free Margin: ${info['free_margin']:.2f}\n\n"
        f"Daily DD: {daily_pct:.1f}% / {MAX_DAILY_DRAWDOWN_PERCENT}%\n"
        f"Total DD: {total_pct:.1f}% / {MAX_TOTAL_DRAWDOWN_PERCENT}%\n\n"
        f"Positions:\n{pos_text}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def buy_fibo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 not connected. Use /connect first.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Use: /buyfibo GOLD 0.02")
        return

    symbol = context.args[0].upper()
    try:
        volume = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid volume.")
        return

    normalized = mt5_client.normalize_symbol(symbol)
    market = mt5_client.market_price(normalized)
    if not market:
        await update.message.reply_text(f"❌ {normalized} not available in MT5.")
        return

    account = mt5_client.account_info()
    ok, message = validate_trade_dimensions(account, len(mt5_client.positions()), volume, 60, 120)
    if not ok:
        await update.message.reply_text(f"❌ {message}")
        return

    entry = market["ask"]
    levels = fib_partial_levels(entry, "BUY")
    v1, v2, v3 = partial_close_split(volume)

    try:
        result = mt5_client.buy(normalized, volume, sl=levels["SL"], tp=levels["TP1"], comment="FIBO BUY MAIN")
        if result is None or result.retcode not in (0, 10009, 10008):
            await update.message.reply_text(f"❌ Main order failed: {result.comment if result else 'Unknown'}")
            return

        # Partial closes
        mt5_client.sell(normalized, v1, tp=levels["TP1"], comment="FIBO TP1")
        mt5_client.sell(normalized, v2, tp=levels["TP2"], comment="FIBO TP2")
        mt5_client.sell(normalized, v3, tp=levels["TP3"], comment="FIBO TP3")

        text = (
            f"✅ *BUY FIBO* opened for {normalized}\n\n"
            f"Entry: {entry:.5f}\n"
            f"TP1: {levels['TP1']:.5f} | Vol: {v1}\n"
            f"TP2: {levels['TP2']:.5f} | Vol: {v2}\n"
            f"TP3: {levels['TP3']:.5f} | Vol: {v3}\n"
            f"SL: {levels['SL']:.5f}\n\n"
            f"Total Vol: {volume}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def sell_fibo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 not connected. Use /connect first.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Use: /sellfibo USDJPY 0.10")
        return

    symbol = context.args[0].upper()
    try:
        volume = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid volume.")
        return

    normalized = mt5_client.normalize_symbol(symbol)
    market = mt5_client.market_price(normalized)
    if not market:
        await update.message.reply_text(f"❌ {normalized} not available in MT5.")
        return

    account = mt5_client.account_info()
    ok, message = validate_trade_dimensions(account, len(mt5_client.positions()), volume, 60, 120)
    if not ok:
        await update.message.reply_text(f"❌ {message}")
        return

    entry = market["bid"]
    levels = fib_partial_levels(entry, "SELL")
    v1, v2, v3 = partial_close_split(volume)

    try:
        result = mt5_client.sell(normalized, volume, sl=levels["SL"], tp=levels["TP1"], comment="FIBO SELL MAIN")
        if result is None or result.retcode not in (0, 10009, 10008):
            await update.message.reply_text(f"❌ Main order failed: {result.comment if result else 'Unknown'}")
            return

        # Partial closes
        mt5_client.buy(normalized, v1, tp=levels["TP1"], comment="FIBO TP1")
        mt5_client.buy(normalized, v2, tp=levels["TP2"], comment="FIBO TP2")
        mt5_client.buy(normalized, v3, tp=levels["TP3"], comment="FIBO TP3")

        text = (
            f"✅ *SELL FIBO* opened for {normalized}\n\n"
            f"Entry: {entry:.5f}\n"
            f"TP1: {levels['TP1']:.5f} | Vol: {v1}\n"
            f"TP2: {levels['TP2']:.5f} | Vol: {v2}\n"
            f"TP3: {levels['TP3']:.5f} | Vol: {v3}\n"
            f"SL: {levels['SL']:.5f}\n\n"
            f"Total Vol: {volume}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def close_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 not connected.")
        return
    
    closed = mt5_client.close_all_positions()
    if not closed:
        await update.message.reply_text("✅ No positions to close.")
        return
    
    await update.message.reply_text(f"✅ {len(closed)} position(s) closed.")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing. Add it in config.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("connect", connect_mt5))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("buyfibo", buy_fibo))
    app.add_handler(CommandHandler("sellfibo", sell_fibo))
    app.add_handler(CommandHandler("closeall", close_all))

    print("🚀 FIBO FTMO BOT started...")
    app.run_polling()


if __name__ == "__main__":
    main()
