import logging
import math
from typing import Any, Dict, Optional

import MetaTrader5 as mt5
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import (
    MAX_OPEN_TRADES, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, RISK_PERCENT,
    TELEGRAM_BOT_TOKEN,
)
from strategy import generate_signal, supported_symbols

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
MAGIC = 123456
MAX_SPREAD_ATR_RATIO = 0.15


class MT5Client:
    def __init__(self, login, password, server):
        self.login, self.password, self.server = login, password, server
        self.connected = False

    def normalize_symbol(self, symbol: str) -> str:
        return (symbol or "").strip()

    def connect(self):
        if not self.login or not self.password or not self.server:
            raise RuntimeError("MT5 login/password/server missing. Check .env")
        if not mt5.initialize(login=self.login, password=self.password, server=self.server):
            raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
        self.connected = True
        return True

    def account_info(self):
        info = mt5.account_info() if self.connected else None
        if info is None:
            return None
        return {"login": info.login, "balance": float(info.balance), "equity": float(info.equity),
                "margin": float(info.margin), "free_margin": float(info.margin_free),
                "profit": float(info.profit), "currency": info.currency}

    def market_price(self, symbol):
        if not self.connected or not mt5.symbol_select(symbol, True):
            return None
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        if tick is None or info is None or info.point <= 0:
            return None
        return {"symbol": symbol, "ask": float(tick.ask), "bid": float(tick.bid),
                "spread": float(tick.ask - tick.bid), "point": float(info.point),
                "digits": int(info.digits), "info": info, "tick": tick}

    def positions(self):
        if not self.connected:
            return []
        return list(mt5.positions_get() or [])

    def bot_positions(self):
        return [p for p in self.positions() if p.magic == MAGIC]

    def risk_volume(self, symbol, side, entry, stop, equity=None):
        """Size lots from estimated account-currency loss at SL using broker contract specs."""
        info = mt5.symbol_info(symbol)
        account = mt5.account_info()
        if info is None or account is None:
            raise ValueError("Cannot read symbol/account information.")
        if info.trade_tick_size <= 0 or info.volume_step <= 0:
            raise ValueError("Broker has invalid tick/volume specifications for this symbol.")
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        one_lot_loss = mt5.order_calc_profit(order_type, symbol, 1.0, float(entry), float(stop))
        if one_lot_loss is None or not math.isfinite(one_lot_loss) or one_lot_loss >= 0:
            raise ValueError("Cannot calculate stop-loss risk for this instrument; order blocked.")
        risk_cash = float(equity if equity is not None else account.equity) * (RISK_PERCENT / 100.0)
        raw_volume = risk_cash / abs(one_lot_loss)
        # Round down so rounding cannot increase intended risk.
        steps = math.floor((raw_volume + 1e-12) / info.volume_step)
        volume = steps * info.volume_step
        volume = round(volume, 8)
        if volume < info.volume_min:
            raise ValueError(
                f"Risk-based volume ({volume}) is below broker minimum ({info.volume_min}); "
                "trade blocked rather than exceeding the risk budget."
            )
        volume = min(volume, info.volume_max)
        return volume

    def send_order(self, symbol, side, volume, sl, tp, comment):
        if not self.connected:
            raise RuntimeError("MT5 not connected")
        market = self.market_price(symbol)
        if market is None:
            raise ValueError(f"Symbol {symbol} is unavailable or not selected in MT5.")
        info, tick = market["info"], market["tick"]
        if info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
            raise ValueError(f"Trading is disabled for {symbol}.")
        volume = float(volume)
        step = float(info.volume_step)
        if volume < info.volume_min or volume > info.volume_max or abs(volume / step - round(volume / step)) > 1e-6:
            raise ValueError(f"Volume must match broker limits: min {info.volume_min}, max {info.volume_max}, step {step}.")
        price = market["ask"] if side == "BUY" else market["bid"]
        stop_distance = abs(price - float(sl))
        min_stop = max(int(info.trade_stops_level), 0) * float(info.point)
        if stop_distance < min_stop:
            raise ValueError(f"Stop loss is inside broker's minimum stop distance ({min_stop:g}).")
        if side == "BUY" and not (sl < price < tp):
            raise ValueError("BUY requires SL < entry price < TP.")
        if side == "SELL" and not (tp < price < sl):
            raise ValueError("SELL requires TP < entry price < SL.")
        request_base = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": price, "sl": round(float(sl), info.digits), "tp": round(float(tp), info.digits),
            "deviation": 20, "magic": MAGIC, "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
        }
        # Broker execution modes vary. Try supported filling policies rather than assuming IOC.
        modes = []
        if info.filling_mode & mt5.SYMBOL_FILLING_FOK:
            modes.append(mt5.ORDER_FILLING_FOK)
        if info.filling_mode & mt5.SYMBOL_FILLING_IOC:
            modes.append(mt5.ORDER_FILLING_IOC)
        modes.append(mt5.ORDER_FILLING_RETURN)
        last_result = None
        for mode in dict.fromkeys(modes):
            request = dict(request_base, type_filling=mode)
            last_result = mt5.order_send(request)
            if last_result is not None and last_result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED, mt5.TRADE_RETCODE_DONE_PARTIAL):
                return last_result
            if last_result is None or getattr(last_result, "retcode", None) not in (
                mt5.TRADE_RETCODE_INVALID_FILL, mt5.TRADE_RETCODE_INVALID,
            ):
                break
        return last_result

    def close_bot_positions(self):
        results = []
        for pos in self.bot_positions():
            tick = mt5.symbol_info_tick(pos.symbol)
            info = mt5.symbol_info(pos.symbol)
            if tick is None or info is None:
                results.append({"ticket": pos.ticket, "ok": False, "error": "No quote"})
                continue
            is_buy = pos.type == mt5.POSITION_TYPE_BUY
            request = {
                "action": mt5.TRADE_ACTION_DEAL, "position": pos.ticket,
                "symbol": pos.symbol, "volume": float(pos.volume),
                "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
                "price": float(tick.bid if is_buy else tick.ask), "deviation": 20,
                "magic": MAGIC, "comment": "Bot close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            results.append({"ticket": pos.ticket, "ok": result is not None and result.retcode in
                            (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL),
                            "result": result})
        return results


client = MT5Client(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)


def guard(account, symbol):
    if not account:
        return False, "Account information unavailable."
    if len(client.bot_positions()) >= MAX_OPEN_TRADES:
        return False, f"Bot position limit reached ({MAX_OPEN_TRADES})."
    if not symbol or mt5.symbol_info(symbol) is None:
        return False, f"Symbol {symbol!r} not found. Use its exact broker symbol name."
    return True, "OK"


def build_signal_message(s):
    return (
        f"*MT5 SIGNAL — {s['symbol']}*\n"
        f"Direction: {s['signal']} | Timeframe: {s['timeframe']}\n"
        f"Entry estimate: {s['price']}\nSL: {s['sl']}\nTP: {s['tp']}\n"
        f"ATR: {s['atr']:.6g} | RSI: {s['rsi']:.2f}\n"
        f"Risk target: {RISK_PERCENT:.2f}% equity (volume calculated at confirmation)\n"
        "Broker symbol properties are used; test on demo before live trading."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "MT5 Universal Instruments Bot\n/connect — connect MT5\n/status — account status\n"
        "/scan — scan visible tradable Market Watch symbols\n"
        "/manual BUY SYMBOL 0.01 1.234 1.240 — manual order with explicit SL/TP prices\n"
        "/closeall — close bot-managed positions only"
    )


async def connect_mt5(update, context):
    try:
        client.connect()
        await update.effective_message.reply_text("MT5 connected.")
    except Exception as exc:
        await update.effective_message.reply_text(f"Connection failed: {exc}")


async def status(update, context):
    info = client.account_info()
    if not info:
        await update.effective_message.reply_text("MT5 not connected. Use /connect.")
        return
    positions = client.bot_positions()
    lines = [f"{p.symbol} {'BUY' if p.type == mt5.POSITION_TYPE_BUY else 'SELL'} vol={p.volume} P/L={p.profit:.2f}" for p in positions]
    await update.effective_message.reply_text(
        f"Balance: {info['balance']:.2f} {info['currency']}\nEquity: {info['equity']:.2f}\n"
        f"Floating P/L: {info['profit']:.2f}\nBot positions: {len(positions)}\n" +
        ("\n".join(lines) if lines else "No bot-managed positions.")
    )


async def scan_signals(update, context):
    if not client.connected:
        await update.effective_message.reply_text("MT5 not connected. Use /connect.")
        return
    symbols = supported_symbols()
    if not symbols:
        await update.effective_message.reply_text("No visible tradable symbols found. Enable instruments in MT5 Market Watch.")
        return
    sent = 0
    for symbol in symbols:
        try:
            signal = generate_signal(symbol)
            if not signal:
                continue
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("Confirm", callback_data=f"confirm|{symbol}|{signal['signal']}|{signal['sl']}|{signal['tp']}"),
                InlineKeyboardButton("Reject", callback_data=f"reject|{symbol}")
            ]])
            await update.effective_message.reply_text(build_signal_message(signal), parse_mode="Markdown", reply_markup=keyboard)
            sent += 1
        except Exception:
            logging.exception("Signal generation failed for %s", symbol)
    await update.effective_message.reply_text(f"Scan complete: {len(symbols)} symbols checked, {sent} signals found.")


async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    parts = (query.data or "").split("|")
    if not parts:
        return
    if parts[0] == "reject":
        await query.edit_message_text("Signal rejected.")
        return
    if parts[0] != "confirm" or len(parts) != 5:
        await query.edit_message_text("Invalid signal payload.")
        return
    if not client.connected:
        await query.edit_message_text("MT5 not connected; signal not executed.")
        return
    _, symbol, side, sl_text, tp_text = parts
    try:
        sl, tp = float(sl_text), float(tp_text)
        market = client.market_price(symbol)
        account = client.account_info()
        ok, reason = guard(account, symbol)
        if not ok:
            await query.edit_message_text(f"Trade blocked: {reason}")
            return
        if market is None:
            await query.edit_message_text(f"Trade blocked: no quote for {symbol}.")
            return
        entry = market["ask"] if side == "BUY" else market["bid"]
        info = market["info"]
        spread = market["spread"]
        if spread > MAX_SPREAD_ATR_RATIO * max(abs(entry - sl), info.point):
            await query.edit_message_text("Trade blocked: spread is too large relative to stop distance.")
            return
        volume = client.risk_volume(symbol, side, entry, sl, account["equity"])
        result = client.send_order(symbol, side, volume, sl, tp, "Universal signal")
        if result is None or result.retcode not in (
            mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED, mt5.TRADE_RETCODE_DONE_PARTIAL
        ):
            await query.edit_message_text(f"MT5 rejected order: {getattr(result, 'comment', 'no result')}")
            return
        await query.edit_message_text(
            f"Order sent: {side} {symbol}, volume {volume}. Estimated risk target {RISK_PERCENT:.2f}% equity. "
            "Actual loss may differ due to slippage, gaps, fees and execution."
        )
    except Exception as exc:
        logging.exception("Trade confirmation failed")
        await query.edit_message_text(f"Trade blocked: {exc}")


async def manual_trade(update, context):
    if not client.connected:
        await update.effective_message.reply_text("MT5 not connected. Use /connect.")
        return
    if len(context.args) != 5:
        await update.effective_message.reply_text("Usage: /manual BUY SYMBOL VOLUME SL_PRICE TP_PRICE")
        return
    try:
        side, symbol = context.args[0].upper(), context.args[1]
        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL.")
        volume, sl, tp = float(context.args[2]), float(context.args[3]), float(context.args[4])
        market = client.market_price(symbol)
        account = client.account_info()
        ok, reason = guard(account, symbol)
        if not ok:
            raise ValueError(reason)
        if market is None:
            raise ValueError("No quote for this symbol.")
        entry = market["ask"] if side == "BUY" else market["bid"]
        one_lot_loss = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL,
                                             symbol, volume, entry, sl)
        if one_lot_loss is None or one_lot_loss >= 0:
            raise ValueError("SL is on the wrong side or broker cannot calculate risk.")
        max_risk = account["equity"] * RISK_PERCENT / 100.0
        if abs(one_lot_loss) > max_risk:
            raise ValueError(f"Manual order exceeds {RISK_PERCENT:.2f}% risk cap ({abs(one_lot_loss):.2f} > {max_risk:.2f} {account['currency']}).")
        result = client.send_order(symbol, side, volume, sl, tp, "Manual order")
        if result is None or result.retcode not in (
            mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED, mt5.TRADE_RETCODE_DONE_PARTIAL
        ):
            raise ValueError(f"MT5 rejected order: {getattr(result, 'comment', 'no result')}")
        await update.effective_message.reply_text(f"Order sent: {side} {symbol}, volume {volume}.")
    except Exception as exc:
        await update.effective_message.reply_text(f"Trade blocked: {exc}")


async def close_all(update, context):
    if not client.connected:
        await update.effective_message.reply_text("MT5 not connected.")
        return
    results = client.close_bot_positions()
    ok = sum(1 for item in results if item.get("ok"))
    await update.effective_message.reply_text(
        f"Close requests successful: {ok}/{len(results)}. Only positions with bot magic number {MAGIC} were targeted; check MT5 for final status."
    )


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing. Add it to .env")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("connect", connect_mt5))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("scan", scan_signals))
    app.add_handler(CommandHandler("manual", manual_trade))
    app.add_handler(CommandHandler("closeall", close_all))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logging.info("Universal MT5 signal bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
