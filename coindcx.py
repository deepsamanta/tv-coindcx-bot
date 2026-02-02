import time, hmac, hashlib, json, requests
from decimal import Decimal, ROUND_DOWN
from config import COINDCX_KEY, COINDCX_SECRET, CAPITAL_USDT, LEVERAGE, TEST_MODE

BASE_URL = "https://api.coindcx.com"

# FIXED STEP SIZE MAP (YOU CHOSE THIS)
SYMBOL_STEPS = {
    "BTCUSDT": Decimal("0.001"),
    "ETHUSDT": Decimal("0.001"),
    "BNBUSDT": Decimal("0.01"),
    "SOLUSDT": Decimal("0.01"),
    "XRPUSDT": Decimal("0.1"),
    "DOGEUSDT": Decimal("1"),
}


# ---------- HELPERS ---------- #

def normalize_symbol(symbol: str) -> str:
    symbol = symbol.upper()
    if "USDT" in symbol:
        return symbol.split("USDT")[0] + "USDT"
    return symbol


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


def compute_qty(entry_price, symbol):
    symbol = normalize_symbol(symbol)
    step = SYMBOL_STEPS.get(symbol, Decimal("0.001"))

    exposure = Decimal(str(CAPITAL_USDT)) * Decimal(str(LEVERAGE))
    raw_qty = exposure / Decimal(str(entry_price))

    qty = (raw_qty // step) * step
    if qty <= 0:
        qty = step

    return float(qty)


# ---------- PLACE ORDER ---------- #

def place_order(side, symbol, entry):
    symbol = normalize_symbol(symbol)
    qty = compute_qty(entry, symbol)

    entry = Decimal(str(entry))

    tp = entry * (Decimal("1.04") if side == "buy" else Decimal("0.96"))
    sl = entry * (Decimal("0.95") if side == "buy" else Decimal("1.05"))

    body = {
        "timestamp": int(time.time() * 1000),
        "order": {
            "side": side,
            "pair": fut_pair(symbol),
            "order_type": "market_order",
            "total_quantity": qty,
            "leverage": LEVERAGE,
            "take_profit_price": float(tp),
            "stop_loss_price": float(sl)
        }
    }

    if TEST_MODE:
        print("[TEST_MODE] ORDER:", body)
        return

    payload, headers = sign(body)

    r = requests.post(
        f"{BASE_URL}/exchange/v1/derivatives/futures/orders/create",
        data=payload,
        headers=headers
    )

    print("[COINDCX]", r.status_code, r.text)
