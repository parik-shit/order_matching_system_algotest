import os
import time
import json
import redis
from engine import MatchingEngine

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

REQUEST_STREAM = "engine_requests"
RESPONSE_STREAM = "engine_responses"

# Get the singleton matching engine instance (state loaded from DB)
engine = MatchingEngine.get_instance()

def process_request(message_id, data):
    request_id = data.get("request_id")
    action = data.get("action")
    params_str = data.get("params")
    params = json.loads(params_str) if params_str else {}
    
    response = {
        "request_id": request_id,
        "status": "ok",
        "result": ""
    }
    
    try:
        if action == "place_order":
            quantity = int(params["quantity"])
            price = float(params["price"])
            side = int(params["side"])
            order_id = engine.place_order(quantity, price, side)
            response["result"] = json.dumps({"order_id": order_id})
        elif action == "modify_order":
            order_id = params["order_id"]
            new_price = float(params["new_price"])
            success = engine.modify_order(order_id, new_price)
            if not success:
                response["status"] = "error"
                response["error"] = "Order not found or cannot be modified"
            else:
                response["result"] = json.dumps({"success": True})
        elif action == "cancel_order":
            order_id = params["order_id"]
            success = engine.cancel_order(order_id)
            if not success:
                response["status"] = "error"
                response["error"] = "Order not found or cannot be cancelled"
            else:
                response["result"] = json.dumps({"success": True})
        elif action == "fetch_order":
            order_id = params["order_id"]
            fetched = engine.fetch_order(order_id)
            if not fetched:
                response["status"] = "error"
                response["error"] = "Order not found"
            else:
                response["result"] = json.dumps(fetched)
        elif action == "get_all_orders":
            all_orders = engine.get_all_orders()
            response["result"] = json.dumps(all_orders)
        elif action == "get_all_trades":
            all_trades = engine.get_all_trades()
            response["result"] = json.dumps(all_trades)
        else:
            response["status"] = "error"
            response["error"] = f"Unknown action: {action}"
    except Exception as e:
        response["status"] = "error"
        response["error"] = str(e)
    
    r.xadd(RESPONSE_STREAM, response)

def main_loop():
    last_id = "0-0"
    print(f"Engine microservice started. Listening on stream: {REQUEST_STREAM}")
    while True:
        streams = r.xread({REQUEST_STREAM: last_id}, block=5000, count=1)
        if streams:
            for stream_name, messages in streams:
                for message_id, message_data in messages:
                    last_id = message_id
                    data = {k.decode(): v.decode() for k, v in message_data.items()}
                    process_request(message_id, data)
        else:
            time.sleep(0.1)

if __name__ == "__main__":
    main_loop()
