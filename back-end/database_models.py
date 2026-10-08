from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    CheckConstraint
)

from sqlalchemy.orm import relationship


Base = declarative_base()  # conventional name


class ChargePoints(Base):
    __tablename__ = "ChargePoints"
    pointid = Column(Integer, primary_key=True, index=True)

    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)

    status = Column(
        String,
        nullable=False,
        default="offline"
    )

    cap = Column(Integer)  
    reservation_endtime = Column(DateTime ,nullable = True, default = None)
    kwhprice = Column(Float, nullable=False, default=1.0)

    __table_args__ = (
        CheckConstraint("lat >= -90", name="lat_min"),
        CheckConstraint("lat <= 90", name="lat_max"),
        CheckConstraint("lon >= -180", name="lon_min"),
        CheckConstraint("lon <= 180", name="lon_max"),
        CheckConstraint("cap > 0", name="Cap_should_be_positive"),
        CheckConstraint("kwhprice >= 0", name="kwhprice_non_negative"),
        CheckConstraint("status IN ('available', 'charging', 'reserved', 'malfunction', 'offline' )", name="valid_status"),
        CheckConstraint("(status = 'reserved') OR (reservation_endtime IS NULL)",name="reservation_endtime_required_if_reserved")
    )

    sessions = relationship("ChargingSessionHistory", back_populates="charge_point") #one to many relations
    status_history = relationship("StatusHistory", back_populates="charge_point")

     # 🔹 Reservation relationship (1-to-1)
    reservation = relationship(
        "Reservations",
        back_populates="charge_point",
        uselist=False,
        cascade="all, delete-orphan"
    )



class ChargingSessionHistory(Base):
    __tablename__ = "ChargingSessionHistory"
    session_id = Column(Integer, primary_key=True, index=True)
    pointid = Column(Integer, ForeignKey("ChargePoints.pointid"), nullable=False)

    starttime = Column(DateTime, nullable=False)
    endtime = Column(DateTime, nullable=False)

    startsoc = Column(Integer, nullable=False)
    endsoc = Column(Integer, nullable=False)

    totalkwh = Column(Float, nullable=False)
    kwhprice = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("startsoc >= 0", name="startsoc_min"),
        CheckConstraint("startsoc <= 100", name="startsoc_max"),
        CheckConstraint("endsoc >= startsoc", name="endsoc_min"),
        CheckConstraint("endsoc <= 100", name="endsoc_max"),
        CheckConstraint("totalkwh > 0", name="totalkwh_positive"),
        CheckConstraint("kwhprice >= 0", name="kwhprice_non_negative"),
        CheckConstraint("amount >= 0", name="amount_non_negative"),
    )

    charge_point = relationship("ChargePoints", back_populates="sessions")


class StatusHistory(Base):
    __tablename__ = "StatusHistory"
    id = Column(Integer, primary_key=True, index=True)
    pointid = Column(Integer, ForeignKey("ChargePoints.pointid"), nullable=False)

    timeref = Column(DateTime, nullable=False)

    old_state = Column(String, nullable=False)
    new_state = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint(  "old_state IN ('available', 'charging', 'reserved', 'malfunction', 'offline' )", name="valid_old_status"),
        CheckConstraint(  "new_state IN ('available', 'charging', 'reserved', 'malfunction', 'offline' )", name="valid_new_status")
    )

    charge_point = relationship("ChargePoints", back_populates="status_history")


class Reservations(Base):
    __tablename__ = "Reservations"
    id = Column(Integer, primary_key=True, index=True)
    pointid = Column(Integer, ForeignKey("ChargePoints.pointid"), nullable=False)

    endtime = Column(DateTime, nullable=False)
    
    charge_point = relationship("ChargePoints",back_populates="reservation")