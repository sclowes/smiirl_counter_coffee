from flask import Flask, jsonify, request
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SQUARE_ACCESS_TOKEN = os.environ.get("SQUARE_TOKEN")
LOCATION_ID = os.environ.get("SQUARE_LOCATION")

TRACKED_ITEMS = [
    "Americano", "CBD Coffee Americano", "CBD Coffee Latte", "Cappuccino", "Cortado",
    "Espresso", "Filter Coffee", "Flat White", "Latte", "Long Black", "Macchiato", "Mocha",
    "Mushroom Coffee Americano", "Mushroom Coffee Latte", "Mushroom Mocha", "V60",
    "Iced Americano", "Iced Latte", "Iced Mocha"
]

def get_item_counts():
    url = "https://connect.squareup.com/v2/orders/search"
    headers = {
        "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "location_ids": [LOCATION_ID],
        "query": {
            "filter": {
                "state_filter": {
                    "states": ["COMPLETED"]
                }
            }
        }
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print("Square API Error:", response.status_code, response.text)
        return {}

    orders = response.json().get("orders", [])
    item_counts = {item: 0 for item in TRACKED_ITEMS}

    for order in orders:
        for item in order.get("line_items", []):
            name = item["name"]
            qty = int(item.get("quantity", 0))
            if name in item_counts:
                item_counts[name] += qty

    return item_counts

@app.route('/')
def home():
    return 'SMIRL Square Counter is running!'

@app.route('/items-sold.json')
def items_sold():
    counts = get_item_counts()
    return jsonify(counts)

@app.route('/smirl.json')
def serve_smirl():
    try:
        with open("smirl.json", "r") as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"value": -1000})

@app.route('/square-webhook', methods=['POST'])
def square_webhook():
    print("✅ Webhook route triggered") 
    event = request.json
    if event.get("type") == "order.updated":
        order = event.get("data", {}).get("object", {}).get("order", {})
        state = order.get("state", "")
        if state == "COMPLETED":
            print("New completed order received via webhook!")
            item_counts = get_item_counts()
            total = sum(item_counts.values())
            with open("smirl.json", "w") as f:
                json.dump({"value": total}, f)
    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
