from flask import Flask, request, jsonify
from coindcx import place_order, normalize_symbol

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    signal = data["signal"].lower()
    symbol = normalize_symbol(data["symbol"])
    price = float(data["price"])

    print(f"[WEBHOOK] {signal.upper()} {symbol} @ {price}")

    if signal not in ("buy", "sell"):
        return jsonify({"error": "invalid signal"}), 400

    place_order(signal, symbol, price)

    return jsonify({"status": "order sent"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
