import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")
DEFAULT_LOT = float(os.getenv("DEFAULT_LOT", "0.02"))
RISK_PERCENT = float(os.getenv("RISK_PERCENT", "0.5"))

MAX_OPEN_TRADES = int(os.getenv("MAX_OPEN_TRADES", "3"))
MAX_DAILY_DRAWDOWN_PERCENT = float(os.getenv("MAX_DAILY_DRAWDOWN_PERCENT", "5.0"))
MAX_TOTAL_DRAWDOWN_PERCENT = float(os.getenv("MAX_TOTAL_DRAWDOWN_PERCENT", "4.0"))
MIN_STOP_LOSS_POINTS = int(os.getenv("MIN_STOP_LOSS_POINTS", "50"))
