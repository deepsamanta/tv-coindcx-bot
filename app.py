from flask import Flask, request, jsonify
from coindcx import place_order, normalize_symbol

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)

        signal = data["signal"].lower()
        symbol = normalize_symbol(data["symbol"])
        price = float(data["price"])

        print("[WEBHOOK RECEIVED]", data, flush=True)

        place_order(signal, symbol, price)

        return jsonify({"status": "sent"})

    except Exception as e:
        print("❌ WEBHOOK ERROR:", str(e), flush=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
