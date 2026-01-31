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

# ===== COINDCX FUTURES SETTINGS =====
STEP = 0.001        # Required precision
MIN_STEP_UNITS = 1 # Never allow zero qty


def compute_qty(entry_price: float) -> float:
    """
    Compute quantity using integer step units ONLY
    Ensures qty is always divisible by STEP
    """
    exposure = CAPITAL_USDT * LEVERAGE
    raw_qty = exposure / entry_price

    # Convert to integer step units FIRST
    step_units = int(raw_qty / STEP)

    if step_units < MIN_STEP_UNITS:
        print(
            f"[WARN] Qty too small ({raw_qty:.8f}), forcing minimum qty {STEP}",
            flush=True
        )
        step_units = MIN_STEP_UNITS

    qty = step_units * STEP

    # Final safety rounding (eliminates float garbage)
    return round(qty, 3)


def fut_pair(symbol: str) -> str:
    """
    TradingView: ETHUSDT
    CoinDCX Futures: B-ETH_USDT
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

    # ===== TP / SL =====
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

    signature = hmac.new(
        COINDCX_SECRET.encode("utf-8"),
        json_body.encode(),
        hashlib.sha256
    ).hexdigest()

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
