import time
import hmac
import hashlib
import json
import requests
from decimal import Decimal, getcontext
from config import COINDCX_KEY, COINDCX_SECRET, CAPITAL_USDT, LEVERAGE, TEST_MODE

# High precision for Decimal math
getcontext().prec = 28

BASE_URL = "https://api.coindcx.com"

# ===================== QUANTITY STEP PER SYMBOL =====================

SYMBOL_STEPS = {
    "BTCUSDT": Decimal("0.001"),
    "ETHUSDT": Decimal("0.001"),
    "BNBUSDT": Decimal("0.01"),
    "SOLUSDT": Decimal("0.01"),
    "XRPUSDT": Decimal("0.1"),
    "DOGEUSDT": Decimal("1"),
}

# ===================== PRICE TICK (TP / SL) PER SYMBOL =====================

PRICE_TICKS = {
    "BTCUSDT": Decimal("0.1"),
    "ETHUSDT": Decimal("0.01"),
    "BNBUSDT": Decimal("0.01"),
    "SOLUSDT": Decimal("0.01"),
    "XRPUSDT": Decimal("0.01"),
    "DOGEUSDT": Decimal("0.0001"),
}

# ===================== SPECIAL RULES =====================

SPECIAL_RULES = {
    "BTCUSDT": {
        "capital": Decimal("13"),
        "leverage": 20
    }
}

# ===================== HELPERS =====================

def normalize_symbol(symbol: str) -> str:
    """
    Converts symbols like BTCUSDT.P, BTCUSDT_1 → BTCUSDT
    """
    symbol = symbol.upper()
    if "USDT" in symbol:
        return symbol.split("USDT")[0] + "USDT"
    return symbol


def fut_pair(symbol: str) -> str:
    """
    BTCUSDT → B-BTC_USDT (CoinDCX futures format)
    """
    return f"B-{symbol.replace('USDT', '')}_USDT"


def sign(body: dict):
    payload = json.dumps(body, separators=(",", ":"))
    signature = hmac.new(
        COINDCX_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": COINDCX_KEY,
        "X-AUTH-SIGNATURE": signature
    }
    return payload, headers

# ===================== CORE LOGIC =====================

def compute_qty(entry_price: float, symbol: str) -> float:
    symbol = normalize_symbol(symbol)

    step = SYMBOL_STEPS.get(symbol)
    if step is None:
        raise ValueError(f"No quantity step defined for {symbol}")

    # Apply BTC override if present
    if symbol in SPECIAL_RULES:
        capital = SPECIAL_RULES[symbol]["capital"]
        leverage = Decimal(str(SPECIAL_RULES[symbol]["leverage"]))
    else:
        capital = Decimal(str(CAPITAL_USDT))
        leverage = Decimal(str(LEVERAGE))

    exposure = capital * leverage
    raw_qty = exposure / Decimal(str(entry_price))

    # Force divisibility by step
    qty = raw_qty - (raw_qty % step)
    if qty <= 0:
        qty = step

    return float(qty)


def place_order(side: str, symbol: str, entry_price: float):
    try:
        symbol = normalize_symbol(symbol)

        qty = compute_qty(entry_price, symbol)

        # Leverage selection
        leverage = SPECIAL_RULES.get(symbol, {}).get("leverage", LEVERAGE)

        entry = Decimal(str(entry_price))

        # TP / SL calculation
        if side == "buy":
            tp = entry * Decimal("1.04")
            sl = entry * Decimal("0.95")
        else:
            tp = entry * Decimal("0.96")
            sl = entry * Decimal("1.05")

        # Apply price tick precision (CRITICAL FIX)
        price_tick = PRICE_TICKS.get(symbol, Decimal("0.01"))

        tp = (tp // price_tick) * price_tick
        sl = (sl // price_tick) * price_tick

        body = {
            "timestamp": int(time.time() * 1000),
            "order": {
                "side": side,
                "pair": fut_pair(symbol),
                "order_type": "market_order",
                "total_quantity": qty,
                "leverage": leverage,
                "take_profit_price": float(tp),
                "stop_loss_price": float(sl)
            }
        }

        print("[ORDER PAYLOAD]", body, flush=True)

        if TEST_MODE:
            print("[TEST_MODE] Order not sent", flush=True)
            return

        payload, headers = sign(body)
        response = requests.post(
            f"{BASE_URL}/exchange/v1/derivatives/futures/orders/create",
            data=payload,
            headers=headers,
            timeout=10
        )

        print("[COINDCX]", response.status_code, response.text, flush=True)

    except Exception as e:
        print("❌ ORDER ERROR:", str(e), flush=True)
