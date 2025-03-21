from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://order_user:order_password@postgres:5432/order_db")

engine_db = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_db)
Base = declarative_base()

class OrderModel(Base):
    __tablename__ = "orders"
    order_id = Column(String, primary_key=True, index=True)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    remaining = Column(Integer, nullable=False)
    traded_quantity = Column(Integer, default=0)
    average_trade_price = Column(Float, default=0.0)
    side = Column(Integer, nullable=False)
    alive = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TradeModel(Base):
    __tablename__ = "trades"
    trade_id = Column(String, primary_key=True, index=True)
    timestamp = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    qty = Column(Integer, nullable=False)
    bid_order_id = Column(String, nullable=False)
    ask_order_id = Column(String, nullable=False)
