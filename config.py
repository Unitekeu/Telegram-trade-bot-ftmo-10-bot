import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")
DEFAULT_LOT = float(os.getenv("DEFAULT_LOT", "0.05"))
RISK_PERCENT = float(os.getenv("RISK_PERCENT", "1.0"))
