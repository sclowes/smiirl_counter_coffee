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

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    print(f"⚠️ Caught unknown request: {request.method} {path}")
    return f"Unknown route: {path}", 404

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

    #event = request.json
    #print("Raw webhook payload:")
    #print(json.dumps(event, indent=2))

    # Extract order_id from webhook
    order_id = (
        event.get("data", {})
             .get("object", {})
             .get("order_updated", {})
             .get("order_id")
    )

    if not order_id:
        print("❌ No order_id found in webhook payload.")
        return '', 400

    print(f"➡️ Fetching full order from Square for order_id: {order_id}")

    # Prepare API request
    headers = {
        "Authorization": f"Bearer {os.environ.get('SQUARE_TOKEN')}",
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

    # Calculate quantity from items
    total = sum(int(item.get("quantity", 0)) for item in line_items)
    print(f"Total items in this order: {total}")

    # Load existing smirl.json
    try:
        with open("smirl.json", "r") as f:
            current = json.load(f).get("value", 0)
    except FileNotFoundError:
        current = 0

    new_total = current + total
    print(f"Updating smirl.json: {current} + {total} = {new_total}")

    # Save updated total
    with open("smirl.json", "w") as f:
        json.dump({"value": new_total}, f)

    return '', 200

@app.route('/routes', methods=['GET'])
def list_routes():
    output = []
    for rule in app.url_map.iter_rules():
        output.append(f"{rule.methods} {rule.rule}")
    return "<br>".join(sorted(output))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
