# FTMO-safe Telegram Trading Bot
# Supported instruments: GOLD, USDJPY, BTCUSD

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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
from mt5_client import MT5Client

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

mt5_client = MT5Client(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)


def format_position_type(position_type):
    values = {0: "BUY", 1: "SELL"}
    return values.get(position_type, str(position_type))


def ftmo_trade_guard(account_info, positions, symbol, volume, sl_points, tp_points):
    if not account_info:
        return "MT5 account info not available."

    if len(positions or []) >= MAX_OPEN_TRADES:
        return f"Max open trades reached: {MAX_OPEN_TRADES}. Close one before opening a new trade."

    if sl_points < MIN_STOP_LOSS_POINTS:
        return f"Stop loss too small. Minimum allowed is {MIN_STOP_LOSS_POINTS} points."

    if tp_points <= sl_points:
        return "Take profit must be greater than stop loss."

    balance = account_info["balance"]
    if balance <= 0:
        return "Invalid account balance."

    risk_amount = balance * (RISK_PERCENT / 100.0)
    if volume * 1000 <= 0:
        return "Volume must be greater than zero."

    if account_info["equity"] <= 0:
        return "Account equity invalid."

    if MAX_DAILY_DRAWDOWN_PERCENT > 0:
        daily_loss_limit = balance * (MAX_DAILY_DRAWDOWN_PERCENT / 100.0)
        if account_info["profit"] <= -daily_loss_limit:
            return f"Daily loss limit reached. Max allowed daily drawdown: {MAX_DAILY_DRAWDOWN_PERCENT}%"

    if MAX_TOTAL_DRAWDOWN_PERCENT > 0:
        total_loss_limit = balance * (MAX_TOTAL_DRAWDOWN_PERCENT / 100.0)
        if account_info["profit"] <= -total_loss_limit:
            return f"Total loss limit reached. Max allowed total drawdown: {MAX_TOTAL_DRAWDOWN_PERCENT}%"

    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥 *FTMO SAFE MT5 BOT*\n\n"
        "Instrumentet e mbështetura:\n"
        "• GOLD / XAUUSD\n"
        "• USD/JPY / USDJPY\n"
        "• BTC / BTCUSD\n\n"
        "Komandat:\n"
        "/connect\n"
        "/status\n"
        "/buy GOLD 0.02 60 120\n"
        "/sell USDJPY 0.10 80 160\n"
        "/closeall\n"
        "/symbols\n\n"
        "Rregulla for FTMO:\n"
        "• Max 3 open trades\n"
        f"• Max risk per trade: {RISK_PERCENT}%\n"
        f"• Min SL: {MIN_STOP_LOSS_POINTS} points\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def connect_mt5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mt5_client.connect()
        await update.message.reply_text("✅ Lidhja me MT5 u realizua me sukses.")
    except Exception as e:
        await update.message.reply_text(f"❌ Gabim gjatë lidhjes me MT5: {e}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 nuk është lidhur. Shtyp /connect")
        return

    info = mt5_client.account_info()
    if not info:
        await update.message.reply_text("❌ Nuk mund të lexoj të dhënat e llogarisë.")
        return

    positions = mt5_client.positions()
    text_positions = "Nuk ka pozicione aktive."
    if positions:
        lines = []
        for pos in positions:
            lines.append(
                f"- {pos.symbol} | {format_position_type(pos.type)} | Volume: {pos.volume} | Profit: {pos.profit}"
            )
        text_positions = "\n".join(lines)

    text = (
        "📊 *Statusi i llogarisë*\n\n"
        f"Balance: {info['balance']}\n"
        f"Equity: {info['equity']}\n"
        f"Margin: {info['margin']}\n"
        f"Free Margin: {info['free_margin']}\n"
        f"Profit: {info['profit']}\n"
        f"Currency: {info['currency']}\n\n"
        f"Pozicionet:\n{text_positions}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def buy_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 nuk është lidhur. Shtyp /connect")
        return

    if len(context.args) < 4:
        await update.message.reply_text("Përdorim: /buy GOLD 0.02 60 120")
        return

    symbol = context.args[0]
    volume = float(context.args[1])
    sl_points = int(context.args[2])
    tp_points = int(context.args[3])
    normalized = mt5_client.normalize_symbol(symbol)

    info = mt5_client.account_info()
    positions = mt5_client.positions()
    guard_error = ftmo_trade_guard(info, positions, normalized, volume, sl_points, tp_points)
    if guard_error:
        await update.message.reply_text(f"❌ {guard_error}")
        return

    try:
        market = mt5_client.market_price(normalized)
        if not market:
            await update.message.reply_text(f"❌ Symboli {normalized} nuk është i disponueshëm.")
            return

        sl_value = market["ask"] - (sl_points * 0.01)
        tp_value = market["ask"] + (tp_points * 0.01)
        result = mt5_client.buy(normalized, volume, sl=sl_value, tp=tp_value, comment="TG BUY")

        if result is None:
            await update.message.reply_text(f"❌ Porosia për {normalized} dështoi.")
            return

        if result.retcode not in (0, 10009, 10008):
            await update.message.reply_text(f"❌ Gabim: {result.comment}")
            return

        await update.message.reply_text(
            f"✅ Buy u hap për {normalized}\nVolume: {volume}\nSL: {sl_value}\nTP: {tp_value}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gabim: {e}")


async def sell_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 nuk është lidhur. Shtyp /connect")
        return

    if len(context.args) < 4:
        await update.message.reply_text("Përdorim: /sell USDJPY 0.10 80 160")
        return

    symbol = context.args[0]
    volume = float(context.args[1])
    sl_points = int(context.args[2])
    tp_points = int(context.args[3])
    normalized = mt5_client.normalize_symbol(symbol)

    info = mt5_client.account_info()
    positions = mt5_client.positions()
    guard_error = ftmo_trade_guard(info, positions, normalized, volume, sl_points, tp_points)
    if guard_error:
        await update.message.reply_text(f"❌ {guard_error}")
        return

    try:
        market = mt5_client.market_price(normalized)
        if not market:
            await update.message.reply_text(f"❌ Symboli {normalized} nuk është i disponueshëm.")
            return

        sl_value = market["bid"] + (sl_points * 0.01)
        tp_value = market["bid"] - (tp_points * 0.01)
        result = mt5_client.sell(normalized, volume, sl=sl_value, tp=tp_value, comment="TG SELL")

        if result is None:
            await update.message.reply_text(f"❌ Porosia për {normalized} dështoi.")
            return

        if result.retcode not in (0, 10009, 10008):
            await update.message.reply_text(f"❌ Gabim: {result.comment}")
            return

        await update.message.reply_text(
            f"✅ Sell u hap për {normalized}\nVolume: {volume}\nSL: {sl_value}\nTP: {tp_value}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gabim: {e}")


async def close_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 nuk është lidhur. Shtyp /connect")
        return

    try:
        result = mt5_client.close_all_positions()
        await update.message.reply_text(f"✅ Të gjitha pozicionet u mbyllën.\n{result}")
    except Exception as e:
        await update.message.reply_text(f"❌ Gabim: {e}")


async def symbols(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 nuk është lidhur. Shtyp /connect")
        return

    supported = ["XAUUSD", "USDJPY", "BTCUSD"]
    text = "📌 Instrumentet e mbështetura:\n" + "\n".join(f"- {s}" for s in supported)
    await update.message.reply_text(text)


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing. Add it in .env")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("connect", connect_mt5))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("buy", buy_order))
    app.add_handler(CommandHandler("sell", sell_order))
    app.add_handler(CommandHandler("closeall", close_all))
    app.add_handler(CommandHandler("symbols", symbols))

    print("FTMO-safe trading bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
