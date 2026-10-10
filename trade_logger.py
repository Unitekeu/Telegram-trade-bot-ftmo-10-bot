import json
import logging
import os
from datetime import datetime

from config import LOG_PATH


class TradeLogger:
    def __init__(self, log_dir=LOG_PATH):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.trade_log = os.path.join(self.log_dir, "trades.jsonl")
        self.signal_log = os.path.join(self.log_dir, "signals.jsonl")

    def log_trade(self, payload):
        try:
            with open(self.trade_log, "a", encoding="utf-8") as f:
                f.write(json.dumps({"timestamp": datetime.utcnow().isoformat(), **payload}) + "\n")
            return True
        except Exception as exc:
            logging.exception("Trade log failed: %s", exc)
            return False

    def log_signal(self, payload):
        try:
            with open(self.signal_log, "a", encoding="utf-8") as f:
                f.write(json.dumps({"timestamp": datetime.utcnow().isoformat(), **payload}) + "\n")
            return True
        except Exception as exc:
            logging.exception("Signal log failed: %s", exc)
            return False
