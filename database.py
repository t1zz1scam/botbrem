import os
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime,
    ForeignKey, func, select, update, desc, text
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env variable is not set")

engine = create_async_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    role = Column(String, default="user")
    payout = Column(BigInteger, default=0)
    joined_at = Column(DateTime, server_default=func.now())
    applications = relationship("Application", back_populates="user")
    payouts_hist = relationship("Payout", back_populates="user")

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"))
    message = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    resolved_by = Column(BigInteger, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="applications")

class Payout(Base):
    __tablename__ = "payouts"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"))
    amount = Column(BigInteger)
    issued_by = Column(BigInteger)
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

async def run_bigint_migration(engine):
    async with engine.begin() as conn:
        # Проверяем тип поля users.user_id
        result = await conn.execute(text("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='user_id'
        """))
        row = await result.first()
        if row:
            data_type = row[0]
            if data_type != 'bigint':
                print("Migrating users.user_id to BIGINT...")
                await conn.execute(text("""
                    ALTER TABLE users ALTER COLUMN user_id TYPE BIGINT;
                """))
            else:
                print("users.user_id already BIGINT")
        else:
            print("Column users.user_id not found")

        # Проверяем тип поля payouts.amount
        result = await conn.execute(text("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name='payouts' AND column_name='amount'
        """))
        row = await result.first()
        if row:
            data_type = row[0]
            if data_type != 'bigint':
                print("Migrating payouts.amount to BIGINT...")
                await conn.execute(text("""
                    ALTER TABLE payouts ALTER COLUMN amount TYPE BIGINT;
                """))
            else:
                print("payouts.amount already BIGINT")
        else:
            print("Column payouts.amount not found")

# Остальные функции (get_user_by_id, create_user_if_not_exists и т.д.) можно оставить без изменений
