import os
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime,
    ForeignKey, func, select, update, desc, text
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()
engine = create_async_engine(os.getenv("DATABASE_URL"), future=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", 0))

class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    role = Column(String, default="user")
    payout = Column(BigInteger, default=0)
    joined_at = Column(DateTime, server_default=func.now())
    banned_until = Column(DateTime, nullable=True)
    user_rank = Column(String, nullable=True)  # Старый "rank" → user_rank
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
        await conn.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                      WHERE table_name='users' AND column_name='user_id' AND data_type='integer'
                ) THEN
                    ALTER TABLE users ALTER COLUMN user_id TYPE BIGINT;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                      WHERE table_name='applications' AND column_name='user_id' AND data_type='integer'
                ) THEN
                    ALTER TABLE applications ALTER COLUMN user_id TYPE BIGINT;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                      WHERE table_name='payouts' AND column_name='user_id' AND data_type='integer'
                ) THEN
                    ALTER TABLE payouts ALTER COLUMN user_id TYPE BIGINT;
                END IF;
            END;
            $$;
        """))

async def ensure_banned_until_column(engine):
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name
              FROM information_schema.columns
             WHERE table_name='users' AND column_name='banned_until'
        """))
        if not result.scalar():
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN banned_until TIMESTAMP NULL;
            """))

async def ensure_user_rank_rename(engine):
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name
              FROM information_schema.columns
             WHERE table_name='users' AND column_name='rank'
        """))
        if result.scalar():
            await conn.execute(text("""
                ALTER TABLE users RENAME COLUMN rank TO user_rank;
            """))

# Data-access functions (get_user_by_id, etc.)
async def get_user_by_id(user_id: int):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

async def create_user_if_not_exists(user_id: int):
    async with SessionLocal() as session:
        user = await get_user_by_id(user_id)
        if not user:
            role = "superadmin" if user_id == SUPER_ADMIN_ID else "user"
            new_user = User(user_id=user_id, role=role)
            session.add(new_user)
            await session.commit()
            return new_user
        else:
            if user.user_id == SUPER_ADMIN_ID and user.role != "superadmin":
                await session.execute(
                    update(User).where(User.user_id == user_id).values(role="superadmin")
                )
                await session.commit()
                user.role = "superadmin"
            return user

async def update_user_name(user_id: int, name: str):
    async with SessionLocal() as session:
        await session.execute(update(User).where(User.user_id == user_id).values(name=name))
        await session.commit()

async def update_user_wallet(user_id: int, wallet: str):
    async with SessionLocal() as session:
        await session.execute(update(User).where(User.user_id == user_id).values(contact=wallet))
        await session.commit()

async def get_top_users(period="day"):
    now = datetime.utcnow()
    since = now - {
        "day": timedelta(days=1),
        "week": timedelta(weeks=1),
        "month": timedelta(days=30),
    }.get(period, timedelta(days=1))

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
        res = await session.execute(
            select(func.sum(Payout.amount)).where(func.date(Payout.created_at) == today)
        )
        return res.scalar()
