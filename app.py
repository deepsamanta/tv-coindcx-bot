from flask import Flask, request
from coindcx import place_bracket

app = Flask(__name__)

CURRENT_POSITION = None  # LONG | SHORT | None


@app.route("/webhook", methods=["POST"])
def webhook():
    global CURRENT_POSITION

    data = request.json
    print("Webhook received:", data)

    signal = data.get("signal")
    symbol = data.get("symbol")
    price = float(data.get("price"))

    if signal == "BUY" and CURRENT_POSITION != "LONG":
        place_bracket("buy", symbol, price)
        CURRENT_POSITION = "LONG"

    elif signal == "SELL" and CURRENT_POSITION != "SHORT":
        place_bracket("sell", symbol, price)
        CURRENT_POSITION = "SHORT"

    elif signal == "EXIT":
        CURRENT_POSITION = None
        print("Exit signal received")

    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
