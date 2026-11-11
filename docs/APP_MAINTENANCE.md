# App-weiter Wartungshinweis (Admin → Flutter)

## Admin

Im Django-Admin: **App-Wartungshinweis** (ein Eintrag, Singleton).

| Feld | Bedeutung |
|------|-----------|
| **Aktiv** (`enabled`) | Hinweis grundsätzlich eingeschaltet |
| **Titel** | Kurzzeile, z. B. „Wartungsarbeiten“ |
| **Nachricht** | Freitext für Nutzer (Deutsch) |
| **Start / Ende** | Optional; ohne Start = sofort (wenn aktiv); ohne Ende = offen |

**Nicht verwechseln** mit `Sensor.maintenance_mode` (nur ein Sensor auf der Karte).

## API

`GET /api/v1/system/app-maintenance/`  
Öffentlich, keine Auth.

```json
{
  "app_maintenance": {
    "active": true,
    "state": "active",
    "title": "Wartungsarbeiten",
    "message": "Heute 22–24 Uhr können Daten verzögert sein.",
    "starts_at": "2026-11-11T20:00:00+00:00",
    "ends_at": "2026-11-11T23:00:00+00:00",
    "updated_at": "2026-11-11T18:30:00+00:00"
  }
}
```

### `state`

| Wert | `active` | UI-Empfehlung |
|------|----------|----------------|
| `inactive` | false | Kein Banner (`enabled` aus) |
| `scheduled` | false | Optional: Info „ab …“ (Vorschau) |
| `active` | true | **Banner anzeigen** (title + message) |
| `ended` | false | Banner aus (Zeitfenster vorbei, Admin kann `enabled` ausmachen) |

Zeiten sind **ISO 8601** (meist UTC mit Offset); in der App lokal formatieren.

## Flutter

1. **Abruf:** Beim App-Start und z. B. alle **15–30 Minuten** (oder bei Resume) `GET …/system/app-maintenance/`.
2. **Banner**, wenn `app_maintenance.active == true`:
   - Titel = `title`
   - Text = `message`
   - Optional Unterzeile aus `starts_at` / `ends_at` (lokal formatiert)
3. **Optional** bei `state == scheduled`: dezenter Hinweis „Geplant ab …“.
4. **Kein Blockieren** der App nötig – nur Transparenz; Map-API läuft weiter (Hard-Block später möglich, derzeit nicht im Backend).
5. Bei API-Fehler: Banner nicht anzeigen / letzten Stand behalten (kurze TTL).

Deploy Backend: `python manage.py migrate` (Migration `core.0001_app_maintenance_settings`).
