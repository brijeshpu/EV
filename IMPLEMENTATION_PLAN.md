# AMPWISE — Implementation Plan

## Goal Description

**AMPWISE** is a smart EV bus charging booking and power-allocation web app for a hackathon ("Compute 50 — Smart Cities and Urban Innovation"). Cities adding electric buses face a constraint: each charging station has a fixed power limit and cannot charge all buses at full speed simultaneously. AMPWISE replaces first-come-first-served with a **weighted-score dynamic priority queue** that considers range urgency and distance-to-next-station, with an emergency reserve pool, minimum power floors, and automatic reallocation.

The prototype must be **demo-ready**: a clean UI, working simulation, and seed data for Tamil Nadu stations.

---

## Misalignment Analysis & Corrections

After thorough review of all 13 sections, I identified these issues and made the following corrections:

> [!IMPORTANT]
> **1. Emergency "safe level" graduation (§5 step 6) vs. booking target:**
> The spec says emergency buses charge only to a "safe level" and then become normal buses. But a booking has a `target_pct`. Resolution: once an emergency bus reaches the safe level (energy to reach next station + 20% buffer), its `is_emergency` flag flips to `false`, it moves to the normal pool, and continues charging to `target_pct` at normal priority. The allocation function recalculates on each cycle.

> [!IMPORTANT]
> **2. `wait_minutes` in the scoring function inputs:**
> `wait_minutes` is listed as an input but never used in the score formula. Resolution: I will pass it through and include it in the explanation text ("waiting 12 min") and use it as a tiebreaker for equal scores (longer wait = higher priority). This avoids scope creep while using the field.

> [!IMPORTANT]
> **3. Prepaid estimate timing:**
> The spec mentions `prepaid_estimate` and `refund` but doesn't specify when the estimate is computed. Resolution: computed at booking creation time using `(target_pct - battery_pct) / 100 * battery_kwh * tariff`. On cancellation or completion, `final_bill = energy_delivered_kwh * tariff` and `refund = max(0, prepaid_estimate - final_bill)`.

> [!NOTE]
> **4. Compare endpoint (§9) metrics:**
> "Buses ready" = buses that would reach target earlier under AMPWISE vs. FCFS; "peak load" = max simultaneous kW; "delay for non-emergency" = average extra wait for non-emergency buses. The FCFS baseline allocator assigns equal power to all connected buses in arrival order.

> [!NOTE]
> **5. Polling interval:**
> The spec says 3 seconds for live status. The simulation ticks every 2 seconds. These are independent — the frontend polls the latest state every 3 s; the backend simulation advances every 2 s.

> [!NOTE]
> **6. `psql` not installed on this machine.**
> I'll use SQLAlchemy with `asyncpg` / `psycopg2` and provide `.env` configuration so the app connects to any Postgres instance (local Docker, Neon, Supabase, etc.). The seed script uses SQLAlchemy directly.

---

## Open Questions

> [!IMPORTANT]
> **PostgreSQL access:** `psql` is not installed locally. Do you have a Postgres instance running (Docker, local install, or cloud like Neon/Supabase)? If not, I can add a `docker-compose.yml` for one-command Postgres setup, or use SQLite as a fallback for the hackathon demo. **Recommendation: add `docker-compose.yml` with Postgres.**

> [!NOTE]
> **Deployment:** The README will document Vercel/Netlify (frontend) + Render/Railway (backend) + Neon/Supabase (DB) deployment. No actual deployment will be done during implementation. OK?

---

## Architecture

### System Architecture Diagram

```mermaid
graph TB
    subgraph "Frontend — React + Vite"
        UI["React SPA"]
        LP["Leaflet Map"]
        RC["Recharts"]
        I18["react-i18next (demo)"]
    end

    subgraph "Backend — FastAPI"
        API["REST API (/api)"]
        ALLOC["Allocation Engine"]
        SIM["Charging Simulator (bg task)"]
        SEED["Seed Script"]
    end

    subgraph "Database — PostgreSQL"
        DB["Tables: users, stations, vehicles, bookings, allocations, ratings, alerts"]
    end

    UI -->|"REST (poll 3s)"| API
    LP --> UI
    RC --> UI
    I18 --> UI
    API --> ALLOC
    API --> DB
    SIM -->|"tick 2s"| ALLOC
    SIM --> DB
    ALLOC --> DB
    SEED --> DB
```

### Directory Structure

```
/Users/brijesh/EV/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, CORS, lifespan (sim task)
│   │   ├── config.py                # Settings from .env
│   │   ├── database.py              # SQLAlchemy engine, session
│   │   ├── models.py                # ORM models
│   │   ├── schemas.py               # Pydantic schemas
│   │   ├── allocator.py             # Pure allocation function + FCFS baseline
│   │   ├── simulator.py             # Background charging simulation
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── stations.py
│   │       ├── vehicles.py
│   │       ├── bookings.py
│   │       ├── queue.py
│   │       ├── analytics.py
│   │       ├── ratings.py
│   │       ├── alerts.py
│   │       └── demo.py
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_allocator.py        # 6+ unit tests
│   ├── seed.py                      # Seed script
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── public/
│   │   ├── manifest.json            # PWA metadata (demo)
│   │   └── icons/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── api.js                   # Axios instance + endpoints
│   │   ├── i18n.js                  # react-i18next setup (demo)
│   │   ├── components/
│   │   │   ├── Header.jsx           # Role, language, bell icon
│   │   │   ├── MapView.jsx          # Leaflet map
│   │   │   ├── ProgressBar.jsx
│   │   │   ├── AllocationBar.jsx    # Recharts bar
│   │   │   ├── QRPlaceholder.jsx    # Demo QR
│   │   │   ├── NotificationBell.jsx # Demo bell
│   │   │   └── FaultBanner.jsx
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx        # Operator: map + station cards
│   │   │   ├── BookCharging.jsx     # Booking form
│   │   │   ├── MyCharging.jsx       # Live status + cancel
│   │   │   ├── StationQueue.jsx     # Queue + allocation chart
│   │   │   ├── History.jsx          # Analytics + ratings
│   │   │   └── Admin.jsx            # Station settings, faults, fleet, demo, compare
│   │   └── locales/                 # en.json, hi.json (demo stubs)
│   ├── index.html
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── vite.config.js
│   ├── package.json
│   └── .env.example
├── docker-compose.yml               # Postgres
├── README.md
└── .gitignore
```

---

## User Flow Diagrams

### Operator Flow

```mermaid
flowchart TD
    A["Login as Operator"] --> B["Operator Dashboard"]
    B --> C["View stations on map"]
    C --> D{"Station faulty?"}
    D -->|Yes| E["See fault banner, booking blocked"]
    D -->|No| F["Click 'Book Charging'"]
    F --> G["Enter vehicle reg number"]
    G --> H{"Vehicle known?"}
    H -->|Yes| I["Auto-fill vehicle details"]
    H -->|No| J["Register new vehicle"]
    J --> I
    I --> K["Fill booking: range, distance, battery%, target%, arrival time"]
    K --> L["See prepaid estimate"]
    L --> M["Submit booking"]
    M --> N["Allocation engine runs"]
    N --> O["See queue position, allocated kW, ETA"]
    O --> P{"Action?"}
    P -->|Wait| Q["Poll status every 3s, see progress bar"]
    Q --> R{"Charging complete?"}
    R -->|Yes| S["See final bill, give rating"]
    R -->|No| Q
    P -->|Cancel early| T["Cancel booking"]
    T --> U["See bill adjustment: energy used × tariff, refund"]
    P -->|Station full/faulty| V["See nearby alternatives on map"]
    B --> W["View charging history & analytics"]
    B --> X["See alerts for faulty stations"]
```

### Admin Flow

```mermaid
flowchart TD
    A["Login as Admin"] --> B["Admin Dashboard"]
    B --> C["Station Management"]
    C --> D["Edit station settings: ports, power, reserve%, floor%, tariff, weights"]
    D --> E["Allocation engine recomputes"]
    B --> F["Fault Management"]
    F --> G["Mark station faulty with message"]
    G --> H["Operators see alert, bookings blocked"]
    F --> I["Clear fault"]
    I --> J["Station operational again"]
    B --> K["Fleet View"]
    K --> L["Table of all vehicles: reg, type, battery, availability"]
    B --> M["Demo Controls"]
    M --> N["Add emergency bus"]
    M --> O["Reduce station capacity 30%"]
    M --> P["Reset demo"]
    B --> Q["AMPWISE vs FCFS Comparison"]
    Q --> R["Side-by-side metrics: buses ready, peak load, delay"]
```

### Allocation Engine Flow

```mermaid
flowchart TD
    A["Trigger: booking / cancel / complete / settings change"] --> B["Gather all active bookings at station"]
    B --> C["Compute score per bus"]
    C --> D["Classify: EMERGENCY if margin < 15 km"]
    D --> E["Sort: emergencies by score desc, then normals by score desc"]
    E --> F["Select charging set: top N = num_ports"]
    F --> G["Reserve pool = total_power × reserve_pct"]
    G --> H["Normal pool = total_power - reserve pool"]
    H --> I["Assign floor to each normal charging bus from normal pool"]
    I --> J{"Normal pool covers all floors?"}
    J -->|No| K["Drop lowest-scored normal buses to waiting"]
    K --> I
    J -->|Yes| L["Allocate reserve pool to emergency buses, each up to max_charger_kw"]
    L --> M{"Reserve exhausted?"}
    M -->|Yes| N["Emergency borrows from normal pool, never below floors"]
    M -->|No| O["Unused reserve flows to normal pool"]
    N --> P["Distribute remaining normal pool by score, up to max_charger_kw"]
    O --> P
    P --> Q["Return: allocated_kw, rank, status, is_emergency, score, explanation"]
```

---

## Database Schema

### Entity Relationship Diagram

```mermaid
erDiagram
    USERS {
        int id PK
        string username
        string password
        string role "operator | admin"
        string display_name
    }

    STATIONS {
        int id PK
        string name
        string city
        float lat
        float lng
        int num_ports
        float total_power_kw
        float reserve_pct "0.10-0.15"
        float max_charger_kw
        float floor_pct "default 0.10"
        float tariff "Rs/kWh"
        float w1 "default 0.6"
        float w2 "default 0.4"
        bool is_faulty "default false"
        string fault_message
    }

    VEHICLES {
        int id PK
        string reg_number UK
        string type "bus | cab | hospital_vehicle | private"
        string model
        float battery_capacity_kwh
        string connector_type
        int owner_id FK
        float current_range_km
        string availability "available | in_use | maintenance"
        datetime next_departure
    }

    BOOKINGS {
        int id PK
        int operator_id FK
        int vehicle_id FK
        int station_id FK
        float battery_pct
        float target_pct
        float range_km
        float distance_to_next_km
        datetime preferred_arrival
        string status "queued | charging | completed | cancelled"
        float energy_delivered_kwh
        float prepaid_estimate
        float final_bill
        float refund
        datetime created_at
        datetime started_charging_at
        datetime completed_at
    }

    ALLOCATIONS {
        int id PK
        int booking_id FK UK
        float allocated_kw
        int rank
        bool is_emergency
        float score
        string explanation
        datetime updated_at
    }

    RATINGS {
        int id PK
        int booking_id FK
        int station_id FK
        int operator_id FK
        int stars "1-5"
        string comment
        datetime created_at
    }

    ALERTS {
        int id PK
        int station_id FK
        string message
        string alert_type "fault | info"
        bool is_active
        datetime created_at
    }

    USERS ||--o{ BOOKINGS : "operator_id"
    USERS ||--o{ VEHICLES : "owner_id"
    USERS ||--o{ RATINGS : "operator_id"
    STATIONS ||--o{ BOOKINGS : "station_id"
    STATIONS ||--o{ ALERTS : "station_id"
    STATIONS ||--o{ RATINGS : "station_id"
    VEHICLES ||--o{ BOOKINGS : "vehicle_id"
    BOOKINGS ||--o| ALLOCATIONS : "booking_id"
    BOOKINGS ||--o| RATINGS : "booking_id"
```

---

## Proposed Changes

### Build Stage 1: Database Models, Config, and Seed

---

#### [NEW] `docker-compose.yml`

Postgres 16 with volume, exposed on port 5432.

```yaml
version: "3.9"
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ampwise
      POSTGRES_PASSWORD: ampwise123
      POSTGRES_DB: ampwise
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

#### [NEW] `backend/.env.example`

```env
DATABASE_URL=postgresql://ampwise:ampwise123@localhost:5432/ampwise
SIM_SPEED=1
SIM_INTERVAL=2
MAX_RANGE_KM=250
MAX_DIST_KM=100
SAFE_MARGIN_KM=15
CORS_ORIGINS=http://localhost:5173
```

#### [NEW] `backend/app/config.py`

Pydantic `BaseSettings` loading from `.env`. Fields: `DATABASE_URL`, `SIM_SPEED`, `SIM_INTERVAL`, `MAX_RANGE_KM`, `MAX_DIST_KM`, `SAFE_MARGIN_KM`, `CORS_ORIGINS`.

#### [NEW] `backend/app/database.py`

Synchronous SQLAlchemy engine + `SessionLocal` factory + `get_db` dependency. Uses `create_all` on startup (no Alembic).

#### [NEW] `backend/app/models.py`

SQLAlchemy ORM models for all 7 tables as described in the ER diagram above. Key design decisions:
- `Booking.status` uses a Python `Enum` mapped to a VARCHAR: `queued`, `charging`, `completed`, `cancelled`.
- `Vehicle.type` as `Enum`: `bus`, `cab`, `hospital_vehicle`, `private`.
- `Allocation` has a unique constraint on `booking_id` (1:1 with active booking).
- Timestamps use `func.now()` defaults.

#### [NEW] `backend/app/schemas.py`

Pydantic v2 schemas for all request/response bodies. Includes validators:
- `battery_pct`: 0–100
- `target_pct`: must be > `battery_pct`
- `range_km`, `distance_to_next_km`: positive floats
- `stars`: 1–5

#### [NEW] `backend/seed.py`

Seeds:
- **3 users:** `operator1` (Operator), `operator2` (Operator), `admin1` (Admin)
- **5 stations** in Tamil Nadu:
  | Station | City | Lat | Lng | Ports | Power (kW) | Reserve% | Max Charger | Floor% | Tariff |
  |---|---|---|---|---|---|---|---|---|---|
  | Coimbatore Central | Coimbatore | 11.0168 | 76.9558 | 6 | 300 | 0.12 | 60 | 0.10 | 8.5 |
  | Chennai Marina | Chennai | 13.0827 | 80.2707 | 8 | 250 | 0.10 | 50 | 0.10 | 9.0 |
  | Madurai Junction | Madurai | 9.9252 | 78.1198 | 4 | 180 | 0.15 | 60 | 0.12 | 7.5 |
  | Trichy Hub | Tiruchirappalli | 10.7905 | 78.7047 | 5 | 200 | 0.10 | 50 | 0.10 | 8.0 |
  | Salem Depot | Salem | 11.6643 | 78.1460 | 4 | 120 | 0.12 | 40 | 0.15 | 7.0 |

- **15–20 vehicles** across all types with varied `battery_capacity_kwh` (40–300 kWh), connectors (CCS2, CHAdeMO, Type2), assigned to operators.
- **8–10 active bookings** at Coimbatore Central (the demo station), with varied battery%, range, and distance values to show different priorities and at least 1 emergency.

**Verification:** Run `seed.py`, query counts from each table.

---

### Build Stage 2: Allocation Function with Tests

---

#### [NEW] `backend/app/allocator.py`

A **pure function** `allocate_power(buses, station_settings)` that takes:

```python
@dataclass
class BusInput:
    booking_id: int
    range_km: float
    distance_to_next_station_km: float
    battery_pct: float
    target_pct: float
    battery_kwh: float
    wait_minutes: float
    created_at: datetime  # for FCFS tiebreaker

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
```

**Algorithm implementation** (follows §5 exactly):

```python
def allocate_power(buses: list[BusInput], settings: StationSettings) -> list[AllocationResult]:
    # 1. Score each bus
    for bus in buses:
        range_urgency = 1 - min(bus.range_km / settings.max_range_km, 1)
        distance_urgency = min(bus.distance_to_next_station_km / settings.max_dist_km, 1)
        bus._score = settings.w1 * range_urgency + settings.w2 * distance_urgency
        margin_km = bus.range_km - bus.distance_to_next_station_km
        bus._is_emergency = margin_km < settings.safe_margin_km

    # 2. Sort: emergencies first (by score desc), then normals (by score desc)
    #    Tiebreaker: higher wait_minutes first
    emergencies = sorted([b for b in buses if b._is_emergency],
                         key=lambda b: (-b._score, -b.wait_minutes))
    normals = sorted([b for b in buses if not b._is_emergency],
                     key=lambda b: (-b._score, -b.wait_minutes))
    ordered = emergencies + normals

    # 3. Charging set = first num_ports, rest = waiting
    charging = ordered[:settings.num_ports]
    waiting = ordered[settings.num_ports:]

    # 4. Pools
    reserve_pool = settings.total_power_kw * settings.reserve_pct
    normal_pool = settings.total_power_kw - reserve_pool
    floor_kw = settings.floor_pct * settings.max_charger_kw

    # 5. Assign floors to non-emergency charging buses
    normal_charging = [b for b in charging if not b._is_emergency]
    emergency_charging = [b for b in charging if b._is_emergency]

    # Ensure normal pool covers all floors; drop lowest if not
    while len(normal_charging) * floor_kw > normal_pool and normal_charging:
        dropped = normal_charging.pop()  # lowest scored
        charging.remove(dropped)
        waiting.insert(0, dropped)

    # Deduct floors from normal pool
    normal_pool -= len(normal_charging) * floor_kw
    allocations = {b.booking_id: floor_kw for b in normal_charging}

    # 6. Emergency buses: draw from reserve, then borrow
    remaining_reserve = reserve_pool
    for bus in emergency_charging:
        need = settings.max_charger_kw
        from_reserve = min(need, remaining_reserve)
        remaining_reserve -= from_reserve
        alloc = from_reserve
        if alloc < need:
            # Borrow from normal pool, respecting floors
            borrow = min(need - alloc, normal_pool)
            alloc += borrow
            normal_pool -= borrow
        allocations[bus.booking_id] = alloc

    # 7. Unused reserve flows back
    normal_pool += remaining_reserve

    # 8. Distribute remaining normal pool to normal buses by score
    for bus in normal_charging:
        top_up = min(settings.max_charger_kw - allocations[bus.booking_id], normal_pool)
        if top_up > 0:
            allocations[bus.booking_id] += top_up
            normal_pool -= top_up

    # 9. Build results ...
```

Also: `def allocate_fcfs(buses, settings)` — sorts by `created_at`, divides power equally among first `num_ports` buses.

#### [NEW] `backend/tests/test_allocator.py`

**6 test cases** using `pytest`:

| # | Test | Assertion |
|---|---|---|
| 1 | Normal case (3 buses, 6 ports, no emergency) | All charging, power distributed by score, total ≤ station limit |
| 2 | One emergency using reserve | Emergency bus gets reserve power, flagged `is_emergency` |
| 3 | Emergency beyond reserve (borrows down to floors) | Emergency gets reserve + borrowed, no normal bus below floor |
| 4 | No emergencies (reserve flows back) | All normal pool + reserve distributed among normals |
| 5 | More buses than ports | Excess buses are `waiting`, rank > num_ports |
| 6 | Total power never exceeds station limit | Sum of all allocated_kw ≤ total_power_kw |

**Verification:** `cd backend && pytest tests/test_allocator.py -v` — all pass.

---

### Build Stage 3: Booking, Queue, Simulation, and Core Endpoints

---

#### [NEW] `backend/app/main.py`

FastAPI app with:
- CORS middleware (origins from `.env`)
- Lifespan: `create_all` tables, start background simulator task
- Include all routers under `/api`

#### [NEW] `backend/app/simulator.py`

Background `asyncio` task (runs in FastAPI lifespan):
- Every `SIM_INTERVAL` seconds (default 2):
  1. Query all bookings with `status = charging` grouped by station
  2. For each charging bus: `energy_increment = (allocated_kw * SIM_SPEED * SIM_INTERVAL) / 3600` kWh
  3. Update `energy_delivered_kwh += energy_increment`
  4. Compute new `battery_pct = old_pct + (energy_increment / battery_capacity_kwh) * 100`
  5. Update `range_km` proportionally
  6. If `battery_pct >= target_pct`: mark `completed`, compute `final_bill`, free port
  7. After any change: call `run_allocation(station_id)` to redistribute

#### [NEW] `backend/app/routers/auth.py`

```
POST /api/auth/login  {username, password} → {user_id, username, role, display_name}
```
Simple lookup — no hashing, no JWT. Returns user object or 401.

#### [NEW] `backend/app/routers/vehicles.py`

```
GET  /api/vehicles/lookup?reg=TN01AB1234  → Vehicle or 404
POST /api/vehicles  {reg_number, type, model, battery_capacity_kwh, connector_type, owner_id} → Vehicle
```

#### [NEW] `backend/app/routers/bookings.py`

```
POST /api/bookings  → Creates booking (queued), computes prepaid_estimate, triggers allocation
GET  /api/bookings?operator_id=1  → List bookings for operator
GET  /api/bookings/{id}  → Single booking with allocation details
POST /api/bookings/{id}/cancel  → Sets status=cancelled, computes final_bill & refund, triggers reallocation
```

Booking creation:
1. Validate inputs (battery < target, positive distances, station not faulty)
2. Check if station has capacity or suggest alternatives
3. Create booking with `status=queued`
4. Compute `prepaid_estimate = (target_pct - battery_pct) / 100 * battery_kwh * tariff`
5. Call `run_allocation(station_id)` — this may promote bus to `charging`

#### [NEW] `backend/app/routers/queue.py`

```
GET /api/stations/{id}/queue → [{booking_id, vehicle_reg, allocated_kw, rank, status, is_emergency, score, explanation, battery_pct, target_pct, progress_pct, eta_minutes}]
```

#### [NEW] `backend/app/routers/stations.py`

```
GET  /api/stations → All stations with port availability counts
GET  /api/stations/{id} → Station details + current queue summary
PUT  /api/stations/{id} → Admin: update settings, trigger reallocation
POST /api/stations/{id}/fault → Admin: mark faulty, create alert
POST /api/stations/{id}/clear-fault → Admin: clear fault
GET  /api/stations/{id}/nearby-alternatives → Haversine-sorted list of non-faulty stations with free ports
GET  /api/stations/{id}/compare → AMPWISE vs FCFS comparison metrics
```

Haversine implementation (in `stations.py` or a utils module):
```python
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))
```

#### [NEW] `backend/app/routers/analytics.py`

```
GET /api/analytics/operator/{id} → {sessions: [...], total_energy_kwh, total_cost, charts_data: {energy_over_time, cost_over_time}}
```

#### [NEW] `backend/app/routers/ratings.py`

```
POST /api/ratings  {booking_id, station_id, operator_id, stars, comment}
GET  /api/stations/{id}/ratings → {average_stars, count, ratings: [...]}
```

#### [NEW] `backend/app/routers/alerts.py`

```
GET /api/alerts?operator_id=1 → Active alerts for stations where operator has/had bookings
```

#### [NEW] `backend/app/routers/demo.py`

```
POST /api/demo/emergency-bus → Creates a low-range bus + booking at demo station
POST /api/demo/reduce-capacity → Cuts demo station power by 30%, triggers reallocation
POST /api/demo/reset → Clears all bookings/allocations, re-runs seed
```

**Verification:** Start server with `uvicorn app.main:app --reload`, test endpoints with `curl` or `httpie`.

---

### Build Stage 4: Frontend — Operator Pages

---

#### [NEW] `frontend/` — Vite + React + Tailwind scaffold

```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install tailwindcss @tailwindcss/vite react-router-dom axios recharts \
  react-leaflet leaflet react-i18next i18next
```

#### [NEW] `frontend/src/api.js`

Axios instance with `baseURL` from env, 3-second polling hook:
```javascript
export function usePolling(fetcher, intervalMs = 3000) {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetcher().then(setData);
    const id = setInterval(() => fetcher().then(setData), intervalMs);
    return () => clearInterval(id);
  }, []);
  return data;
}
```

#### [NEW] `frontend/src/App.jsx`

React Router with routes:
- `/` → Login
- `/dashboard` → Dashboard (operator)
- `/book` → BookCharging
- `/my-charging` → MyCharging
- `/station/:id/queue` → StationQueue
- `/history` → History
- `/admin` → Admin

Auth context stores `{user, role}` in React state (no localStorage complexity needed for demo).

#### [NEW] `frontend/src/pages/Login.jsx`

Clean card-style login form. Also has a **role switcher** toggle for quick demo switching. Tailwind styling, centered on page.

#### [NEW] `frontend/src/pages/Dashboard.jsx`

- Leaflet map centered on Tamil Nadu (lat: 11.1, lng: 78.6, zoom: 7) showing 5 station markers
- Clicking a marker shows a popup: station name, ports free/total, queue length, average rating
- Below map: station cards in a responsive grid. Each card shows:
  - Station name, city
  - Ports: `3/6 free`
  - Queue: `4 buses waiting`
  - Fault banner (red) if faulty
  - "Book" button → navigates to `/book?station={id}`

#### [NEW] `frontend/src/pages/BookCharging.jsx`

Form with:
1. Vehicle registration input → on blur, calls `/api/vehicles/lookup?reg=` → auto-fills if found
2. If not found: expand registration sub-form (type, model, battery_kwh, connector)
3. Fields: current range (km), distance to next station (km), battery %, target %, preferred arrival time
4. Station selector (dropdown, pre-filled if from dashboard)
5. Live estimate: `(target - current) / 100 * battery_kwh * tariff = ₹X`
6. Submit → POST `/api/bookings`
7. On success → navigate to `/my-charging`
8. If station full/faulty → show nearby alternatives on a mini Leaflet map

Validation: target > current battery, positive numbers, all required fields.

#### [NEW] `frontend/src/pages/MyCharging.jsx`

- Polls `/api/bookings?operator_id=` every 3 seconds
- For each active booking, shows a **status card**:
  - Vehicle reg, station name
  - Status badge: 🟡 Queued, 🟢 Charging, ✅ Completed
  - If charging: allocated kW, rank, progress bar (battery_pct → target_pct), ETA
  - If emergency: red badge "⚡ EMERGENCY"
  - Cancel button → POST `/api/bookings/{id}/cancel` → shows bill adjustment (prepaid, actual, refund)
  - QR placeholder with "Coming Soon" label (demo)

#### [NEW] `frontend/src/pages/StationQueue.jsx`

- Station selector dropdown
- Table sorted by rank:
  | Rank | Vehicle | Status | Battery | Target | Allocated kW | Emergency? | Score | Explanation |
- Recharts horizontal bar chart: each bus as a bar showing allocated kW, color-coded (red = emergency, blue = normal, gray = waiting)
- Reserve pool usage indicator (used/total)
- Auto-refreshes every 3 seconds

#### [NEW] `frontend/src/pages/History.jsx`

- Table of past sessions: date, station, vehicle, energy (kWh), cost (₹), duration, status
- Recharts line chart: energy consumed over time
- Recharts bar chart: cost per session
- Rating form for completed sessions: star selector (1–5), comment textarea, submit

**Verification:** `npm run dev`, manually test each page, verify polling works.

---

### Build Stage 5: Admin Pages and Demo Controls

---

#### [NEW] `frontend/src/pages/Admin.jsx`

Tabbed layout with sub-sections:

**Tab 1: Station Settings**
- Select station dropdown
- Editable fields: num_ports, total_power_kw, reserve_pct, max_charger_kw, floor_pct, tariff, w1, w2
- Save button → PUT `/api/stations/{id}`

**Tab 2: Fault Management**
- Station selector
- "Mark Faulty" button with message textarea → POST `/api/stations/{id}/fault`
- "Clear Fault" button → POST `/api/stations/{id}/clear-fault`
- Current status indicator

**Tab 3: Fleet View**
- Table of all vehicles: reg, type, model, battery capacity, connector, owner, availability, next departure
- Filter by type dropdown

**Tab 4: Demo Controls**
- Three big buttons with descriptions:
  - "🚨 Add Emergency Bus" → POST `/api/demo/emergency-bus` → shows result
  - "⚡ Reduce Capacity (-30%)" → POST `/api/demo/reduce-capacity` → shows new power
  - "🔄 Reset Demo" → POST `/api/demo/reset` → reloads page

**Tab 5: AMPWISE vs FCFS**
- Select station
- Side-by-side comparison cards:
  - "Buses reaching target faster" count
  - "Peak load (kW)" comparison
  - "Avg delay for non-emergency (min)" comparison
- Recharts grouped bar chart comparing the two

**Verification:** Admin pages functional, demo controls work end-to-end.

---

### Build Stage 6: Cancellation, Nearby, Ratings, Faults, Analytics

---

This stage wires up the remaining feature endpoints that were stubbed:

- **Cancellation billing:** Cancel endpoint computes `final_bill = energy_delivered_kwh * tariff`, `refund = max(0, prepaid_estimate - final_bill)`. UI shows a bill breakdown card.
- **Nearby stations:** When booking fails (full/faulty), UI calls `/api/stations/{id}/nearby-alternatives` and renders markers on a Leaflet map with distances.
- **Ratings:** After session completes, History page shows a star rating widget. Calls POST `/api/ratings`. Station popup shows average rating.
- **Fault alerts:** GET `/api/alerts?operator_id=` returns active fault alerts. `FaultBanner.jsx` renders at the top of Dashboard and MyCharging pages.
- **Analytics:** History page gets Recharts charts populated from `/api/analytics/operator/{id}`.

**Verification:** End-to-end flow: book → charge → cancel (see refund) or complete (see bill + rate).

---

### Build Stage 7: Dummy Features

---

#### [MODIFY] `frontend/src/components/Header.jsx`

Add:
- **Language dropdown** (English, Hindi, Tamil, Telugu) — changes `i18n.changeLanguage()`, translates ~5 labels (dashboard title, book button, etc.). Comment: `/* DEMO: i18n scaffolding */`
- **Notification bell** — static dropdown with 3 sample notifications. Comment: `/* DEMO: static notifications */`

#### [MODIFY] `frontend/src/pages/MyCharging.jsx`

- **QR placeholder** on booking confirmation card. Comment: `/* DEMO: QR verification coming soon */`

#### [NEW] `frontend/public/manifest.json`

PWA metadata: `name: "AMPWISE"`, `short_name: "AMPWISE"`, `start_url: "/"`, `display: "standalone"`, theme color green. Comment in `index.html`: `<!-- DEMO: PWA metadata -->`.

#### [NEW] `frontend/src/i18n.js` + locale files

`react-i18next` init with `en.json` (full), `hi.json`, `ta.json`, `te.json` (5 translated keys each, rest fallback to English).

**Verification:** Language dropdown changes a few labels, bell shows static items, QR shows placeholder.

---

### Build Stage 8: Polish and README

---

#### UI polish:
- Responsive layout (Tailwind `sm:`, `md:`, `lg:` breakpoints)
- Loading spinners during API calls
- Error toasts / banners for failed requests
- Footer: "AMPWISE — Hackathon Prototype | All data is simulated"
- Consistent color scheme: emerald/green for charging, red for emergency, amber for warnings
- Smooth transitions with Tailwind `transition-all`

#### [MODIFY] `README.md`

Complete README with:
- Project overview and screenshots placeholder
- Tech stack
- Prerequisites (Node 18+, Python 3.11+, PostgreSQL 14+)
- Setup steps (docker-compose, backend venv, seed, frontend npm install)
- Environment variables table
- Run commands (`docker-compose up -d`, `uvicorn`, `npm run dev`)
- API documentation summary
- Deployment notes (Vercel/Netlify + Render/Railway + Neon/Supabase)
- Demo accounts table

#### [NEW] `.gitignore`

```
node_modules/
__pycache__/
*.pyc
.env
dist/
.venv/
```

**Verification:** Full walkthrough: login → dashboard → book → watch simulation → cancel → rate → admin controls → emergency demo.

---

## Verification Plan

### Automated Tests

```bash
# Backend allocation tests
cd backend
pip install pytest
pytest tests/test_allocator.py -v

# Frontend build check
cd frontend
npm run build
```

### Manual Verification

1. **Seed data:** Run `python seed.py`, verify 5 stations, 15+ vehicles, 8+ bookings created
2. **Allocation correctness:** Use demo controls to add emergency bus, verify it gets reserve power and higher rank
3. **Simulation:** Watch a charging bus's battery % increase and eventually complete
4. **Cancellation:** Cancel a charging bus, verify bill adjustment and reallocation of freed power
5. **Fault handling:** Mark station faulty, verify booking blocked and operators see alert
6. **Nearby stations:** With station full or faulty, verify nearby suggestions appear on map
7. **Admin settings:** Change station power, verify reallocation happens
8. **Comparison:** View AMPWISE vs FCFS metrics at a station with mixed emergency/normal buses
9. **Responsive:** Resize browser to mobile width, verify layout adapts
10. **Full demo flow:** Login as operator1 → Dashboard → Book at Coimbatore → Watch charging → Complete → Rate → Login as admin → Trigger emergency → See reallocation → Reset

### End-to-End Demo Script

For the hackathon presentation:
1. Start with admin view showing 5 stations on map
2. Switch to operator, book a bus at Coimbatore (pre-filled vehicle)
3. Show queue with 8 buses, scores, and allocations
4. Admin triggers "Add Emergency Bus" → watch queue reshuffle, reserve allocated
5. Admin triggers "Reduce Capacity" → watch power redistribute, some buses drop to floor
6. Cancel a bus → show bill adjustment
7. Mark station faulty → show alert on operator view, suggest nearby station
8. Show AMPWISE vs FCFS comparison chart
9. Show analytics and rating

---

## Summary of File Counts

| Component | Files | Lines (est.) |
|---|---|---|
| Backend Python | 16 | ~1800 |
| Backend Tests | 2 | ~200 |
| Frontend JSX/JS | 18 | ~2200 |
| Config/Docker/README | 6 | ~200 |
| **Total** | **~42** | **~4400** |

Estimated implementation time: 3–4 hours with parallel subagents.
