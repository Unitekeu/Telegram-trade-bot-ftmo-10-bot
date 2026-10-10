from config import (
    DEFAULT_LOT,
    MAX_DAILY_DRAWDOWN_PERCENT,
    MAX_OPEN_TRADES,
    MAX_TOTAL_DRAWDOWN_PERCENT,
    MIN_STOP_LOSS_POINTS,
    RISK_PERCENT,
)


class FTMORiskController:
    def __init__(self, initial_balance=200000):
        self.initial_balance = initial_balance
        self.daily_loss_limit = initial_balance * (MAX_DAILY_DRAWDOWN_PERCENT / 100.0)
        self.total_loss_limit = initial_balance * (MAX_TOTAL_DRAWDOWN_PERCENT / 100.0)
        self.max_risk_per_trade = initial_balance * (RISK_PERCENT / 100.0)

    def validate_trade(self, account_info, positions_count, volume, sl_points, tp_points):
        if not account_info:
            return False, "Account info unavailable."
        if positions_count >= MAX_OPEN_TRADES:
            return False, f"Max open trades reached ({MAX_OPEN_TRADES})."
        if volume <= 0:
            return False, "Volume must be greater than zero."
        if sl_points < MIN_STOP_LOSS_POINTS:
            return False, f"Stop loss too small. Minimum is {MIN_STOP_LOSS_POINTS} points."
        if tp_points <= sl_points:
            return False, "Take profit must be greater than stop loss."

        balance = account_info.get("balance", 0)
        profit = account_info.get("profit", 0)
        if balance <= 0:
            return False, "Invalid balance."
        if profit <= -self.daily_loss_limit:
            return False, f"Daily loss limit reached. Max daily drawdown: {MAX_DAILY_DRAWDOWN_PERCENT}%"
        if profit <= -self.total_loss_limit:
            return False, f"Total loss limit reached. Max total drawdown: {MAX_TOTAL_DRAWDOWN_PERCENT}%"

        # risk sanity check
        estimated_risk = volume * sl_points * 0.01
        if estimated_risk > self.max_risk_per_trade:
            return False, f"Risk exceeded. Max allowed risk: ${self.max_risk_per_trade:.2f}"

        return True, "Validation OK."

    def format_status(self, account_info):
        if not account_info:
            return "❌ No account info available."
        balance = account_info["balance"]
        equity = account_info["equity"]
        profit = account_info["profit"]
        margin = account_info["margin"]
        free_margin = account_info["free_margin"]
        daily_used = min((abs(profit) / self.daily_loss_limit) * 100 if profit < 0 else 0, 100)
        total_used = min((abs(profit) / self.total_loss_limit) * 100 if profit < 0 else 0, 100)
        status = "🟢 SAFE" if daily_used < 80 else "🟡 WARNING" if daily_used < 100 else "🔴 DANGER"
        return (
            f"{status} *FTMO ACCOUNT STATUS*\n\n"
            f"Balance: ${balance:.2f}\n"
            f"Equity: ${equity:.2f}\n"
            f"Profit: ${profit:.2f}\n"
            f"Margin: ${margin:.2f}\n"
            f"Free Margin: ${free_margin:.2f}\n\n"
            f"Daily Drawdown: {daily_used:.1f}% / {MAX_DAILY_DRAWDOWN_PERCENT}%\n"
            f"Total Drawdown: {total_used:.1f}% / {MAX_TOTAL_DRAWDOWN_PERCENT}%"
        )
