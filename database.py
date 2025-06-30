import os
from sqlalchemy import (Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()
engine = create_async_engine(os.getenv("DATABASE_URL"), future=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class User(Base):
    tablename = "users"
    user_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    role = Column(String, default="user")
    payout = Column(Integer, default=0)
    joined_at = Column(DateTime, server_default=func.now())
    applications = relationship("Application", back_populates="user")
    payouts_hist = relationship("Payout", back_populates="user")

class Application(Base):
    tablename = "applications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    message = Column(Text)
    status = Column(String, default="pending")  # pending | approved | rejected
    created_at = Column(DateTime, server_default=func.now())
    resolved_by = Column(Integer, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="applications")

class Payout(Base):
    tablename = "payouts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    amount = Column(Integer)
    issued_by = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="payouts_hist")

class News(Base):
    tablename = "news"
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    sent = Column(Boolean, default=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
