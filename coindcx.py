import time, hmac, hashlib, json, requests
from decimal import Decimal, getcontext
from config import COINDCX_KEY, COINDCX_SECRET, CAPITAL_USDT, LEVERAGE, TEST_MODE

getcontext().prec = 28
BASE_URL = "https://api.coindcx.com"

# FIXED STEP SIZE MAP
SYMBOL_STEPS = {
    "BTCUSDT": Decimal("0.001"),
    "ETHUSDT": Decimal("0.001"),
    "BNBUSDT": Decimal("0.01"),
    "SOLUSDT": Decimal("0.01"),
    "XRPUSDT": Decimal("0.1"),
    "DOGEUSDT": Decimal("1"),
}


def normalize_symbol(symbol: str) -> str:
    symbol = symbol.upper()
    if "USDT" in symbol:
        return symbol.split("USDT")[0] + "USDT"
    return symbol


def fut_pair(symbol):
    return f"B-{symbol.replace('USDT', '')}_USDT"


def sign(body):
    payload = json.dumps(body, separators=(",", ":"))
    sig = hmac.new(
        COINDCX_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return payload, {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": COINDCX_KEY,
        "X-AUTH-SIGNATURE": sig
    }


# 🔒 THIS IS THE KEY FIX
def compute_qty(entry_price, symbol):
    symbol = normalize_symbol(symbol)
    step = SYMBOL_STEPS.get(symbol)

    if step is None:
        raise ValueError(f"Step size missing for {symbol}")

    exposure = Decimal(str(CAPITAL_USDT)) * Decimal(str(LEVERAGE))
    raw_qty = exposure / Decimal(str(entry_price))

    # EXACT divisibility enforcement
    qty = raw_qty - (raw_qty % step)

    if qty <= 0:
        qty = step

    # Final safety check
    if qty % step != 0:
        raise ValueError(f"Invalid qty {qty} for step {step}")

    return float(qty)


def place_order(side, symbol, entry):
    try:
        symbol = normalize_symbol(symbol)
        qty = compute_qty(entry, symbol)

        entry_d = Decimal(str(entry))
        tp = entry_d * (Decimal("1.04") if side == "buy" else Decimal("0.96"))
        sl = entry_d * (Decimal("0.95") if side == "buy" else Decimal("1.05"))

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

        print("[ORDER PAYLOAD]", body, flush=True)

        if TEST_MODE:
            print("[TEST_MODE] Skipped API call", flush=True)
            return

        payload, headers = sign(body)
        r = requests.post(
            f"{BASE_URL}/exchange/v1/derivatives/futures/orders/create",
            data=payload,
            headers=headers,
            timeout=10
        )

        print("[COINDCX]", r.status_code, r.text, flush=True)

    except Exception as e:
        print("❌ ORDER ERROR:", str(e), flush=True)
