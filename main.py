import os
import json
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SQUARE_TOKEN = os.getenv("SQUARE_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ALLOWED_LOCATION_ID = os.getenv("SQUARE_LOCATION")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Coffee items to track
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

# DB Model
class Counter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, default=0)

# Run setup once before first request
initialized = False

@app.before_request
def setup_once():
    global initialized
    if not initialized:
        db.create_all()
        if not Counter.query.get(1):
            db.session.add(Counter(id=1, value=0))
            db.session.commit()
        initialized = True

# Serve smirl JSON
@app.route("/smirl.json")
def serve_smirl():
    counter = Counter.query.get(1)
    return jsonify({"value": counter.value if counter else 0})

# Manually set counter
@app.route("/set-total", methods=["POST"])
def set_total():
    data = request.get_json()
    value = data.get("value")
    if value is not None:
        counter = Counter.query.get(1)
        counter.value = value
        db.session.commit()
        return jsonify({"message": "Total updated", "value": counter.value})
    return jsonify({"error": "No value provided"}), 400

# Square webhook handler
@app.route("/square-webhook", methods=["POST"])
def square_webhook():
    print("✅ Webhook route triggered")

    event = request.json

    payment_data = event.get("data", {}).get("object", {}).get("payment", {})
    order_id = payment_data.get("order_id")
    location_id = payment_data.get("location_id")
    print(f"Location_id: {location_id}")
    
    if not order_id:
        print("❌ No order_id found in payment payload.")
        return '', 400

    if location_id != ALLOWED_LOCATION_ID:
        print(f"🚫 Ignored webhook from location_id: {location_id}")
        return '', 200  # Gracefully ignore, no error

    print(f"➡️ Fetching full order from Square for order_id: {order_id}")

    headers = {
        "Authorization": f"Bearer {SQUARE_TOKEN}",
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

    filtered_items = [item["name"] for item in line_items if item.get("name") in TARGET_ITEMS]
    print(f"✅ Counted items: {filtered_items}")

    total = sum(int(item.get("quantity", 0)) for item in line_items if item.get("name") in TARGET_ITEMS)
    print(f"Total coffee items in this order: {total}")

    counter = Counter.query.get(1)
    counter.value += total
    db.session.commit()

    return '', 200

if __name__ == "__main__":
    print("📦 Flask app starting up...")
    app.run(host="0.0.0.0", port=8080)
