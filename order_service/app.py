from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import uuid
import json
import time

app = FastAPI()

# Redis configuration (using container name 'redis')
REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_DB   = 0

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

REQUEST_STREAM = "engine_requests"
RESPONSE_STREAM = "engine_responses"

def send_request_and_wait(action, params, timeout=5):
    """
    Sends a request to the engine microservice by adding a message to the request stream,
    then waits for a matching response from the response stream.
    """
    request_id = str(uuid.uuid4())
    message = {
        "request_id": request_id,
        "action": action,
        "params": json.dumps(params)
    }
    r.xadd(REQUEST_STREAM, message)
    
    start_time = time.time()
    last_id = "0-0"
    while time.time() - start_time < timeout:
        streams = r.xread({RESPONSE_STREAM: last_id}, block=5000, count=10)
        if streams:
            for stream, messages in streams:
                for message_id, message_data in messages:
                    data = {k.decode(): v.decode() for k, v in message_data.items()}
                    if data.get("request_id") == request_id:
                        if data.get("status") == "ok":
                            return json.loads(data.get("result", "{}"))
                        else:
                            return {"error": data.get("error")}
                    last_id = message_id
        time.sleep(0.01)
    return {"error": "Timeout waiting for engine response"}

class OrderRequest(BaseModel):
    quantity: int
    price: float
    side: int  # 1 for buy, -1 for sell

class ModifyRequest(BaseModel):
    price: float

@app.post("/order")
def place_order(order: OrderRequest):
    if order.quantity <= 0 or order.price <= 0 or order.side not in [1, -1]:
        raise HTTPException(status_code=400, detail="Invalid order parameters")
    response = send_request_and_wait("place_order", {
        "quantity": order.quantity,
        "price": order.price,
        "side": order.side
    })
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    return response

@app.put("/order/{order_id}")
def modify_order(order_id: str, modify: ModifyRequest):
    response = send_request_and_wait("modify_order", {
        "order_id": order_id,
        "new_price": modify.price
    })
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    return response

@app.delete("/order/{order_id}")
def cancel_order(order_id: str):
    response = send_request_and_wait("cancel_order", {
        "order_id": order_id
    })
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    return response

@app.get("/order/{order_id}")
def fetch_order(order_id: str):
    response = send_request_and_wait("fetch_order", {"order_id": order_id})
    if "error" in response:
        raise HTTPException(status_code=404, detail=response["error"])
    return response

@app.get("/orders")
def all_orders():
    response = send_request_and_wait("get_all_orders", {})
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    return response

@app.get("/trades")
def all_trades():
    response = send_request_and_wait("get_all_trades", {})
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    return response
