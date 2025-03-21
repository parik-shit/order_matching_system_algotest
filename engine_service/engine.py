# import time
# import threading
# import uuid
# from collections import OrderedDict
# import json

# from order import Order
# from trade import Trade
# from db_models import SessionLocal, OrderModel, TradeModel

# class MatchingEngine:
#     _instance = None
#     _lock = threading.Lock()

#     @classmethod
#     def get_instance(cls):
#         with cls._lock:
#             if cls._instance is None:
#                 cls._instance = cls()
#             return cls._instance

#     def __init__(self):
#         self.orders = {}  # order_id -> Order
#         self.bid_levels = {}  # price -> OrderedDict for buy orders
#         self.ask_levels = {}  # price -> OrderedDict for sell orders
#         self.best_bid = None
#         self.best_ask = None
#         self.trades = []  # List of Trade objects
#         self.engine_lock = threading.Lock()
#         # Load persisted state on startup
#         self.load_state_from_db()

#     # --- Persistence Helper Methods ---
#     def _persist_order(self, order: Order):
#         db = SessionLocal()
#         db_order = db.query(OrderModel).filter(OrderModel.order_id == order.order_id).first()
#         if db_order:
#             db_order.price = order.price
#             db_order.quantity = order.quantity
#             db_order.remaining = order.remaining
#             db_order.traded_quantity = order.traded_quantity
#             db_order.average_trade_price = order.average_trade_price()
#             db_order.side = order.side
#             db_order.alive = order.alive
#         else:
#             db_order = OrderModel(
#                 order_id=order.order_id,
#                 price=order.price,
#                 quantity=order.quantity,
#                 remaining=order.remaining,
#                 traded_quantity=order.traded_quantity,
#                 average_trade_price=order.average_trade_price(),
#                 side=order.side,
#                 alive=order.alive
#             )
#             db.add(db_order)
#         db.commit()
#         db.close()

#     def _persist_trade(self, trade: Trade):
#         db = SessionLocal()
#         db_trade = TradeModel(
#             trade_id=trade.trade_id,
#             timestamp=trade.timestamp,
#             price=trade.price,
#             qty=trade.qty,
#             bid_order_id=trade.bid_order_id,
#             ask_order_id=trade.ask_order_id
#         )
#         db.add(db_trade)
#         db.commit()
#         db.close()

#     def load_state_from_db(self):
#         """
#         Loads orders and trades from the database to rebuild the in-memory state.
#         Active orders are reinserted into their corresponding price levels.
#         """
#         db = SessionLocal()
#         orders = db.query(OrderModel).all()
#         for db_order in orders:
#             order = Order(quantity=db_order.quantity, price=db_order.price, side=db_order.side,
#                           timestamp=db_order.created_at.timestamp() if db_order.created_at else time.time())
#             order.order_id = db_order.order_id
#             order.remaining = db_order.remaining
#             order.traded_quantity = db_order.traded_quantity
#             order.total_trade_value = (db_order.average_trade_price * db_order.traded_quantity) if db_order.traded_quantity > 0 else 0.0
#             order.alive = db_order.alive
#             self.orders[order.order_id] = order
#             if order.alive:
#                 if order.side == 1:
#                     if order.price not in self.bid_levels:
#                         self.bid_levels[order.price] = OrderedDict()
#                     self.bid_levels[order.price][order.order_id] = order
#                     if self.best_bid is None or order.price > self.best_bid:
#                         self.best_bid = order.price
#                 else:
#                     if order.price not in self.ask_levels:
#                         self.ask_levels[order.price] = OrderedDict()
#                     self.ask_levels[order.price][order.order_id] = order
#                     if self.best_ask is None or order.price < self.best_ask:
#                         self.best_ask = order.price
#         trades = db.query(TradeModel).all()
#         for db_trade in trades:
#             trade = Trade(db_trade.bid_order_id, db_trade.ask_order_id, db_trade.price, db_trade.qty)
#             trade.trade_id = db_trade.trade_id
#             trade.timestamp = db_trade.timestamp
#             self.trades.append(trade)
#         db.close()

#     # --- Order Book Management ---
#     def _insert_order(self, order: Order):
#         levels = self.bid_levels if order.side == 1 else self.ask_levels
#         if order.price not in levels:
#             levels[order.price] = OrderedDict()
#         levels[order.price][order.order_id] = order
#         if order.side == 1:
#             if self.best_bid is None or order.price > self.best_bid:
#                 self.best_bid = order.price
#         else:
#             if self.best_ask is None or order.price < self.best_ask:
#                 self.best_ask = order.price

#     def _remove_order(self, order: Order):
#         levels = self.bid_levels if order.side == 1 else self.ask_levels
#         if order.price in levels and order.order_id in levels[order.price]:
#             del levels[order.price][order.order_id]
#             if not levels[order.price]:
#                 del levels[order.price]
#                 if order.side == 1:
#                     self.best_bid = max(levels.keys()) if levels else None
#                 else:
#                     self.best_ask = min(levels.keys()) if levels else None

#     # --- Public API Operations ---
#     def place_order(self, quantity, price, side):
#         with self.engine_lock:
#             order = Order(quantity, price, side)
#             self.orders[order.order_id] = order
#             self.match_order(order)
#             if order.alive:
#                 self._insert_order(order)
#             self._persist_order(order)
#             return order.order_id

#     def modify_order(self, order_id, new_price):
#         with self.engine_lock:
#             if order_id not in self.orders:
#                 return False
#             order = self.orders[order_id]
#             if not order.alive:
#                 return False
#             self._remove_order(order)
#             order.price = new_price
#             self.match_order(order)
#             if order.alive:
#                 self._insert_order(order)
#             self._persist_order(order)
#             return True

#     def cancel_order(self, order_id):
#         with self.engine_lock:
#             if order_id not in self.orders:
#                 return False
#             order = self.orders[order_id]
#             if not order.alive:
#                 return False
#             self._remove_order(order)
#             order.alive = False
#             order.remaining = 0
#             self._persist_order(order)
#             return True

#     def fetch_order(self, order_id):
#         with self.engine_lock:
#             if order_id in self.orders:
#                 return order.to_dict() if (order := self.orders.get(order_id)) else None
#             return None

#     def get_all_orders(self):
#         with self.engine_lock:
#             return [order.to_dict() for order in self.orders.values()]

#     def get_all_trades(self):
#         with self.engine_lock:
#             return [trade.to_dict() for trade in self.trades]

#     # --- Matching Logic ---
#     def match_order(self, incoming_order: Order):
#         if incoming_order.side == 1:  # Buy order: match with asks
#             while incoming_order.remaining > 0 and self.best_ask is not None and self.best_ask <= incoming_order.price:
#                 level = self.ask_levels.get(self.best_ask)
#                 if not level:
#                     self.best_ask = min(self.ask_levels.keys()) if self.ask_levels else None
#                     continue
#                 for resting_order_id in list(level.keys()):
#                     if incoming_order.remaining <= 0:
#                         break
#                     resting_order = level[resting_order_id]
#                     if resting_order.price <= incoming_order.price:
#                         trade_qty = min(incoming_order.remaining, resting_order.remaining)
#                         trade_price = resting_order.price
#                         trade = Trade(incoming_order.order_id, resting_order.order_id, trade_price, trade_qty)
#                         self.trades.append(trade)
#                         incoming_order.record_trade(trade_qty, trade_price)
#                         resting_order.record_trade(trade_qty, trade_price)
#                         self._persist_trade(trade)
#                         self._persist_order(incoming_order)
#                         self._persist_order(resting_order)
#                         if not resting_order.alive:
#                             del level[resting_order_id]
#                     else:
#                         break
#                 if not level:
#                     del self.ask_levels[self.best_ask]
#                     self.best_ask = min(self.ask_levels.keys()) if self.ask_levels else None
#                 if self.best_ask is None or self.best_ask > incoming_order.price:
#                     break
#         else:  # Sell order: match with bids
#             while incoming_order.remaining > 0 and self.best_bid is not None and self.best_bid >= incoming_order.price:
#                 level = self.bid_levels.get(self.best_bid)
#                 if not level:
#                     self.best_bid = max(self.bid_levels.keys()) if self.bid_levels else None
#                     continue
#                 for resting_order_id in list(level.keys()):
#                     if incoming_order.remaining <= 0:
#                         break
#                     resting_order = level[resting_order_id]
#                     if resting_order.price >= incoming_order.price:
#                         trade_qty = min(incoming_order.remaining, resting_order.remaining)
#                         trade_price = resting_order.price
#                         trade = Trade(resting_order.order_id, incoming_order.order_id, trade_price, trade_qty)
#                         self.trades.append(trade)
#                         incoming_order.record_trade(trade_qty, trade_price)
#                         resting_order.record_trade(trade_qty, trade_price)
#                         self._persist_trade(trade)
#                         self._persist_order(incoming_order)
#                         self._persist_order(resting_order)
#                         if not resting_order.alive:
#                             del level[resting_order_id]
#                     else:
#                         break
#                 if not level:
#                     del self.bid_levels[self.best_bid]
#                     self.best_bid = max(self.bid_levels.keys()) if self.bid_levels else None
#                 if self.best_bid is None or self.best_bid < incoming_order.price:
#                     break


import time
import threading
import uuid
import json
import os
import redis
from collections import OrderedDict

from order import Order
from trade import Trade
from db_models import SessionLocal, OrderModel, TradeModel

# --- Redis Setup ---
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.Redis.from_url(redis_url)

class MatchingEngine:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self.orders = {}  # order_id -> Order
        self.bid_levels = {}  # price -> OrderedDict for buy orders
        self.ask_levels = {}  # price -> OrderedDict for sell orders
        self.best_bid = None
        self.best_ask = None
        self.trades = []  # List of Trade objects
        self.engine_lock = threading.Lock()

        # Load persisted state on startup
        self.load_state_from_db()

    # ------------------------------------------------------------------------
    # Persistence Helpers
    # ------------------------------------------------------------------------
    def _persist_order(self, order: Order):
        db = SessionLocal()
        db_order = db.query(OrderModel).filter(OrderModel.order_id == order.order_id).first()
        if db_order:
            db_order.price = order.price
            db_order.quantity = order.quantity
            db_order.remaining = order.remaining
            db_order.traded_quantity = order.traded_quantity
            db_order.average_trade_price = order.average_trade_price()
            db_order.side = order.side
            db_order.alive = order.alive
        else:
            db_order = OrderModel(
                order_id=order.order_id,
                price=order.price,
                quantity=order.quantity,
                remaining=order.remaining,
                traded_quantity=order.traded_quantity,
                average_trade_price=order.average_trade_price(),
                side=order.side,
                alive=order.alive
            )
            db.add(db_order)
        db.commit()
        db.close()

    def _persist_trade(self, trade: Trade):
        db = SessionLocal()
        db_trade = TradeModel(
            trade_id=trade.trade_id,
            timestamp=trade.timestamp,
            price=trade.price,
            qty=trade.qty,
            bid_order_id=trade.bid_order_id,
            ask_order_id=trade.ask_order_id
        )
        db.add(db_trade)
        db.commit()
        db.close()

    def load_state_from_db(self):
        """
        Loads orders and trades from the database to rebuild the in-memory state.
        Active orders are reinserted into their corresponding price levels.
        """
        db = SessionLocal()
        orders = db.query(OrderModel).all()
        for db_order in orders:
            order = Order(
                quantity=db_order.quantity,
                price=db_order.price,
                side=db_order.side,
                timestamp=db_order.created_at.timestamp() if db_order.created_at else time.time()
            )
            order.order_id = db_order.order_id
            order.remaining = db_order.remaining
            order.traded_quantity = db_order.traded_quantity
            order.total_trade_value = (
                db_order.average_trade_price * db_order.traded_quantity
                if db_order.traded_quantity > 0 else 0.0
            )
            order.alive = db_order.alive
            self.orders[order.order_id] = order
            if order.alive:
                if order.side == 1:
                    if order.price not in self.bid_levels:
                        self.bid_levels[order.price] = OrderedDict()
                    self.bid_levels[order.price][order.order_id] = order
                    if self.best_bid is None or order.price > self.best_bid:
                        self.best_bid = order.price
                else:
                    if order.price not in self.ask_levels:
                        self.ask_levels[order.price] = OrderedDict()
                    self.ask_levels[order.price][order.order_id] = order
                    if self.best_ask is None or order.price < self.best_ask:
                        self.best_ask = order.price

        # Load trades into memory (not strictly necessary unless you want them in self.trades)
        trades = db.query(TradeModel).all()
        for db_trade in trades:
            t = Trade(db_trade.bid_order_id, db_trade.ask_order_id, db_trade.price, db_trade.qty)
            t.trade_id = db_trade.trade_id
            t.timestamp = db_trade.timestamp
            self.trades.append(t)

        db.close()

    # ------------------------------------------------------------------------
    # Redis Notification Helpers
    # ------------------------------------------------------------------------
    def notify_trade(self, trade: Trade):
        """
        Publish a trade message to the "trade_notifications" channel.
        """
        trade_data = json.dumps(trade.to_dict())
        redis_client.publish("trade_notifications", trade_data)

    def update_orderbook_in_redis(self):
        """
        Store the latest order book snapshot in Redis as JSON.
        """
        snapshot = self.get_orderbook_snapshot()
        # Optionally add a timestamp
        snapshot['timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime())
        redis_client.set("latest_orderbook_snapshot", json.dumps(snapshot))

    # ------------------------------------------------------------------------
    # Order Book Management
    # ------------------------------------------------------------------------
    def _insert_order(self, order: Order):
        levels = self.bid_levels if order.side == 1 else self.ask_levels
        if order.price not in levels:
            levels[order.price] = OrderedDict()
        levels[order.price][order.order_id] = order
        if order.side == 1:
            if self.best_bid is None or order.price > self.best_bid:
                self.best_bid = order.price
        else:
            if self.best_ask is None or order.price < self.best_ask:
                self.best_ask = order.price

    def _remove_order(self, order: Order):
        levels = self.bid_levels if order.side == 1 else self.ask_levels
        if order.price in levels and order.order_id in levels[order.price]:
            del levels[order.price][order.order_id]
            if not levels[order.price]:
                del levels[order.price]
                if order.side == 1:
                    self.best_bid = max(levels.keys()) if levels else None
                else:
                    self.best_ask = min(levels.keys()) if levels else None

    # ------------------------------------------------------------------------
    # Public API Operations
    # ------------------------------------------------------------------------
    def place_order(self, quantity, price, side):
        with self.engine_lock:
            order = Order(quantity, price, side)
            self.orders[order.order_id] = order
            self.match_order(order)
            if order.alive:
                self._insert_order(order)
            self._persist_order(order)

            # Update order book snapshot in Redis
            self.update_orderbook_in_redis()

            return order.order_id

    def modify_order(self, order_id, new_price):
        with self.engine_lock:
            if order_id not in self.orders:
                return False
            order = self.orders[order_id]
            if not order.alive:
                return False
            self._remove_order(order)
            order.price = new_price
            self.match_order(order)
            if order.alive:
                self._insert_order(order)
            self._persist_order(order)

            # Update order book snapshot in Redis
            self.update_orderbook_in_redis()

            return True

    def cancel_order(self, order_id):
        with self.engine_lock:
            if order_id not in self.orders:
                return False
            order = self.orders[order_id]
            if not order.alive:
                return False
            self._remove_order(order)
            order.alive = False
            order.remaining = 0
            self._persist_order(order)

            # Update order book snapshot in Redis
            self.update_orderbook_in_redis()

            return True

    def fetch_order(self, order_id):
        with self.engine_lock:
            if order_id in self.orders:
                return self.orders[order_id].to_dict()
            return None

    def get_all_orders(self):
        with self.engine_lock:
            return [order.to_dict() for order in self.orders.values()]

    def get_all_trades(self):
        with self.engine_lock:
            return [trade.to_dict() for trade in self.trades]

    # ------------------------------------------------------------------------
    # Matching Logic
    # ------------------------------------------------------------------------
    def match_order(self, incoming_order: Order):
        """
        Matches an incoming order against the order book.
        For buys: match with lowest ask first.
        For sells: match with highest bid first.
        """
        if incoming_order.side == 1:  # Buy order
            while (incoming_order.remaining > 0 and 
                   self.best_ask is not None and 
                   self.best_ask <= incoming_order.price):
                level = self.ask_levels.get(self.best_ask)
                if not level:
                    self.best_ask = min(self.ask_levels.keys()) if self.ask_levels else None
                    continue
                for resting_order_id in list(level.keys()):
                    if incoming_order.remaining <= 0:
                        break
                    resting_order = level[resting_order_id]
                    if resting_order.price <= incoming_order.price:
                        trade_qty = min(incoming_order.remaining, resting_order.remaining)
                        trade_price = resting_order.price
                        trade = Trade(incoming_order.order_id, resting_order.order_id, trade_price, trade_qty)
                        self.trades.append(trade)

                        # Notify trade via Redis pub/sub
                        self.notify_trade(trade)

                        # Update in-memory orders
                        incoming_order.record_trade(trade_qty, trade_price)
                        resting_order.record_trade(trade_qty, trade_price)

                        # Persist trade & orders
                        self._persist_trade(trade)
                        self._persist_order(incoming_order)
                        self._persist_order(resting_order)

                        if not resting_order.alive:
                            del level[resting_order_id]
                    else:
                        break
                if not level:
                    del self.ask_levels[self.best_ask]
                    self.best_ask = min(self.ask_levels.keys()) if self.ask_levels else None
                if self.best_ask is None or self.best_ask > incoming_order.price:
                    break
        else:  # Sell order
            while (incoming_order.remaining > 0 and 
                   self.best_bid is not None and 
                   self.best_bid >= incoming_order.price):
                level = self.bid_levels.get(self.best_bid)
                if not level:
                    self.best_bid = max(self.bid_levels.keys()) if self.bid_levels else None
                    continue
                for resting_order_id in list(level.keys()):
                    if incoming_order.remaining <= 0:
                        break
                    resting_order = level[resting_order_id]
                    if resting_order.price >= incoming_order.price:
                        trade_qty = min(incoming_order.remaining, resting_order.remaining)
                        trade_price = resting_order.price
                        trade = Trade(resting_order.order_id, incoming_order.order_id, trade_price, trade_qty)
                        self.trades.append(trade)

                        # Notify trade via Redis pub/sub
                        self.notify_trade(trade)

                        # Update in-memory orders
                        incoming_order.record_trade(trade_qty, trade_price)
                        resting_order.record_trade(trade_qty, trade_price)

                        # Persist trade & orders
                        self._persist_trade(trade)
                        self._persist_order(incoming_order)
                        self._persist_order(resting_order)

                        if not resting_order.alive:
                            del level[resting_order_id]
                    else:
                        break
                if not level:
                    del self.bid_levels[self.best_bid]
                    self.best_bid = max(self.bid_levels.keys()) if self.bid_levels else None
                if self.best_bid is None or self.best_bid < incoming_order.price:
                    break

    # ------------------------------------------------------------------------
    # Order Book Snapshot
    # ------------------------------------------------------------------------
    def get_orderbook_snapshot(self):
        """
        Returns top 5 bids and asks, aggregated by price level.
        """
        bids_snapshot = []
        asks_snapshot = []

        bid_prices = sorted(self.bid_levels.keys(), reverse=True)[:5]
        for price in bid_prices:
            total_qty = sum(o.remaining for o in self.bid_levels[price].values() if o.alive)
            bids_snapshot.append({'price': price, 'quantity': total_qty})

        ask_prices = sorted(self.ask_levels.keys())[:5]
        for price in ask_prices:
            total_qty = sum(o.remaining for o in self.ask_levels[price].values() if o.alive)
            asks_snapshot.append({'price': price, 'quantity': total_qty})

        return {
            'bids': bids_snapshot,
            'asks': asks_snapshot
        }
