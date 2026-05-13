# Taupunktsensorik API Backend

Minimal, API-first Django backend for Smart City IoT sensor data in Landkreis Hof.

## Stack

- Django 5
- Django REST Framework
- drf-spectacular (OpenAPI 3)
- PostgreSQL (production) / SQLite (development)

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

## Environment (optional PostgreSQL)

If these variables are provided, PostgreSQL is used:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

Otherwise SQLite is used.

## API

Base path: `/api/v1/`

### Sensors

- `GET /api/v1/sensors/`
- `GET /api/v1/sensors/{id}/`
- Filters: `municipality`, `active`, `sensor_type`

### Readings

- `GET /api/v1/readings/`
- `GET /api/v1/readings/latest/`
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

## OpenAPI

- Schema: `/api/schema/`
- Swagger UI: `/api/docs/swagger/`
- ReDoc: `/api/docs/redoc/`

This schema is designed to be consumed by Flutter client generators.
