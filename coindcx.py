import time, hmac, hashlib, json, requests, math
from config import COINDCX_KEY, COINDCX_SECRET, CAPITAL_USDT, LEVERAGE, TEST_MODE

BASE_URL = "https://api.coindcx.com"

# ✅ FIXED STEP SIZE PER SYMBOL
SYMBOL_STEPS = {
    "BTCUSDT": 0.001,
    "ETHUSDT": 0.001,
    "BNBUSDT": 0.01,
    "SOLUSDT": 0.01,
    "XRPUSDT": 0.1,
    "DOGEUSDT": 1,
}


# ---------- HELPERS ---------- #

def fut_pair(symbol):
    base = symbol.replace("USDT", "")
    return f"B-{base}_USDT"


def sign(body):
    payload = json.dumps(body, separators=(",", ":"))
    signature = hmac.new(
        COINDCX_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": COINDCX_KEY,
        "X-AUTH-SIGNATURE": signature
    }
    return payload, headers


def apply_precision(qty, symbol):
    step = SYMBOL_STEPS.get(symbol, 0.001)
    qty = math.floor(qty / step) * step
    return max(step, round(qty, 6))


def compute_qty(entry_price, symbol):
    exposure = CAPITAL_USDT * LEVERAGE
    raw_qty = exposure / entry_price
    return apply_precision(raw_qty, symbol)


# ---------- POSITION HANDLING ---------- #

def get_all_positions():
    body = {"timestamp": int(time.time() * 1000)}
    payload, headers = sign(body)

    r = requests.post(
        f"{BASE_URL}/exchange/v1/derivatives/futures/positions",
        data=payload,
        headers=headers
    )
    return r.json() if r.status_code == 200 else []


def get_position_for_symbol(symbol):
    pair = fut_pair(symbol)
    for p in get_all_positions():
        if p.get("pair") == pair and abs(float(p.get("size", 0))) > 0:
            return p
    return None


def close_position(symbol):
    pos = get_position_for_symbol(symbol)
    if not pos:
        return

    side = "sell" if pos["side"] == "buy" else "buy"

    body = {
        "timestamp": int(time.time() * 1000),
        "order": {
            "side": side,
            "pair": pos["pair"],
            "order_type": "market_order",
            "total_quantity": abs(float(pos["size"])),
            "leverage": LEVERAGE
        }
    }

    payload, headers = sign(body)

    if TEST_MODE:
        print("[TEST_MODE] CLOSE:", body)
        return

    r = requests.post(
        f"{BASE_URL}/exchange/v1/derivatives/futures/orders/create",
        data=payload,
        headers=headers
    )
    print("[COINDCX CLOSE]", r.status_code, r.text)


# ---------- OPEN POSITION ---------- #

def place_bracket(side, symbol, entry):
    qty = compute_qty(entry, symbol)

    tp = entry * (1.04 if side == "buy" else 0.96)
    sl = entry * (0.95 if side == "buy" else 1.05)

    body = {
        "timestamp": int(time.time() * 1000),
        "order": {
            "side": side,
            "pair": fut_pair(symbol),
            "order_type": "market_order",
            "total_quantity": qty,
            "leverage": LEVERAGE,
            "take_profit_price": round(tp, 2),
            "stop_loss_price": round(sl, 2)
        }
    }

    if TEST_MODE:
        print("[TEST_MODE] OPEN:", body)
        return

    payload, headers = sign(body)

    r = requests.post(
        f"{BASE_URL}/exchange/v1/derivatives/futures/orders/create",
        data=payload,
        headers=headers
    )
    print("[COINDCX OPEN]", r.status_code, r.text)
