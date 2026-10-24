import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")
# Fraction of equity at risk per automated trade; start with demo testing.
RISK_PERCENT = float(os.getenv("RISK_PERCENT", "0.25"))
MAX_OPEN_TRADES = int(os.getenv("MAX_OPEN_TRADES", "3"))
MAX_DAILY_DRAWDOWN_PERCENT = float(os.getenv("MAX_DAILY_DRAWDOWN_PERCENT", "5.0"))
MAX_TOTAL_DRAWDOWN_PERCENT = float(os.getenv("MAX_TOTAL_DRAWDOWN_PERCENT", "4.0"))
# Comma-separated Telegram numeric user IDs. Required for trade/control commands.
_allowed = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").strip()
TELEGRAM_ALLOWED_USER_IDS = {int(value.strip()) for value in _allowed.split(",") if value.strip()}
