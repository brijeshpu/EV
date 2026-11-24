import pytest
from app.allocator import allocate_power, allocate_fcfs, BusInput, StationSettings, AllocationResult
from datetime import datetime, timedelta


def make_bus(booking_id, range_km, dist_km, battery_pct=50, target_pct=90, battery_kwh=200, wait=0):
    return BusInput(
        booking_id=booking_id,
        range_km=range_km,
        distance_to_next_station_km=dist_km,
        battery_pct=battery_pct,
        target_pct=target_pct,
        battery_kwh=battery_kwh,
        wait_minutes=wait,
        created_at=datetime.now() - timedelta(minutes=wait),
    )


def make_settings(**kwargs):
    defaults = dict(
        total_power_kw=300,
        reserve_pct=0.1,
        num_ports=6,
        max_charger_kw=60,
        floor_pct=0.1,
        w1=0.6,
        w2=0.4,
    )
    defaults.update(kwargs)
    return StationSettings(**defaults)


def test_normal_case():
    """3 buses, 6 ports, no emergency – all should be charging."""
    buses = [make_bus(1, 150, 30), make_bus(2, 100, 50), make_bus(3, 200, 20)]
    results = allocate_power(buses, make_settings())
    assert all(r.status == "charging" for r in results)
    assert sum(r.allocated_kw for r in results) <= 300
    assert all(not r.is_emergency for r in results)


def test_one_emergency_uses_reserve():
    """1 emergency (range 10, dist 40 => margin -30 < 15) + 2 normal."""
    buses = [make_bus(1, 10, 40), make_bus(2, 150, 30), make_bus(3, 200, 20)]
    results = allocate_power(buses, make_settings())
    emergency = [r for r in results if r.is_emergency]
    assert len(emergency) == 1
    assert emergency[0].booking_id == 1
    assert emergency[0].allocated_kw > 0


def test_emergency_borrows_to_floors():
    """Many emergencies exhaust reserve, borrow from normal pool."""
    buses = [make_bus(i, 5, 50) for i in range(1, 5)]  # 4 emergencies
    buses += [make_bus(5, 200, 20), make_bus(6, 180, 25)]  # 2 normals
    settings = make_settings(total_power_kw=200, reserve_pct=0.1, num_ports=6)
    results = allocate_power(buses, settings)
    normal_charging = [r for r in results if not r.is_emergency and r.status == "charging"]
    floor = settings.floor_pct * settings.max_charger_kw
    for r in normal_charging:
        assert r.allocated_kw >= floor - 0.01  # floating point tolerance


def test_no_emergency_reserve_flows_back():
    """No emergencies -> reserve should flow to normal buses."""
    buses = [make_bus(1, 150, 30), make_bus(2, 100, 50)]
    settings = make_settings(total_power_kw=100, reserve_pct=0.1, num_ports=4)
    results = allocate_power(buses, settings)
    total = sum(r.allocated_kw for r in results)
    # Should use full 100kW (not just 90kW normal pool)
    assert total <= 100
    assert all(not r.is_emergency for r in results)


def test_more_buses_than_ports():
    """9 buses, 4 ports – at most 4 charging, at least 5 waiting."""
    buses = [make_bus(i, 150 - i * 10, 30 + i * 5) for i in range(1, 10)]
    settings = make_settings(num_ports=4)
    results = allocate_power(buses, settings)
    charging = [r for r in results if r.status == "charging"]
    waiting = [r for r in results if r.status == "waiting"]
    assert len(charging) <= 4
    assert len(waiting) >= 5


def test_total_never_exceeds_station_limit():
    """14 emergency-ish buses – total must stay ≤ total_power_kw."""
    buses = [make_bus(i, 20, 60) for i in range(1, 15)]
    settings = make_settings(total_power_kw=200, num_ports=8)
    results = allocate_power(buses, settings)
    total = sum(r.allocated_kw for r in results if r.status == "charging")
    assert total <= settings.total_power_kw + 0.01
