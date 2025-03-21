import time
import uuid

class Trade:
    def __init__(self, bid_order_id, ask_order_id, price, qty):
        self.trade_id = str(uuid.uuid4())
        self.timestamp = time.time()
        self.price = price
        self.qty = qty
        self.bid_order_id = bid_order_id
        self.ask_order_id = ask_order_id

    def to_dict(self):
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp,
            "price": self.price,
            "qty": self.qty,
            "bid_order_id": self.bid_order_id,
            "ask_order_id": self.ask_order_id
        }
