"""
AMPWISE power-allocation engine.

Pure functions — NO database or SQLAlchemy imports.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class BusInput:
    booking_id: int
    range_km: float
    distance_to_next_station_km: float
    battery_pct: float
    target_pct: float
    battery_kwh: float
    wait_minutes: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class StationSettings:
    total_power_kw: float
    reserve_pct: float
    num_ports: int
    max_charger_kw: float
    floor_pct: float
    w1: float = 0.6
    w2: float = 0.4
    max_range_km: float = 250.0
    max_dist_km: float = 100.0
    safe_margin_km: float = 15.0


@dataclass
class AllocationResult:
    booking_id: int
    allocated_kw: float
    rank: int
    status: str  # "charging" | "waiting"
    is_emergency: bool
    score: float
    explanation: str


# ── Scoring helpers ──────────────────────────────────────────────────────────

def _score_bus(bus: BusInput, s: StationSettings):
    range_urgency = 1.0 - min(bus.range_km / s.max_range_km, 1.0)
    distance_urgency = min(bus.distance_to_next_station_km / s.max_dist_km, 1.0)
    score = s.w1 * range_urgency + s.w2 * distance_urgency
    margin_km = bus.range_km - bus.distance_to_next_station_km
    is_emergency = margin_km < s.safe_margin_km
    return score, is_emergency, margin_km


# ── AMPWISE allocator ───────────────────────────────────────────────────────

def allocate_power(
    buses: List[BusInput],
    settings: StationSettings,
) -> List[AllocationResult]:
    if not buses:
        return []

    s = settings

    # 1. Score each bus
    scored: list[tuple[BusInput, float, bool, float]] = []
    for bus in buses:
        score, is_emerg, margin = _score_bus(bus, s)
        scored.append((bus, score, is_emerg, margin))

    # 2. Sort: emergencies first (score desc, wait desc), then normals (same)
    emergencies = [(b, sc, e, m) for b, sc, e, m in scored if e]
    normals = [(b, sc, e, m) for b, sc, e, m in scored if not e]

    emergencies.sort(key=lambda x: (x[1], x[0].wait_minutes), reverse=True)
    normals.sort(key=lambda x: (x[1], x[0].wait_minutes), reverse=True)

    sorted_all = emergencies + normals

    # 3. Charging set = first num_ports buses, rest = waiting
    charging_set = sorted_all[: s.num_ports]
    waiting_set = sorted_all[s.num_ports :]

    # 4. Pools
    reserve_pool = s.total_power_kw * s.reserve_pct
    normal_pool = s.total_power_kw - reserve_pool

    # Separate charging buses into emergency and normal subsets
    emergency_charging = [(b, sc, e, m) for b, sc, e, m in charging_set if e]
    normal_charging = [(b, sc, e, m) for b, sc, e, m in charging_set if not e]

    # 5. Floor for non-emergency charging buses
    floor = s.floor_pct * s.max_charger_kw

    # Drop lowest-scored normals to waiting until normal_pool >= num_normal * floor
    while normal_charging and normal_pool < len(normal_charging) * floor:
        dropped = normal_charging.pop()  # lowest scored is last
        waiting_set.append(dropped)

    # 6. Deduct floors from normal_pool; record each normal bus alloc = floor
    alloc_map: dict[int, float] = {}
    for b, sc, e, m in normal_charging:
        alloc_map[b.booking_id] = floor
    normal_pool -= len(normal_charging) * floor

    # 7. Emergency buses get from reserve first, then borrow from normal_pool
    for b, sc, e, m in emergency_charging:
        need = s.max_charger_kw
        given = 0.0
        # From reserve
        take_reserve = min(need, reserve_pool)
        given += take_reserve
        reserve_pool -= take_reserve
        need -= take_reserve
        # Borrow from normal_pool if reserve ran out
        if need > 0:
            take_normal = min(need, normal_pool)
            given += take_normal
            normal_pool -= take_normal
        alloc_map[b.booking_id] = given

    # 8. Unused reserve flows back to normal_pool
    normal_pool += reserve_pool
    reserve_pool = 0.0

    # 9. Distribute remaining normal_pool to normal charging buses in score order
    for b, sc, e, m in normal_charging:
        headroom = s.max_charger_kw - alloc_map[b.booking_id]
        give = min(headroom, normal_pool)
        if give > 0:
            alloc_map[b.booking_id] += give
            normal_pool -= give

    # Safety clamp: total must never exceed total_power_kw
    total_allocated = sum(alloc_map.values())
    if total_allocated > s.total_power_kw:
        excess = total_allocated - s.total_power_kw
        # Trim from lowest-scored normal charging buses first
        for b, sc, e, m in reversed(normal_charging):
            if excess <= 0:
                break
            current = alloc_map[b.booking_id]
            can_trim = max(0.0, current - floor)
            trim = min(can_trim, excess)
            alloc_map[b.booking_id] -= trim
            excess -= trim

    # 10. Build results with ranks
    results: list[AllocationResult] = []
    rank = 1

    # Charging buses (maintain sorted order for ranks)
    actual_charging = emergency_charging + normal_charging
    for b, sc, e, m in actual_charging:
        kw = alloc_map[b.booking_id]
        if e:
            expl = (
                f"Emergency: range {b.range_km:.0f} km, next station "
                f"{b.distance_to_next_station_km:.0f} km. Reserve power allocated."
            )
        else:
            expl = (
                f"Normal: score {sc:.2f}, rank #{rank}. "
                f"Allocated {kw:.1f} kW."
            )
        results.append(AllocationResult(
            booking_id=b.booking_id,
            allocated_kw=round(kw, 2),
            rank=rank,
            status="charging",
            is_emergency=e,
            score=round(sc, 4),
            explanation=expl,
        ))
        rank += 1

    # Waiting buses
    for b, sc, e, m in waiting_set:
        if e:
            expl = (
                f"Emergency (waiting): range {b.range_km:.0f} km, next station "
                f"{b.distance_to_next_station_km:.0f} km. No port available."
            )
        else:
            expl = (
                f"Normal (waiting): score {sc:.2f}, rank #{rank}. "
                f"Waiting for available port."
            )
        results.append(AllocationResult(
            booking_id=b.booking_id,
            allocated_kw=0.0,
            rank=rank,
            status="waiting",
            is_emergency=e,
            score=round(sc, 4),
            explanation=expl,
        ))
        rank += 1

    return results


# ── FCFS allocator (baseline) ────────────────────────────────────────────────

def allocate_fcfs(
    buses: List[BusInput],
    settings: StationSettings,
) -> List[AllocationResult]:
    if not buses:
        return []

    s = settings

    # Sort by created_at (first come, first served)
    sorted_buses = sorted(buses, key=lambda b: b.created_at)

    # First num_ports get power, rest wait
    charging = sorted_buses[: s.num_ports]
    waiting = sorted_buses[s.num_ports :]

    # Divide total_power_kw equally, each capped at max_charger_kw
    if charging:
        equal_share = s.total_power_kw / len(charging)
        per_bus_kw = min(equal_share, s.max_charger_kw)
    else:
        per_bus_kw = 0.0

    results: list[AllocationResult] = []
    rank = 1

    for bus in charging:
        score, is_emerg, margin = _score_bus(bus, s)
        results.append(AllocationResult(
            booking_id=bus.booking_id,
            allocated_kw=round(per_bus_kw, 2),
            rank=rank,
            status="charging",
            is_emergency=is_emerg,
            score=round(score, 4),
            explanation=f"FCFS: rank #{rank}. Allocated {per_bus_kw:.1f} kW.",
        ))
        rank += 1

    for bus in waiting:
        score, is_emerg, margin = _score_bus(bus, s)
        results.append(AllocationResult(
            booking_id=bus.booking_id,
            allocated_kw=0.0,
            rank=rank,
            status="waiting",
            is_emergency=is_emerg,
            score=round(score, 4),
            explanation=f"FCFS (waiting): rank #{rank}. No port available.",
        ))
        rank += 1

    return results
