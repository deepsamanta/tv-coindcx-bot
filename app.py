from flask import Flask, request, jsonify
from coindcx import place_order, normalize_symbol

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # 1️⃣ Log raw body (CRITICAL for debugging)
        raw_data = request.data.decode("utf-8")
        print("[RAW WEBHOOK BODY]", raw_data, flush=True)

        # 2️⃣ Parse JSON safely
        data = request.get_json(silent=True)
        if not data:
            print("⚠️ Empty or invalid JSON received", flush=True)
            return jsonify({"status": "ignored", "reason": "invalid json"}), 200

        # 3️⃣ Validate required fields
        if "signal" not in data or "symbol" not in data or "price" not in data:
            print("⚠️ Missing required fields:", data, flush=True)
            return jsonify({"status": "ignored", "reason": "missing fields"}), 200

        signal = str(data["signal"]).lower()
        symbol = normalize_symbol(str(data["symbol"]))
        price = float(data["price"])

        print(f"[WEBHOOK PARSED] {signal.upper()} {symbol} @ {price}", flush=True)

        # 4️⃣ Validate signal
        if signal not in ("buy", "sell"):
            print("⚠️ Invalid signal:", signal, flush=True)
            return jsonify({"status": "ignored", "reason": "invalid signal"}), 200

        # 5️⃣ Place order (stateless)
        place_order(signal, symbol, price)

        return jsonify({"status": "order sent"}), 200

    except Exception as e:
        # NEVER crash TradingView webhook
        print("❌ WEBHOOK ERROR:", str(e), flush=True)
        return jsonify({"status": "error", "message": str(e)}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
