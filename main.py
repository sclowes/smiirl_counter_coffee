from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import requests
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(app)

SQUARE_ACCESS_TOKEN = os.environ.get('SQUARE_TOKEN')

TARGET_ITEMS = {
    "Americano",
    "CBD Coffee Americano",
    "CBD Coffee Latte",
    "Cappuccino",
    "Cortado",
    "Espresso",
    "Filter Coffee",
    "Flat White",
    "Latte",
    "Long Black",
    "Macchiato",
    "Mocha",
    "Mushroom Coffee Americano",
    "Mushroom Coffee Latte",
    "Mushroom Mocha",
    "V60",
    "Iced Americano",
    "Iced Latte",
    "Iced Mocha",
}

class Counter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, default=0)

@app.before_first_request
def create_tables():
    db.create_all()
    if not Counter.query.get(1):
        db.session.add(Counter(id=1, value=0))
        db.session.commit()

@app.route("/square-webhook", methods=["POST"])
def square_webhook():
    print("✅ Webhook route triggered")
    event = request.json
    print("Raw webhook payload:\n", json.dumps(event, indent=2))

    if event.get("type") != "payment.created":
        print("❌ Not a payment.created event.")
        return '', 200

    payment = event.get("data", {}).get("object", {}).get("payment", {})
    order_id = payment.get("order_id")

    if not order_id:
        print("❌ No order_id found in payment payload.")
        return '', 400

    print(f"➡️ Fetching full order from Square for order_id: {order_id}")

    headers = {
        "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.get(
        f"https://connect.squareup.com/v2/orders/{order_id}",
        headers=headers
    )

    print(f"Square API response status: {response.status_code}")
    print("Square API response body:")
    print(response.text)

    if response.status_code != 200:
        print("❌ Failed to fetch order from Square.")
        return '', 500

    order_data = response.json().get("order", {})
    line_items = order_data.get("line_items", [])

    print("✅ Fetched line_items:", line_items)

    total = 0
    for item in line_items:
        name = item.get("name")
        qty = int(item.get("quantity", 0))
        if name in TARGET_ITEMS:
            total += qty
            print(f"✅ Counted {qty} of {name}")
        else:
            print(f"⏭️ Skipped item: {name}")

    if total > 0:
        counter = Counter.query.get(1)
        counter.value += total
        db.session.commit()
        print(f"📈 Updated counter by {total} → new value: {counter.value}")

    return '', 200

@app.route("/smirl.json")
def serve_smirl():
    counter = Counter.query.get(1)
    return jsonify({"value": counter.value if counter else -1000})

@app.route("/set-total", methods=["POST"])
def set_total():
    data = request.get_json()
    value = data.get("value")
    if isinstance(value, int) and value >= 0:
        counter = Counter.query.get(1)
        counter.value = value
        db.session.commit()
        return jsonify({"message": "Total updated", "value": value})
    return jsonify({"error": "Invalid value"}), 400
