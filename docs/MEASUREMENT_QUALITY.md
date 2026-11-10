# Messqualität & Map-API (Frontend)

## Konfiguration (Backend `.env`)

Grenzwerte für plausibel / nicht plausibel (Standard Boden −50 °C):

| Variable | Standard | Bedeutung |
|----------|----------|-----------|
| `READING_ROAD_TEMP_MIN` | `-50` | Mindest-Fahrbahntemperatur °C |
| `READING_ROAD_TEMP_MAX` | `60` | Maximum Fahrbahn °C |
| `READING_AIR_TEMP_MIN` | `-50` | Mindest-Luft °C |
| `READING_AIR_TEMP_MAX` | `50` | Maximum Luft °C |
| `READING_HUMIDITY_MIN` | `0` | Mindest-Luftfeuchte % |
| `READING_HUMIDITY_MAX` | `100` | Maximum Luftfeuchte % |

Nach Änderung der Werte: Server neu starten (Gunicorn).

## `GET /api/v1/dashboard/map-data/`

Pro Sensor **neu** (zusätzlich zu den bisherigen Stammdaten):

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `measurement_status` | `"ok"` \| `"unreliable"` \| `"maintenance"` | Steuert Banner / Marker-Logik |
| `status_message` | `string` \| `null` | Deutsch, nur wenn nicht `ok` |
| `display_reading` | Objekt \| `null` | Nur bei `measurement_status` ≠ `"ok"` (sonst `null`, Anzeige aus `latest_reading`) |
| `latest_reading.is_plausible` | `boolean` | Ob der Roh-Messwert in den Grenzen liegt |
| `alert_status` | … \| **`"gray"`** | Grau bei Wartung oder ohne anzeigbare Werte |

`latest_reading` enthält weiterhin die **letzte gespeicherte** Zeile (inkl. kaputter Werte).

`display_reading` hat dieselben Felder wie `latest_reading` plus:

| Feld | Beschreibung |
|------|--------------|
| `is_stale` | `true`, wenn `display_reading` älter ist als `latest_reading` (weil latest unplausibel) |

### UI-Empfehlung (Flutter)

1. **Temperaturen / Trend / Taupunkt:** `display_reading ?? latest_reading` (bei `ok` ist `display_reading` immer `null`).
2. **Marker-Farbe:** `alert_status` (bei `gray` neutraler Marker, kein Warn-Rot).
3. **Banner:** wenn `status_message != null`, Text anzeigen.
4. **Wartung:** `measurement_status == "maintenance"` → Meldung „Sensor gerade in Wartung“ (`status_message`).
5. **Unplausibel:** `measurement_status == "unreliable"` → ggf. veralteten Wert mit Hinweis (`is_stale == true`).

### Beispiel unreliable

```json
{
  "measurement_status": "unreliable",
  "status_message": "Aktueller Messwert nicht plausibel",
  "alert_status": "yellow",
  "latest_reading": {
    "road_temperature": -100.0,
    "is_plausible": false,
    "timestamp": "2026-11-05T12:00:00Z"
  },
  "display_reading": {
    "road_temperature": 2.1,
    "is_plausible": true,
    "is_stale": true,
    "timestamp": "2026-11-05T11:45:00Z"
  }
}
```

### Beispiel maintenance (Admin: Sensor → `maintenance_mode`)

```json
{
  "measurement_status": "maintenance",
  "status_message": "Sensor gerade in Wartung",
  "alert_status": "gray",
  "ice_warning_level": "none",
  "display_reading": { "...": "letzter plausibler Wert, wenn ≠ latest" }
}
```

Bei Wartung mit plausibelem `latest_reading` kann `display_reading` **`null`** sein – Werte dann aus `latest_reading`.

## Backend-Verhalten (kurz)

- Unplausible Webhooks werden **gespeichert**, setzen `is_plausible=false`.
- **Keine** Aktualisierung der gespeicherten Glättewarnstufe und **keine** Push-Benachrichtigung bei unplausiblen Messungen.
- „Kältester Sensor“ (`/dashboard/coldest-sensor/`) nutzt nur plausibele Messungen.
