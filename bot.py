from config import DEFAULT_LOT, RISK_PERCENT


def calculate_risk_lot(balance):
    if balance <= 0:
        return DEFAULT_LOT

    risk_amount = (balance * RISK_PERCENT) / 100
    return max(DEFAULT_LOT, round(risk_amount / 100, 2))
