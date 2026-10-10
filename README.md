# Telegram Trading Bot
# Supported instruments: GOLD, USDJPY, BTCUSD

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import DEFAULT_LOT, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, TELEGRAM_BOT_TOKEN
from mt5_client import MT5Client

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

mt5_client = MT5Client(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)


def format_position_type(position_type):
    values = {
        0: "BUY",
        1: "SELL",
    }
    return values.get(position_type, str(position_type))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥 *MT5 Trading Bot*\n\n"
        "Instrumentet e mbështetura:\n"
        "• GOLD / XAUUSD\n"
        "• USD/JPY / USDJPY\n"
        "• BTC / BTCUSD\n\n"
        "Komandat:\n"
        "/connect\n"
        "/status\n"
        "/buy GOLD 0.05\n"
        "/sell USDJPY 0.10\n"
        "/buy BTC 0.01\n"
        "/closeall\n"
        "/symbols"
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

    if len(context.args) < 2:
        await update.message.reply_text("Përdorim: /buy GOLD 0.05 ose /buy BTC 0.01")
        return

    symbol = context.args[0]
    volume = float(context.args[1])
    normalized = mt5_client.normalize_symbol(symbol)

    try:
        result = mt5_client.buy(normalized, volume, comment="TG BUY")
        if result is None:
            await update.message.reply_text(f"❌ Porosia për {normalized} dështoi.")
            return

        if result.retcode not in (0, 10009, 10008):
            await update.message.reply_text(f"❌ Gabim: {result.comment}")
            return

        price = mt5_client.market_price(normalized)
        await update.message.reply_text(
            f"✅ Buy u hap për {normalized}\nVolume: {volume}\nAsk: {price['ask'] if price else 'N/A'}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gabim: {e}")


async def sell_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mt5_client.connected:
        await update.message.reply_text("❌ MT5 nuk është lidhur. Shtyp /connect")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Përdorim: /sell GOLD 0.05 ose /sell USDJPY 0.10")
        return

    symbol = context.args[0]
    volume = float(context.args[1])
    normalized = mt5_client.normalize_symbol(symbol)

    try:
        result = mt5_client.sell(normalized, volume, comment="TG SELL")
        if result is None:
            await update.message.reply_text(f"❌ Porosia për {normalized} dështoi.")
            return

        if result.retcode not in (0, 10009, 10008):
            await update.message.reply_text(f"❌ Gabim: {result.comment}")
            return

        price = mt5_client.market_price(normalized)
        await update.message.reply_text(
            f"✅ Sell u hap për {normalized}\nVolume: {volume}\nBid: {price['bid'] if price else 'N/A'}"
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

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
