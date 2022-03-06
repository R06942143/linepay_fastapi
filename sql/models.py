from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.engine.base import Transaction
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.orm import relation, relationship
from .database import Base
from datetime import datetime


class Payment(Base):
    __tablename__ = "payment"
    
    Id = Column(Integer, primary_key=True, nullable=False)
    UserId = Column(String(255), ForeignKey("users.id"), nullable=False)
    OrderId = Column(String(255))
    TransactionId = Column(String(255))
    Source = Column(String(30))
    CreateTime = Column(DateTime, nullable=False, default=datetime.now())
    UpdateTime = Column(DateTime, nullable=False)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, nullable= False)
    username = Column(String(45))
    email = Column(String(60))
    password = Column(String(128))
    token = Column(String(256), default=None)
    left_time = Column(Integer, default=None)
    last_stored = Column(DateTime, default=None)
    line_token = Column(String(256), default=None)
    veri_url = Column(Text, default=None)
    invite_code = Column(Text, default=None)

    payment = relation("Payment")

## this is for ORM model  define database model