import MetaTrader5 as mt5


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

    def disconnect(self):
        if self.connected:
            mt5.shutdown()
            self.connected = False

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

    def buy(self, symbol, volume, sl=None, tp=None, comment="TG BUY"):
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

    def sell(self, symbol, volume, sl=None, tp=None, comment="TG SELL"):
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

    def close_position_by_ticket(self, ticket):
        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            return None

        position = pos[0]
        symbol = position.symbol
        type_order = position.type
        volume = position.volume
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

        return mt5.order_send(request)

    def close_all_positions(self):
        if not self.connected:
            return []

        positions = mt5.positions_get()
        closed = []
        for pos in positions or []:
            result = self.close_position_by_ticket(pos.ticket)
            closed.append({"ticket": pos.ticket, "symbol": pos.symbol, "result": result})
        return closed
