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


# остальной код миграций и вспомогательных функций без изменений
