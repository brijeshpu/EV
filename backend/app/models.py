from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func,
)
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="operator")  # "operator" | "admin"
    display_name = Column(String, nullable=True)

    vehicles = relationship("Vehicle", back_populates="owner")
    bookings = relationship("Booking", back_populates="operator")
    ratings = relationship("Rating", back_populates="operator")


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    num_ports = Column(Integer, nullable=False)
    total_power_kw = Column(Float, nullable=False)
    reserve_pct = Column(Float, default=0.12)
    max_charger_kw = Column(Float, nullable=False)
    floor_pct = Column(Float, default=0.10)
    tariff = Column(Float, nullable=False)
    w1 = Column(Float, default=0.6)
    w2 = Column(Float, default=0.4)
    is_faulty = Column(Boolean, default=False)
    fault_message = Column(String, nullable=True)

    bookings = relationship("Booking", back_populates="station")
    ratings = relationship("Rating", back_populates="station")
    alerts = relationship("Alert", back_populates="station")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    reg_number = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)  # "bus" | "cab" | "hospital_vehicle" | "private"
    model = Column(String, nullable=False)
    battery_capacity_kwh = Column(Float, nullable=False)
    connector_type = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    current_range_km = Column(Float, nullable=True)
    availability = Column(String, default="available")  # "available" | "in_use" | "maintenance"
    next_departure = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="vehicles")
    bookings = relationship("Booking", back_populates="vehicle")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    battery_pct = Column(Float, nullable=False)
    target_pct = Column(Float, nullable=False)
    range_km = Column(Float, nullable=False)
    distance_to_next_km = Column(Float, nullable=False)
    preferred_arrival = Column(DateTime, nullable=True)
    status = Column(String, default="queued")  # queued / charging / completed / cancelled
    energy_delivered_kwh = Column(Float, default=0)
    prepaid_estimate = Column(Float, default=0)
    final_bill = Column(Float, nullable=True)
    refund = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())
    started_charging_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    operator = relationship("User", back_populates="bookings")
    vehicle = relationship("Vehicle", back_populates="bookings")
    station = relationship("Station", back_populates="bookings")
    allocation = relationship("Allocation", back_populates="booking", uselist=False)
    ratings = relationship("Rating", back_populates="booking")


class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    allocated_kw = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    is_emergency = Column(Boolean, nullable=False)
    score = Column(Float, nullable=False)
    explanation = Column(String, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    booking = relationship("Booking", back_populates="allocation")


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stars = Column(Integer, nullable=False)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    booking = relationship("Booking", back_populates="ratings")
    station = relationship("Station", back_populates="ratings")
    operator = relationship("User", back_populates="ratings")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    message = Column(String, nullable=False)
    alert_type = Column(String, default="fault")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    station = relationship("Station", back_populates="alerts")
