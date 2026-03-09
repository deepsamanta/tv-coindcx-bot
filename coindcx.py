import time
import hmac
import hashlib
import json
import requests
from decimal import Decimal, getcontext
from config import COINDCX_KEY, COINDCX_SECRET, CAPITAL_USDT, LEVERAGE, TEST_MODE

getcontext().prec = 28
BASE_URL = "https://api.coindcx.com"


# ===================== PRICE TICK (TP / SL) =====================

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

def normalize_symbol(symbol: str):
    symbol = symbol.upper()
    if "USDT" in symbol:
        return symbol.split("USDT")[0] + "USDT"
    return symbol


def fut_pair(symbol: str):
    return f"B-{symbol.replace('USDT','')}_USDT"


# ===================== GET QUANTITY STEP FROM API =====================

def get_quantity_step(symbol: str):

    pair = fut_pair(symbol)

    url = f"https://api.coindcx.com/exchange/v1/derivatives/futures/data/instrument?pair={pair}&margin_currency_short_name=USDT"

    response = requests.get(url)
    data = response.json()

    instrument = data["instrument"]

    quantity_increment = Decimal(str(instrument["quantity_increment"]))

    min_quantity = Decimal(str(instrument["min_quantity"]))

    step = max(quantity_increment, min_quantity)

    # ===== DEBUG LOG =====
    print(f"[MARKET DEBUG] SYMBOL={symbol}", flush=True)
    print(f"[MARKET DEBUG] PAIR={pair}", flush=True)
    print(f"[MARKET DEBUG] QUANTITY_INCREMENT={quantity_increment}", flush=True)
    print(f"[MARKET DEBUG] MIN_QUANTITY={min_quantity}", flush=True)
    print(f"[MARKET DEBUG] STEP_SELECTED={step}", flush=True)

    return step


# ===================== SIGN REQUEST =====================

def sign_request(body: dict):

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


# ===================== POSITION HANDLING =====================

def get_open_positions():

    body = {
        "timestamp": int(time.time() * 1000),
        "page": "1",
        "size": "50",
        "margin_currency_short_name": ["USDT"]
    }

    payload, headers = sign_request(body)

    url = BASE_URL + "/exchange/v1/derivatives/futures/positions"

    response = requests.post(url, data=payload, headers=headers)

    response.raise_for_status()

    positions = response.json()

    return [
        pos for pos in positions
        if float(pos.get("active_pos", 0)) != 0
    ]


def exit_position(position_id):

    body = {
        "timestamp": int(time.time() * 1000),
        "id": position_id
    }

    payload, headers = sign_request(body)

    url = BASE_URL + "/exchange/v1/derivatives/futures/positions/exit"

    response = requests.post(url, data=payload, headers=headers)

    response.raise_for_status()

    print("[POSITION EXITED]", response.json(), flush=True)

    return response.json()


def exit_if_position_exists(symbol):

    symbol = normalize_symbol(symbol)

    pair = fut_pair(symbol)

    positions = get_open_positions()

    for pos in positions:

        if pos.get("pair") == pair:

            print(f"[INFO] Existing position found for {symbol}, exiting first", flush=True)

            exit_position(pos["id"])

            time.sleep(1)

            break


# ===================== QUANTITY CALCULATION =====================

def compute_qty(entry_price: float, symbol: str):

    symbol = normalize_symbol(symbol)

    step = get_quantity_step(symbol)

    if symbol in SPECIAL_RULES:
        capital = SPECIAL_RULES[symbol]["capital"]
        leverage = Decimal(str(SPECIAL_RULES[symbol]["leverage"]))
    else:
        capital = Decimal(str(CAPITAL_USDT))
        leverage = Decimal(str(LEVERAGE))

    exposure = capital * leverage

    raw_qty = exposure / Decimal(str(entry_price))

    qty = (raw_qty / step).quantize(Decimal("1")) * step

    if qty <= 0:
        qty = step

    qty = qty.quantize(step)

    # ===== DEBUG LOG =====
    print(f"[QTY DEBUG] SYMBOL={symbol}", flush=True)
    print(f"[QTY DEBUG] ENTRY_PRICE={entry_price}", flush=True)
    print(f"[QTY DEBUG] CAPITAL={capital}", flush=True)
    print(f"[QTY DEBUG] LEVERAGE={leverage}", flush=True)
    print(f"[QTY DEBUG] EXPOSURE={exposure}", flush=True)
    print(f"[QTY DEBUG] RAW_QTY={raw_qty}", flush=True)
    print(f"[QTY DEBUG] STEP={step}", flush=True)
    print(f"[QTY DEBUG] FINAL_QTY={qty}", flush=True)

    return float(qty)


# ===================== ORDER LOGIC =====================

def place_order(side: str, symbol: str, entry_price: float):

    try:

        symbol = normalize_symbol(symbol)

        exit_if_position_exists(symbol)

        qty = compute_qty(entry_price, symbol)

        leverage = SPECIAL_RULES.get(symbol, {}).get("leverage", LEVERAGE)

        entry = Decimal(str(entry_price))

        price_tick = PRICE_TICKS.get(symbol, Decimal("0.01"))

        entry = (entry // price_tick) * price_tick

        entry_price = float(entry)

        if side == "buy":
            tp = entry * Decimal("1.04")
            sl = entry * Decimal("0.95")
        else:
            tp = entry * Decimal("0.96")
            sl = entry * Decimal("1.05")

        tp = (tp // price_tick) * price_tick
        sl = (sl // price_tick) * price_tick

        body = {
            "timestamp": int(time.time() * 1000),
            "order": {
                "side": side,
                "pair": fut_pair(symbol),
                "order_type": "limit_order",
                "price": entry_price,
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

        payload, headers = sign_request(body)

        response = requests.post(
            BASE_URL + "/exchange/v1/derivatives/futures/orders/create",
            data=payload,
            headers=headers,
            timeout=10
        )

        print("[COINDCX]", response.status_code, response.text, flush=True)

    except Exception as e:

        print("❌ ORDER ERROR:", str(e), flush=True)