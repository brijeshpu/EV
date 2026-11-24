from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    id: int
    username: str
    role: str
    display_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Stations ─────────────────────────────────────────────────────────────────

class StationOut(BaseModel):
    id: int
    name: str
    city: str
    lat: float
    lng: float
    num_ports: int
    total_power_kw: float
    reserve_pct: float
    max_charger_kw: float
    floor_pct: float
    tariff: float
    w1: float
    w2: float
    is_faulty: bool
    fault_message: Optional[str] = None

    model_config = {"from_attributes": True}


class StationUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    num_ports: Optional[int] = None
    total_power_kw: Optional[float] = None
    reserve_pct: Optional[float] = None
    max_charger_kw: Optional[float] = None
    floor_pct: Optional[float] = None
    tariff: Optional[float] = None
    w1: Optional[float] = None
    w2: Optional[float] = None
    is_faulty: Optional[bool] = None
    fault_message: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Vehicles ─────────────────────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    reg_number: str
    type: str
    model: str
    battery_capacity_kwh: float
    connector_type: str
    owner_id: int
    current_range_km: Optional[float] = None
    next_departure: Optional[datetime] = None


class VehicleOut(BaseModel):
    id: int
    reg_number: str
    type: str
    model: str
    battery_capacity_kwh: float
    connector_type: str
    owner_id: int
    current_range_km: Optional[float] = None
    availability: str
    next_departure: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Allocations ──────────────────────────────────────────────────────────────

class AllocationOut(BaseModel):
    booking_id: int
    allocated_kw: float
    rank: int
    is_emergency: bool
    score: float
    explanation: str
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Bookings ─────────────────────────────────────────────────────────────────

class BookingCreate(BaseModel):
    operator_id: int
    vehicle_id: int
    station_id: int
    battery_pct: float
    target_pct: float
    range_km: float
    distance_to_next_km: float
    preferred_arrival: Optional[datetime] = None

    @field_validator("battery_pct")
    @classmethod
    def battery_pct_range(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError("battery_pct must be between 0 and 100")
        return v

    @field_validator("target_pct")
    @classmethod
    def target_pct_range(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError("target_pct must be between 0 and 100")
        return v

    @field_validator("range_km")
    @classmethod
    def range_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("range_km must be non-negative")
        return v

    @field_validator("distance_to_next_km")
    @classmethod
    def distance_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("distance_to_next_km must be non-negative")
        return v

    @field_validator("target_pct")
    @classmethod
    def target_gt_battery(cls, v: float, info) -> float:
        battery = info.data.get("battery_pct")
        if battery is not None and v <= battery:
            raise ValueError("target_pct must be greater than battery_pct")
        return v


class BookingOut(BaseModel):
    id: int
    operator_id: int
    vehicle_id: int
    station_id: int
    battery_pct: float
    target_pct: float
    range_km: float
    distance_to_next_km: float
    preferred_arrival: Optional[datetime] = None
    status: str
    energy_delivered_kwh: float
    prepaid_estimate: float
    final_bill: Optional[float] = None
    refund: Optional[float] = None
    created_at: Optional[datetime] = None
    started_charging_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    allocation: Optional[AllocationOut] = None

    model_config = {"from_attributes": True}


# ── Queue ────────────────────────────────────────────────────────────────────

class QueueEntry(BaseModel):
    booking_id: int
    vehicle_reg: str
    allocated_kw: float
    rank: int
    status: str
    is_emergency: bool
    score: float
    explanation: str
    battery_pct: float
    target_pct: float
    progress_pct: float
    eta_minutes: float

    model_config = {"from_attributes": True}


# ── Ratings ──────────────────────────────────────────────────────────────────

class RatingCreate(BaseModel):
    booking_id: int
    station_id: int
    operator_id: int
    stars: int
    comment: Optional[str] = None

    @field_validator("stars")
    @classmethod
    def stars_range(cls, v: int) -> int:
        if not (1 <= v <= 5):
            raise ValueError("stars must be between 1 and 5")
        return v


class RatingOut(BaseModel):
    id: int
    booking_id: int
    station_id: int
    operator_id: int
    stars: int
    comment: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Alerts ───────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: int
    station_id: int
    message: str
    alert_type: str
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Compare ──────────────────────────────────────────────────────────────────

class CompareMetrics(BaseModel):
    total_kw: float
    avg_kw: float
    emergencies_served: int
    min_alloc_kw: float
    max_alloc_kw: float
    std_dev_kw: float


class CompareResult(BaseModel):
    ampwise: CompareMetrics
    fcfs: CompareMetrics


# ── Nearby Stations ──────────────────────────────────────────────────────────

class NearbyStation(BaseModel):
    id: int
    name: str
    city: str
    distance_km: float
    free_ports: int

    model_config = {"from_attributes": True}
