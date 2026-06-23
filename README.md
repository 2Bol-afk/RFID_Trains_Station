# 🚆 RFID Train Station — Card Payment System

> A Django + DRF backend for reloadable RFID transit cards: tap-to-ride fares, cashier/admin workflows, fare discounts, lost-card handling, and live reporting — with a Python bridge that talks directly to a serial RFID reader.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.x-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/REST-Framework-A30000)
![DB](https://img.shields.io/badge/DB-SQLite%20%7C%20PostgreSQL-336791?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📖 Table of Contents

- [How It Works](#-how-it-works)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Data Model](#-data-model)
- [Roles & Access](#-roles--access)
- [API Reference](#-api-reference)
- [Web Interfaces](#-web-interfaces)
- [RFID Bridge](#-rfid-bridge-hardware-side)
- [Fare Logic](#-fare-logic)
- [Deployment Checklist](#-deployment-checklist)

---

## 🧠 How It Works

```
┌──────────────┐      serial/USB      ┌────────────────────┐      HTTPS (token auth)      ┌─────────────────────┐
│  RFID Reader │ ───────────────────▶ │   rfid_bridge.py    │ ────────────────────────────▶ │   Django REST API   │
│  (turnstile) │     UID over line     │  (Python service)   │   POST /api/cards/{uid}/ride │   (cards app)        │
└──────────────┘                      └────────────────────┘                                └─────────┬───────────┘
                                                                                                        │
                                                                          ┌─────────────────────────────┼─────────────────────────────┐
                                                                          ▼                              ▼                             ▼
                                                                  ┌──────────────┐              ┌───────────────┐             ┌────────────────┐
                                                                  │  Cashier UI  │              │  Admin Panel  │             │  Passenger UI  │
                                                                  │ purchase/    │              │ stations,     │             │ check balance, │
                                                                  │ reload cards │              │ users, reports│             │ recent rides   │
                                                                  └──────────────┘              └───────────────┘             └────────────────┘
                                                                                                        │
                                                                                                        ▼
                                                                                              ┌───────────────────┐
                                                                                              │  SQLite/Postgres  │
                                                                                              │ Card · Passenger  │
                                                                                              │ Transaction · ... │
                                                                                              └───────────────────┘
```

1. A passenger taps their card on the **RFID reader** at a turnstile.
2. The reader streams the card's **UID** over serial; [rfid_bridge.py](rfid_bridge.py) reads it line-by-line.
3. The bridge calls `GET /api/cards/{uid}/balance/` to confirm the card can be used, then `POST /api/cards/{uid}/ride/`, authenticated with a shared `X-BRIDGE-TOKEN`.
4. Django deducts the fare **inside a DB transaction with row locking** (no double-charging on concurrent taps), applies any **fare-category discount**, and logs a `Transaction` row.
5. Cashiers use the **Cashier UI** to sell new cards and reload balances; admins use the **Admin Dashboard** / Django Admin to manage stations, fare categories, and pull reports; passengers can self-check balance/history from a public UI.

---

## ✨ Features

| Area | Capability |
|---|---|
| 💳 Cards | Purchase, reload, edit passenger info, all with audit-trail transactions |
| 🚇 Rides | Station-aware fare deduction on tap, concurrency-safe balance updates |
| 🏷️ Discounts | Student (20%), Senior (25%), PWD (20%) — applied automatically at tap time |
| 🔒 Card Lifecycle | Activate / deactivate / mark lost, with neutral audit entries |
| 👥 Roles | `cashier` and `admin` Django groups, plus staff/superuser |
| 📊 Reports | Summary, revenue, and card reports + a system health endpoint |
| 🛠️ Admin | Full Django Admin for Cards, Transactions, Passengers, Stations, Fare Categories |
| 📡 Hardware Bridge | Lean script bridging a serial RFID reader to the API |

---

## 🧰 Tech Stack

- **Django 4.x** + **Django REST Framework**
- **SQLite** for development, **PostgreSQL** recommended for production
- **Python 3.11+**
- **pyserial** + **requests** for the hardware bridge

---

## ✅ Prerequisites

Before you start, make sure you have:

- [ ] **Python 3.11 or newer** ([python.org](https://www.python.org/downloads/))
- [ ] **pip** (ships with Python)
- [ ] **Git** (to clone/manage the repo)
- [ ] *(Production only)* **PostgreSQL** server + connection credentials
- [ ] *(Hardware only)* A **serial/USB RFID reader** and its COM port (e.g. `COM3` on Windows, `/dev/ttyUSB0` on Linux)

---

## 🚀 Installation

### 1. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example env file and fill in your own values — settings are read via `os.environ` in [rfid_station/rfid_station/settings.py](rfid_station/rfid_station/settings.py), so **nothing secret is hardcoded or committed**:

```bash
cd rfid_station
cp .env.example .env   # Windows: copy .env.example .env
```

Then load it before running Django (PowerShell example):

```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([^#=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2]) } }
```

Or use a tool like `django-environ`/`python-dotenv` if you prefer auto-loading.

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django cryptographic key — **always set a real one in production** |
| `DJANGO_DEBUG` | `True`/`False` — must be `False` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated domains/IPs allowed to serve the app |
| `RFID_BRIDGE_TOKEN` | Shared secret the bridge sends as `X-BRIDGE-TOKEN` |
| `RIDE_COST` | Default fare when a station isn't specified |

`DATABASES` still defaults to SQLite for local dev — swap to PostgreSQL in `settings.py` for production.

`.env` is gitignored — never commit it. [.env.example](rfid_station/.env.example) documents the required keys with placeholder values only.

### 4. Initialize the database

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Run the server

```bash
python manage.py runserver
```

🎉 Visit `http://localhost:8000/admin/` to log in as your superuser.

---

## 🗄️ Data Model

```
TrainStation ──┐
               ├──< Transaction >── Card ── FareCategory
Passenger ─────┘                     │
                                      └── created_by ── User
```

- **Card** — UID, balance, status (`active` / `deactivated` / `lost`), linked passenger & fare category.
- **Passenger** — full contact/demographic record (optional link from Card).
- **FareCategory** — `regular`, `student`, `senior`, `pwd`, each with a discount %.
- **TrainStation** — name, code, per-station ride cost.
- **Transaction** — immutable audit log: type (`purchase`/`ride`/`reload`/`deactivate`/`lost`/`reactivate`), direction (`credit`/`debit`/`neutral`), amount, station, actor.

---

## 👤 Roles & Access

| Role | Capabilities |
|---|---|
| **Admin** | Everything — reports, station/fare management, card status changes |
| **Cashier** | Purchase/reload cards, process rides, view balances |

Groups (`cashier`, `admin`) are auto-created on admin app load. Add your staff users to the appropriate group in Django Admin.

---

## 🔌 API Reference

All routes are prefixed with `/api/`.

### Cards (cashier/admin)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/cards/purchase/` | Purchase a new card |
| `POST` | `/cards/{uid}/reload/` | Reload an existing card |
| `POST` | `/cards/{uid}/ride/` | Charge a ride (bridge or authenticated user) |
| `POST` | `/cards/{uid}/status/` | Activate / deactivate / mark lost *(admin only)* |
| `GET` | `/cards/{uid}/` | Full card detail + transactions |
| `GET` | `/cards/{uid}/balance/` | Quick balance check |
| `POST` | `/cards/{uid}/fare-category/` | Update fare category |
| `POST` | `/cards/{uid}/update/` | Update passenger info |

### Public (passenger-facing, no login)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/public/cards/{uid}/balance/` | Public balance check |
| `GET` | `/public/cards/{uid}/transactions/` | Public recent transactions |
| `POST` | `/public/cards/{uid}/ride/` | Public ride charge (station required) |

### Reports & System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/reports/?type=summary\|revenue\|cards` | Operational reports |
| `GET` | `/health/` | System health *(admin only)* |

---

## 🖥️ Web Interfaces

| Interface | Path |
|---|---|
| Cashier UI | `/api/cashier/` |
| Passenger UI | `/api/passenger/` |
| Admin Dashboard (custom) | `/api/admin-dashboard/` |
| Django Admin | `/admin/` |

---

## 📡 RFID Bridge (Hardware Side)

[rfid_bridge.py](rfid_bridge.py) reads card UIDs from a serial RFID reader and posts ride charges to the API.

**Requires:** `pyserial`, `requests` (already in [requirements.txt](requirements.txt))

```bash
python rfid_bridge.py --serial COM3 --api-url http://localhost:8000 --token your-bridge-token --ride-cost 20.0
```

| Flag | Meaning |
|---|---|
| `--serial` | Serial port — `COM3` (Windows) or `/dev/ttyUSB0` (Linux) |
| `--api-url` | Base URL of the Django API |
| `--token` | Must match `RFID_BRIDGE_TOKEN` in settings |
| `--ride-cost` | Fallback fare if the API call doesn't resolve a station |
| `--baudrate` | Serial baud rate (default `9600`) |

The bridge authenticates every request with an `X-BRIDGE-TOKEN` header and logs activity to both the console and `rfid_bridge.log`.

---

## 💰 Fare Logic

- **Concurrency-safe**: balance changes happen inside DB transactions with row-level locking — no race-condition double charges.
- **Discounts** apply automatically at tap time based on the card's `FareCategory`:

  | Category | Discount |
  |---|---|
  | Regular | 0% |
  | Student | 20% |
  | Senior | 25% |
  | PWD | 20% |

- **Lost / deactivated cards** can never be charged — status transitions are recorded as neutral (non-monetary) transactions for the audit trail.

---

## 🛡️ Deployment Checklist

- [ ] `DEBUG = False`, real `ALLOWED_HOSTS`, fresh `SECRET_KEY`
- [ ] Switch `DATABASES` to PostgreSQL, then `migrate` + `collectstatic`
- [ ] Serve over HTTPS with strong admin credentials
- [ ] Rotate to a strong, secret `RFID_BRIDGE_TOKEN`

---

## 📄 License

MIT License.
