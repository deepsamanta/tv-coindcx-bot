import time
import json
import hmac
import hashlib
import requests
import math

from config import (
    COINDCX_KEY,
    COINDCX_SECRET,
    CAPITAL_USDT,
    LEVERAGE,
    TEST_MODE,
    TP_PERCENT,
    SL_PERCENT
)

# ===== COINDCX FUTURES QTY SETTINGS =====
STEP = 0.001        # CoinDCX futures precision
MIN_QTY = STEP     # never allow 0 qty


def apply_precision(qty, step=STEP):
    """
    Floor qty to allowed precision
    """
    qty = round(qty, 6)
    return math.floor(qty / step) * step


def compute_qty(entry_price: float):
    """
    Compute quantity using fixed capital + leverage
    NEVER returns zero
    """
    exposure = CAPITAL_USDT * LEVERAGE
    raw_qty = exposure / entry_price

    # Large quantity → integer only
    if raw_qty > 50:
        return int(raw_qty)

    qty = apply_precision(raw_qty)

    # 🔑 CRITICAL FIX: never return 0
    if qty < MIN_QTY:
        print(
            f"[WARN] Qty too small ({raw_qty:.6f}), forcing minimum qty {MIN_QTY}",
            flush=True
        )
        return MIN_QTY

    return qty


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
    """
    Place CoinDCX futures order with TP & SL
    TP = +4%
    SL = -5%
    """
    timestamp = int(time.time() * 1000)
    entry = float(entry)

    qty = compute_qty(entry)

    # === TP / SL CALCULATION ===
    if side == "buy":
        tp = entry * (1 + TP_PERCENT)
        sl = entry * (1 - SL_PERCENT)
    else:  # sell
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
        print("[TEST_MODE] Payload:", body, flush=True)
        return {"status": "TEST_MODE"}

    json_body = json.dumps(body, separators=(",", ":"))
    secret_bytes = COINDCX_SECRET.encode('utf-8')

    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": COINDCX_KEY,
        "X-AUTH-SIGNATURE": signature
    }

    url = "https://api.coindcx.com/exchange/v1/derivatives/futures/orders/create"

    try:
        r = requests.post(url, data=json_body, headers=headers, timeout=10)
        print("[COINDCX]", r.status_code, r.text, flush=True)
        return r.json() if r.text else None
    except Exception as e:
        print("❌ COINDCX API ERROR:", str(e), flush=True)
        raise
