-- postgres/init.sql
CREATE TABLE IF NOT EXISTS orders (
  order_id TEXT PRIMARY KEY,
  price FLOAT NOT NULL,
  quantity INTEGER NOT NULL,
  remaining INTEGER NOT NULL,
  traded_quantity INTEGER DEFAULT 0,
  average_trade_price FLOAT DEFAULT 0.0,
  side INTEGER NOT NULL,
  alive BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trades (
  trade_id TEXT PRIMARY KEY,
  timestamp FLOAT NOT NULL,
  price FLOAT NOT NULL,
  qty INTEGER NOT NULL,
  bid_order_id TEXT NOT NULL,
  ask_order_id TEXT NOT NULL
);

