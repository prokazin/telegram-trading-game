from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base

class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"

class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"

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
