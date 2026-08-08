# RFID hardware bridge

`rfid_station/rfid_bridge.py` connects a serial/USB RFID reader to the Django ride endpoint. It is a standalone Python process and does not need to run on the Django server host.

## Expected reader behavior

The bridge opens a serial port and reads newline-terminated UTF-8 text. Each non-empty line is stripped and treated as a complete card UID.

Example reader output:

```text
04A1B2C3D4
```

The repository does not include RFID reader firmware, a hardware wiring diagram, or support for binary reader protocols. Readers that emulate a keyboard are not supported by the current command-line implementation.

## Install and configure

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r rfid_station/requirements.txt

export RFID_BRIDGE_TOKEN='replace-with-a-strong-shared-secret'
```

Configure the same token in the Django server environment. Do not use the checked-in development fallback for a shared or public deployment.

## Run

Linux example:

```bash
cd rfid_station
python rfid_bridge.py \
  --serial /dev/ttyUSB0 \
  --baudrate 9600 \
  --api-url http://127.0.0.1:8000 \
  --token "$RFID_BRIDGE_TOKEN"
```

Windows example:

```powershell
python rfid_bridge.py --serial COM3 --baudrate 9600 --api-url http://127.0.0.1:8000 --token $env:RFID_BRIDGE_TOKEN
```

| Option | Default | Meaning |
|---|---:|---|
| `--serial PORT` | Required | Serial device such as `/dev/ttyUSB0` or `COM3` |
| `--baudrate N` | `9600` | Reader serial speed |
| `--api-url URL` | `http://localhost:8000` | Django server base URL |
| `--token TOKEN` | Development fallback | Value sent in `X-BRIDGE-TOKEN` |
| `--ride-cost VALUE` | `20.0` | Stored by the bridge object; the server remains authoritative for charges |

## Request flow

For each UID, the bridge currently:

1. Sends `GET /api/cards/{uid}/balance/`.
2. Logs status, balance, and usability if that request succeeds.
3. Sends `POST /api/cards/{uid}/ride/` with an empty JSON body.
4. Logs the new balance or the API error.

All requests use a `requests.Session` with:

```http
X-BRIDGE-TOKEN: configured-token
Content-Type: application/json
```

The ride POST accepts bridge-token authentication. The preliminary balance GET currently requires a Django-authenticated cashier/admin and therefore normally returns an authorization error to a token-only bridge; the bridge proceeds to the authoritative ride POST when the preflight response is unavailable.

## Fare authority

The Django server determines the fare. Because the bridge sends no station ID, the bridge route uses the configured server-side `RIDE_COST`, then applies the card's fare-category discount. The bridge's `--ride-cost` value does not override the current API calculation.

For station-specific hardware, extend the bridge configuration so each reader sends its assigned `station_id`.

## Logs and device feedback

Logs are written to standard output and `rfid_bridge.log` in the bridge's working directory. Successful and failed charges are logged, but GPIO, gate, buzzer, and display feedback are only extension hooks and are not implemented in this repository.

## Troubleshooting

### Serial port cannot be opened

- Confirm the port name and that the device is connected.
- Confirm no second process has opened the same port.
- On Linux, confirm the service user has permission for the serial device.
- Verify the configured baud rate matches the reader.

### Every ride returns 403

- Confirm Django and the bridge use the same `RFID_BRIDGE_TOKEN`.
- Confirm a proxy forwards the `X-BRIDGE-TOKEN` header.
- Confirm the bridge calls `/api/cards/{uid}/ride/`, not the public simulator route.

### Balance preflight returns 403

This is a current known limitation: the balance endpoint does not accept bridge-token authorization. The ride POST remains the authoritative result.

### Card is rejected

Check the API/log message for a missing UID, inactive/lost status, invalid station, or insufficient discounted balance. Verify the UID emitted by the reader exactly matches the value stored in Django.

### Duplicate charges

The database update is atomic, but the API has no idempotency key. Reader/network retries can create separate valid charges. Production hardware should attach a unique tap identifier and the server should reject repeats.

## Production hardening

- Provision a unique credential for each reader rather than one shared global token.
- Use HTTPS and restrict reader network access.
- Add request signatures or mutual TLS, token rotation, rate limiting, and idempotency.
- Supervise the bridge process and centralize its logs.
- Define offline behavior explicitly; the current bridge does not queue transactions.
- Add physical device feedback only after the API result is confirmed.
