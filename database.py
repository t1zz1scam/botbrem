import os
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime,
    ForeignKey, func, select, update, desc, text, Numeric
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from config import DATABASE_URL, SUPERADMIN_ID

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True)  # BigInteger для избежания переполнения
    name = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    role = Column(String, default="user")
    payout = Column(BigInteger, default=0)
    joined_at = Column(DateTime, server_default=func.now())
    banned_until = Column(DateTime, nullable=True)
    user_rank = Column(String, nullable=True)  # убедился, что это user_rank, не rank

    # Указываем foreign_keys, чтобы убрать неоднозначность, тк в Application 2 fk к User
    applications = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[Application.user_id]"
    )
    payouts_hist = relationship(
        "Payout",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[Payout.user_id]"
    )


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    message = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    resolved_by = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="applications"
    )
    resolver = relationship(
        "User",
        foreign_keys=[resolved_by],
        uselist=False  # один резолвер на заявку
    )


class Payout(Base):
    __tablename__ = "payouts"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)  # числовой формат для сумм, лучше decimal
    issued_by = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="payouts_hist"
    )
    issuer = relationship(
        "User",
        foreign_keys=[issued_by],
        uselist=False
    )


class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    sent = Column(Boolean, default=False)


# Вспомогательные функции
async def get_user_by_id(user_id: int):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

async def create_user_if_not_exists(user_id: int):
    async with SessionLocal() as session:
        user = await get_user_by_id(user_id)
        if not user:
            role = "superadmin" if user_id == SUPERADMIN_ID else "user"
            new_user = User(user_id=user_id, role=role)
            session.add(new_user)
            await session.commit()
            return new_user
        else:
            if user.user_id == SUPERADMIN_ID and user.role != "superadmin":
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
