from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config import DB_PATH

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    date = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    barmans = relationship("Barman", back_populates="event")
    coupons = relationship("Coupon", back_populates="event")


class Barman(Base):
    __tablename__ = "barmans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=True)
    name = Column(String, nullable=False)
    pin = Column(String(6), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="barmans")
    assigned_coupons = relationship(
        "Coupon",
        foreign_keys="Coupon.assigned_barman_id",
        back_populates="assigned_barman",
    )
    redeemed_coupons = relationship(
        "Coupon",
        foreign_keys="Coupon.redeemed_by_barman_id",
        back_populates="redeemed_by_barman",
    )


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    holder_email = Column(String, nullable=True)
    holder_name = Column(String, nullable=True)
    assigned_barman_id = Column(Integer, ForeignKey("barmans.id"), nullable=True)
    hmac_signature = Column(String, nullable=False)
    redeemed_at = Column(DateTime, nullable=True)
    redeemed_by_barman_id = Column(Integer, ForeignKey("barmans.id"), nullable=True)
    email_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="coupons")
    assigned_barman = relationship(
        "Barman",
        foreign_keys=[assigned_barman_id],
        back_populates="assigned_coupons",
    )
    redeemed_by_barman = relationship(
        "Barman",
        foreign_keys=[redeemed_by_barman_id],
        back_populates="redeemed_coupons",
    )


def create_tables():
    Base.metadata.create_all(bind=engine)
