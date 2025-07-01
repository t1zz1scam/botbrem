import os
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, func, select, update, desc
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()
engine = create_async_engine(os.getenv("DATABASE_URL"), future=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    role = Column(String, default="user")
    payout = Column(Integer, default=0)
    joined_at = Column(DateTime, server_default=func.now())
    applications = relationship("Application", back_populates="user")
    payouts_hist = relationship("Payout", back_populates="user")

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    message = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    resolved_by = Column(Integer, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="applications")

class Payout(Base):
    __tablename__ = "payouts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    amount = Column(Integer)
    issued_by = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="payouts_hist")

class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    sent = Column(Boolean, default=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Функции для профиля и работы с БД (оставляй без изменений)
async def get_user_by_id(user_id):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

async def update_user_name(user_id, name):
    async with SessionLocal() as session:
        await session.execute(update(User).where(User.user_id == user_id).values(name=name))
        await session.commit()

async def update_user_wallet(user_id, wallet):
    async with SessionLocal() as session:
        await session.execute(update(User).where(User.user_id == user_id).values(contact=wallet))
        await session.commit()

async def get_top_users(period="day"):
    now = datetime.utcnow()
    if period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(weeks=1)
    elif period == "month":
        since = now - timedelta(days=30)
    else:
        since = now - timedelta(days=1)

    async with SessionLocal() as session:
        result = await session.execute(
            select(User.name, func.sum(Payout.amount).label("earned"))
            .join(Payout)
            .where(Payout.created_at >= since)
            .group_by(User.user_id)
            .order_by(desc("earned"))
            .limit(10)
        )
        return result.mappings().all()

async def get_total_earned_today():
    today = datetime.utcnow().date()
    async with SessionLocal() as session:
        result = await session.execute(
            select(func.sum(Payout.amount)).where(func.date(Payout.created_at) == today)
        )
        return result.scalar()
