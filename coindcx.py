import time
import json
import hmac
import hashlib
import requests
import math

from config import (
    COINDCX_KEY,
    COINDCX_SECRET,
    LEVERAGE,
    CAPITAL_USDT,
    TEST_MODE,
    TP_PERCENT,
    SL_PERCENT
)

# ===== QTY PRECISION =====
STEP = 0.001  # futures precision for majors


def apply_precision(qty, step=STEP):
    qty = round(qty, 6)
    return math.floor(qty / step) * step


def compute_qty(entry_price: float):
    exposure = CAPITAL_USDT * LEVERAGE
    raw_qty = exposure / entry_price

    # Large qty → integer only
    if raw_qty > 50:
        return int(raw_qty)

    return apply_precision(raw_qty)


def fut_pair(symbol: str) -> str:
    """
    TradingView: BTCUSDT
    CoinDCX Futures: B-BTC_USDT
    """
    if not symbol.endswith("USDT"):
        raise ValueError(f"Invalid TradingView symbol: {symbol}")

    base = symbol.replace("USDT", "")
    return f"B-{base}_USDT"


def place_bracket(side: str, symbol: str, entry: float):
    timestamp = int(time.time() * 1000)
    entry = float(entry)

    qty = compute_qty(entry)

    if qty <= 0:
        raise ValueError("Computed quantity is zero")

    # === TP / SL ===
    if side == "buy":
        tp = entry * (1 + TP_PERCENT)
        sl = entry * (1 - SL_PERCENT)
    else:
        tp = entry * (1 - TP_PERCENT)
        sl = entry * (1 + SL_PERCENT)

    body = {
        "timestamp": timestamp,
        "order": {
            "side": side,
            "pair": fut_pair(symbol),
            "order_type": "market_order",
            "price": entry,
            "total_quantity": qty,
            "leverage": LEVERAGE,
            "notification": "email_notification",
            "time_in_force": "good_till_cancel",
            "hidden": False,
            "post_only": False,
            "take_profit_price": round(tp, 2),
            "stop_loss_price": round(sl, 2)
        }
    }

    if TEST_MODE:
        print("[TEST_MODE] Payload:", body)
        return {"status": "TEST_MODE"}

    json_body = json.dumps(body, separators=(",", ":"))
    signature = hmac.new(
        COINDCX_SECRET.encode(),
        json_body.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": COINDCX_KEY,
        "X-AUTH-SIGNATURE": signature
    }

    url = "https://api.coindcx.com/exchange/v1/derivatives/futures/orders/create"

    r = requests.post(url, data=json_body, headers=headers, timeout=10)
    print("[COINDCX]", r.status_code, r.text)

    return r.json() if r.text else None
