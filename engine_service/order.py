import time
import uuid

class Order:
    def __init__(self, quantity, price, side, timestamp=None):
        self.order_id = str(uuid.uuid4())
        self.quantity = quantity
        self.remaining = quantity
        self.price = price
        self.side = side  # 1 for buy, -1 for sell
        self.traded_quantity = 0
        self.total_trade_value = 0.0
        self.alive = True
        self.timestamp = timestamp if timestamp is not None else time.time()

    def record_trade(self, trade_qty, trade_price):
        self.traded_quantity += trade_qty
        self.total_trade_value += trade_qty * trade_price
        self.remaining -= trade_qty
        if self.remaining <= 0:
            self.alive = False

    def average_trade_price(self):
        if self.traded_quantity == 0:
            return 0.0
        return self.total_trade_value / self.traded_quantity

    def to_dict(self):
        return {
            "order_id": self.order_id,
            "quantity": self.quantity,
            "remaining": self.remaining,
            "price": self.price,
            "side": self.side,
            "traded_quantity": self.traded_quantity,
            "average_trade_price": self.average_trade_price(),
            "alive": self.alive,
            "timestamp": self.timestamp
        }
