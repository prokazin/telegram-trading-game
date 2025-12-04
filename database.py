from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum
from config import Config

Base = declarative_base()
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"

class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"

class PositionType(enum.Enum):
    LONG = "long"
    SHORT = "short"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    balance = Column(Float, default=Config.INITIAL_BALANCE)
    total_profit = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    rank = Column(Integer, default=0)
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")

class Position(Base):
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    symbol = Column(String, nullable=False)
    position_type = Column(Enum(PositionType), nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    leverage = Column(Integer, nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    liquidation_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    margin = Column(Float, nullable=False)
    is_open = Column(Boolean, default=True)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="positions")

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    symbol = Column(String, nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    leverage = Column(Integer, nullable=False)
    filled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="orders")

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(String, nullable=False)  # 'deposit', 'withdrawal', 'trade', 'fee', 'liquidation'
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
