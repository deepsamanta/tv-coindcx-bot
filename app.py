from flask import Flask, request, jsonify
from coindcx import (
    place_bracket,
    close_position,
    get_position_for_symbol
)

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    signal = data["signal"].lower()
    symbol = data["symbol"]
    price = float(data["price"])

    print(f"[WEBHOOK] {signal.upper()} {symbol} @ {price}")

    pos = get_position_for_symbol(symbol)

    if signal == "buy":
        if pos and pos["side"] == "buy":
            print(f"🚫 {symbol}: already BUY")
            return jsonify({"status": "ignored"})

        if pos and pos["side"] == "sell":
            close_position(symbol)

        place_bracket("buy", symbol, price)

    elif signal == "sell":
        if pos and pos["side"] == "sell":
            print(f"🚫 {symbol}: already SELL")
            return jsonify({"status": "ignored"})

        if pos and pos["side"] == "buy":
            close_position(symbol)

        place_bracket("sell", symbol, price)

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
