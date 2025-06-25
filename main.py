import os
import json
import requests
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")

class Counter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, default=0)

@app.route("/smirl.json")
def serve_smirl():
    counter = Counter.query.get(1)
    return jsonify({"value": counter.value if counter else -1000})

@app.route("/set-total", methods=["POST"])
def set_total():
    data = request.get_json()
    value = data.get("value")
    if isinstance(value, int):
        counter = Counter.query.get(1)
        if not counter:
            counter = Counter(id=1, value=value)
            db.session.add(counter)
        else:
            counter.value = value
        db.session.commit()
        return jsonify({"message": "Total updated", "value": value})
    return jsonify({"error": "Invalid value"}), 400

@app.route("/square-webhook", methods=["POST"])
def square_webhook():
    print("✅ Webhook route triggered")
    event = request.json
    event_type = event.get("type")

    if event_type != "payment.created":
        print(f"❌ Ignored event type: {event_type}")
        return '', 200

    payment = event.get("data", {}).get("object", {}).get("payment", {})
    order_id = payment.get("order_id")

    if not order_id:
        print("❌ No order_id found in payment.created payload.")
        return '', 400

    print(f"➡️ Fetching full order from Square for order_id: {order_id}")
    headers = {
        "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.get(f"https://connect.squareup.com/v2/orders/{order_id}", headers=headers)

    print(f"Square API response status: {response.status_code}")
    print("Square API response body:")
    print(response.text)

    if response.status_code != 200:
        print("❌ Failed to fetch order from Square.")
        return '', 500

    order_data = response.json().get("order", {})
    line_items = order_data.get("line_items", [])

    print("✅ Fetched line_items:", line_items)

    total = sum(int(item.get("quantity", 0)) for item in line_items)
    print(f"Total items in this order: {total}")

    counter = Counter.query.get(1)
    if not counter:
        counter = Counter(id=1, value=total)
        db.session.add(counter)
    else:
        counter.value += total
    db.session.commit()

    return '', 200

# Ensure tables exist and counter is initialized
with app.app_context():
    db.create_all()
    if not Counter.query.get(1):
        db.session.add(Counter(id=1, value=0))
        db.session.commit()

if __name__ == "__main__":
    app.run()
