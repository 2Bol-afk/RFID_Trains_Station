# API reference

The `cards` URL configuration is mounted at both `/` and `/api/`. This document uses `/api/` as the canonical API prefix. Browser-oriented pages use the shorter root routes documented in the README.

## Authentication

| Access label | Requirement |
|---|---|
| Public | No authenticated Django user required |
| Cashier/Admin | Authenticated user in `cashier` or `admin`, or a staff user where allowed by `IsCashierOrAdmin` |
| Admin | Authenticated admin-group, staff, or superuser account as implemented by `IsAdminOnly` |
| Bridge or authenticated | Valid `X-BRIDGE-TOKEN` header or any authenticated Django user |

Session and Basic authentication are enabled globally. Purchase, reload, ride, status, fare-category, and passenger-information mutation views use the project's CSRF-exempt session-authentication class; this is a local-demo behavior and should be changed for production.

Amounts are represented as decimal strings in DRF model responses.

## Card endpoints

### Purchase a card

`POST /api/cards/purchase/` — Cashier/Admin

```json
{
  "uid": "CARD-1001",
  "initial_amount": "200.00",
  "passenger_name": "Demo Passenger",
  "passenger_email": "demo.passenger@example.com",
  "fare_category": "student"
}
```

`initial_amount` must be `100.00`, `200.00`, or `300.00`. `fare_category` must be `regular`, `student`, `senior`, or `pwd`. A successful request returns the created card with HTTP 201. Duplicate UIDs and invalid fields return HTTP 400.

### Reload a card

`POST /api/cards/{uid}/reload/` — Cashier/Admin

```json
{"amount": "50.00"}
```

The amount must be positive and the card must be active. Success returns the updated card. Invalid amounts or inactive/missing cards currently return HTTP 400.

### Charge a ride

`POST /api/cards/{uid}/ride/` — Bridge or authenticated

```json
{"station_id": 1}
```

`station_id` is optional on this endpoint. An active station supplies its configured fare; otherwise the default `RIDE_COST` is used. The card's fare category is applied before the balance check. Missing cards, inactive cards, and insufficient balances return HTTP 400.

The hardware bridge may authenticate this POST with:

```http
X-BRIDGE-TOKEN: configured-shared-secret
```

### Change card status

`POST /api/cards/{uid}/status/` — Admin

```json
{
  "status": "lost",
  "note": "Reported at Central Station"
}
```

Valid states are `active`, `deactivated`, and `lost`. A neutral audit transaction records meaningful transitions.

### Change fare category

`POST /api/cards/{uid}/fare-category/` — Cashier/Admin

```json
{"fare_category": "senior"}
```

Using `regular` clears the discount relationship. The current service records the change as a neutral transaction using the existing `reactivate` type.

### Update passenger summary

`POST /api/cards/{uid}/update/` — Cashier/Admin

```json
{
  "passenger_name": "Updated Demo Passenger",
  "passenger_email": "updated.passenger@example.com"
}
```

Both fields are required. A neutral audit entry records the update.

### Card detail

`GET /api/cards/{uid}/` — Cashier/Admin

Returns card status, balance, passenger summary, fare category, creator, usability flag, and transaction history. Missing cards return HTTP 404.

### Card balance

`GET /api/cards/{uid}/balance/` — Cashier/Admin

```json
{
  "uid": "DEMO001",
  "balance": "140.00",
  "status": "active",
  "can_be_used": true,
  "fare_category": null
}
```

The bridge token alone does not currently authorize this preliminary balance endpoint.

### List cards

`GET /api/cards/` — Admin

Optional query parameters:

- `status`: exact card status.
- `search`: case-insensitive UID substring.

The response is limited to the 100 newest matching cards.

## Public passenger demo endpoints

These routes exist for the browser-based tap demonstration and should be secured or removed from a public deployment.

| Method | Route | Behavior |
|---|---|---|
| `GET` | `/api/public/cards/{uid}/balance/` | Returns balance, status, fare category, and usability |
| `GET` | `/api/public/cards/{uid}/transactions/` | Returns the ten newest card transactions |
| `POST` | `/api/public/cards/{uid}/ride/` | Charges a ride; an active `station_id` is required |
| `POST` | `/api/clear-passenger-session/` | Clears the passenger-interface logout notice flag |

Public ride request:

```json
{"station_id": 1}
```

## Activity, reports, and health

### Recent cashier activity

`GET /api/recent-transactions/` — Cashier/Admin

Returns the ten newest non-ride transactions.

### JSON reports

`GET /api/reports/data/?type=summary` — Cashier/Admin

Supported types:

- `summary`: card counts, purchase/reload/ride totals, averages, and transaction counts.
- `revenue`: 30-day daily breakdown and period totals.
- `cards`: status, balance distribution, active-card ranking, and recent activity.

Invalid types return HTTP 400. The HTML report interface remains at `/api/reports/` or the canonical browser route `/reports/`.

### System health

`GET /api/health/` — Admin

```json
{
  "status": "healthy",
  "total_cards": 3,
  "active_cards": 2,
  "total_transactions": 8,
  "negative_balance_cards": 0,
  "ride_cost": 20.0,
  "bridge_token_configured": true
}
```

The status changes to `warning` when negative-balance cards exist. This is an application-data check, not a full infrastructure readiness probe.

## Common card response fields

```json
{
  "uid": "DEMO001",
  "balance": "140.00",
  "status": "active",
  "status_display": "Active",
  "passenger_name": "Alex Rivera",
  "passenger_email": "alex.rivera@example.com",
  "fare_category": null,
  "created_at": "2026-08-08T01:44:00Z",
  "updated_at": "2026-08-08T01:44:00Z",
  "created_by_username": "demo",
  "can_be_used": true,
  "recent_transactions": []
}
```

Exact timestamps and transaction arrays depend on current data.
