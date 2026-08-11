# Taupunktsensorik API Backend

Minimal, API-first Django backend for Smart City IoT sensor data in Landkreis Hof.

## Stack

- Django 5
- Django REST Framework
- drf-spectacular (OpenAPI 3)
- PostgreSQL (per `RELEASE_MODE`)

## Project apps

- `municipalities`
- `sensors`
- `readings`
- `alerts`
- `core` (utils/services/api wiring)

## Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

## Environment / database modes

Copy `.env.example` to `.env` and set values (never commit `.env`).

Required in `.env`:

- `SECRET_KEY` — generate with:
  `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
  If the key contains special characters (`#`, `$`, `!`, …), wrap it in double quotes in `.env`:
  `SECRET_KEY="your-key-here"`
- PostgreSQL variables for your active `RELEASE_MODE`

`RELEASE_MODE` selects which PostgreSQL block is used:

| Mode | Purpose |
|---|---|
| `dev_local` | Your local PostgreSQL (`POSTGRES_*_DEV_LOCAL`) |
| `testing` | Shared test server (`POSTGRES_*_TESTING` or legacy `POSTGRES_*`) |
| `release` | Production (`POSTGRES_*_RELEASE`) |

Example:

```env
RELEASE_MODE=testing
POSTGRES_DB_TESTING=taupunktsensorik
POSTGRES_HOST_TESTING=192.168.2.110
...
```

Switch locally:

```env
RELEASE_MODE=dev_local
```

`DEBUG` defaults to `true` for `dev_local`/`testing` and `false` for `release`.

## Sensor metadata import

Sensor master data (operator, display name, location description, coordinates, what3words)
belongs to `Sensor`, not `SensorReading`.

The importer supports `.xlsx`, `.csv` and `.tsv`. Expected Excel headers:

```text
Standortbezeichnung	Kommune	Name	Standort (Adresse)	Standort (GPS/ W3W)
```

Then import:

```bash
python manage.py import_sensor_metadata path/to/sensors.xlsx
```

The command matches by `device_name`. If a sensor was imported before the first webhook,
the first webhook later attaches `deviceEui` to the same sensor via `Sensor.external_id`.

## Webhook (data ingestion)

`POST /api/webhook/`

Receives LoRaWAN payloads and writes `SensorReading` rows to the database.

Mapping:

| Payload field | Database |
|---|---|
| `deviceEui` | `Sensor.external_id` |
| `deviceName` | `Sensor.name` and `SensorReading.device_name` |
| `timestamp` / fallback `rxTime` | `SensorReading.timestamp` |
| `air_temperature_radiation_shield` | `air_temperature_radiation_shield` and normalized `air_temperature` |
| `air_temperature` | `air_temperature_unshielded` |
| `air_humidity_radiation_shield` | `air_humidity_radiation_shield` and normalized `humidity` |
| `air_humidity` | `air_humidity_unshielded` |
| `surface_temperature` | normalized `road_temperature` |
| `dew_point` | `reported_dew_point` (API `dew_point` is computed) |
| `angle`, `sensor_temperature`, `battery_voltage` | same named structured fields |
| `lat`, `lon` | reading coordinates and sensor coordinates |
| full JSON body | `raw_data` |

Unknown sensors are auto-created **without** municipality assignment when `WEBHOOK_AUTO_CREATE_SENSOR=true`. Gemeinde kann später im Admin zugeordnet werden.

Example:

```bash
curl -X POST http://localhost:8000/api/webhook/ \
  -H "Content-Type: application/json" \
  -d "{\"deviceEui\":\"70B3D57BA000638D\",\"deviceName\":\"MUB-TPK-0001\",\"timestamp\":\"2026-06-03T09:10:06.316Z\",\"air_temperature_radiation_shield\":12.84,\"air_humidity_radiation_shield\":83.77,\"surface_temperature\":24.8,\"lat\":50.22764,\"lon\":11.76708}"
```

## API

Base path: `/api/v1/`

### Sensors

- `GET /api/v1/sensors/`
- `GET /api/v1/sensors/{id}/`
- Filters: `municipality`, `active`, `sensor_type`

### Readings

- `GET /api/v1/readings/`
- `GET /api/v1/readings/latest/`
- `GET /api/v1/readings/history/?sensor=<id>&days=7` — chart data (1–14 days, ascending timestamps)
- Filters: `sensor`, `municipality`, `from`, `to`

### Municipalities

- `GET /api/v1/municipalities/`
- `GET /api/v1/municipalities/{id}/`

### Alerts

- `GET /api/v1/alerts/rules/`
- `GET /api/v1/alerts/events/`

### Dashboard

- `GET /api/v1/dashboard/warnings/`
- `GET /api/v1/dashboard/coldest-sensor/`
- `GET /api/v1/dashboard/map-data/`

Ice warning levels on map data are computed from the latest reading per sensor:

| Level | Label | Criteria |
|---|---|---|
| `none` | Keine Warnung | Normal conditions |
| `possible_slip` | Mögliche Rutschgefahr | Road ≤ 2 °C and \|road − dew point\| ≤ 2 °C |
| `increased_ice` | Erhöhte Eisgefahr | Road ≤ 1 °C and \|road − dew point\| ≤ 1 °C, or humidity ≥ 90 % with road ≤ 1.5 °C |
| `acute_ice` | Akute Eisbildung wahrscheinlich | Road ≤ 0 °C and \|road − dew point\| ≤ 0.5 °C |

`alert_status` maps to map colors: `green`, `yellow`, `orange`, `red`.
Dew point is computed from air temperature and humidity (Magnus formula).

Incremental map sync:

```http
GET /api/v1/dashboard/map-data/?since=2026-06-10T07:45:42Z
```

The response only contains sensors whose metadata or latest reading changed after `since`.
Every response includes `X-Sync-Timestamp`; Flutter can store that value and send it as
the next `since` parameter.

### Push notifications

- `POST /api/v1/alerts/preferences/` — store alert filter preferences per app user
- `POST /api/v1/push-tokens/` — register FCM device token
- `POST /api/test/push/` — send a test push to one device

See [docs/PUSH_NOTIFICATIONS.md](docs/PUSH_NOTIFICATIONS.md) for Firebase setup, environment
variables and example requests.

## OpenAPI

- Schema: `/api/schema/`
- Swagger UI: `/api/docs/swagger/`
- ReDoc: `/api/docs/redoc/`

This schema is designed to be consumed by Flutter client generators.
