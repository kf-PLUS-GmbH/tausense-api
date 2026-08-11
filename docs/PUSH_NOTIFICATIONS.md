# Firebase Push Notifications

This backend sends ice-warning push notifications through Firebase Cloud Messaging (FCM).

## Required environment variables

Add these values to your `.env` file:

```env
FIREBASE_ENABLED=true
FIREBASE_SERVICE_ACCOUNT_PATH=C:/path/to/firebase-service-account.json
TEST_PUSH_ENABLED=false
TEST_PUSH_SECRET=
```

Alternative to `FIREBASE_SERVICE_ACCOUNT_PATH`:

```env
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
```

| Variable | Required | Description |
|---|---|---|
| `FIREBASE_ENABLED` | No | Default `true`. Set `false` to disable Firebase initialization. |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | One of two | Full Firebase service account JSON as a single-line string. |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | One of two | Filesystem path to the service account JSON file. |
| `TEST_PUSH_ENABLED` | No | Default `false`. Set `true` to enable `POST /api/test/push/`. |
| `TEST_PUSH_SECRET` | No | Optional secret header for the test endpoint. |

Never commit service account files or `.env` to git.

## Firebase setup steps

1. Open [Firebase Console](https://console.firebase.google.com/) and create or select your project.
2. Add your Android and/or iOS Flutter app to the Firebase project.
3. In Firebase Console go to **Project settings → Service accounts**.
4. Click **Generate new private key** and download the JSON file.
5. Store the file outside the repository, for example:

   ```text
   C:/secrets/taupunktsensorik-firebase.json
   ```

6. Set the path in `.env`:

   ```env
   FIREBASE_SERVICE_ACCOUNT_PATH=C:/secrets/taupunktsensorik-firebase.json
   ```

7. Install backend dependencies:

   ```bash
   pip install -r requirements.txt
   ```

8. Run migrations:

   ```bash
   python manage.py migrate
   ```

9. Start the backend and verify startup log:

   ```text
   INFO devices.firebase_app Firebase Admin SDK initialized successfully.
   ```

If credentials are missing, push sending is skipped and errors are logged.

## Alert preferences

Store or update notification filters for one local app user:

```http
POST /api/v1/alerts/preferences/
Content-Type: application/json
X-User-Id: flutter-install-id
```

```json
{
  "severity_filter": "orange",
  "notifications_enabled": true,
  "selected_municipality": "Hof",
  "selected_sensor_ids": [1, 5, 12]
}
```

You can also send `user_id` in the JSON body instead of the `X-User-Id` header.

| Field | Values | Meaning |
|---|---|---|
| `severity_filter` | `orange`, `red` | `orange` = notify for orange and red alerts; `red` = red only |
| `notifications_enabled` | `true`, `false` | Master switch for remote pushes |
| `selected_municipality` | string or `null` | Municipality-wide subscription |
| `selected_sensor_ids` | integer array | Explicit sensor subscriptions |

Response:

```json
{
  "user_id": "flutter-install-id",
  "severity_filter": "orange",
  "notifications_enabled": true,
  "selected_municipality": "Hof",
  "selected_sensor_ids": [1, 5, 12],
  "created_at": "2026-07-30T09:00:00+02:00",
  "updated_at": "2026-07-30T09:00:00+02:00"
}
```

## Push token registration

Register or update the FCM token for one device:

```http
POST /api/v1/push-tokens/
Content-Type: application/json
```

```json
{
  "user_id": "flutter-install-id",
  "fcm_token": "fcm-device-token-from-flutter",
  "platform": "android"
}
```

Response:

```json
{
  "id": 1,
  "user_id": "flutter-install-id",
  "fcm_token": "fcm-device-token-from-flutter",
  "platform": "android",
  "created_at": "2026-07-30T09:00:00+02:00",
  "updated_at": "2026-07-30T09:00:00+02:00"
}
```

Existing tokens are updated in place when the same `fcm_token` is sent again.

### Subscription rules

A user receives alerts when all of the following are true:

- `notifications_enabled=true`
- the alert color matches `severity_filter`
- the sensor is in `selected_sensor_ids`, or its municipality name matches, or its `operator_name` matches `selected_municipality`

Favorites and municipality/operator filters are combined with **OR** logic.

If both `selected_sensor_ids` and `selected_municipality` are empty, no automatic alerts are sent.

All registered devices (`push_tokens`) for the same `user_id` receive the push.

Legacy endpoint still available for older clients:

```http
POST /api/devices/register/
```

## Automatic push triggering

After each webhook ingestion (`POST /api/webhook/`), the backend:

1. evaluates the ice warning level for the new reading
2. compares it with the previous reading
3. sends a push when a **new warning** appears or the warning **escalates**
4. finds matching device tokens
5. sends FCM messages to all matching devices

No push is sent when:

- the warning level stays the same
- the warning is cleared (`none`)
- the warning is downgraded

## Push payload

Function: `send_push_notification()`

Data payload sent to Flutter:

```json
{
  "sensor_id": "5",
  "alert_status": "red",
  "sensor_name": "B173 Hof Nord",
  "municipality_name": "Hof",
  "title": "Warnung: B173 Hof Nord",
  "body": "Akute Eisbildung wahrscheinlich"
}
```

The message also includes a notification payload with `title` and `body` so Android/iOS can display it when the app is in the background.

### Manual push testing

List registered tokens and preferences:

```bash
python manage.py trigger_test_alert_push --list
```

This also prints current sensor alert status counts and lists **green sensors**
with ready-to-copy `--simulate` commands for push testing.

Send a direct test push to all registered devices (ignores preference filters):

```bash
python manage.py trigger_test_alert_push --broadcast red
python manage.py trigger_test_alert_push --broadcast green
python manage.py trigger_test_alert_push --all-colors
```

Simulate a real frost reading and trigger the normal push flow:

```bash
python manage.py trigger_test_alert_push --simulate acute_ice
```

Limit to one app user:

```bash
python manage.py trigger_test_alert_push --broadcast red --user-id flutter-install-id
```

## Test endpoint

Enable locally:

```env
TEST_PUSH_ENABLED=true
```

Then send:

```http
POST /api/test/push/
Content-Type: application/json
```

```json
{
  "device_token": "fcm-device-token-from-flutter",
  "sensor_id": 5,
  "alert_status": "red",
  "sensor_name": "B173 Hof Nord",
  "municipality_name": "Hof",
  "title": "Test Warnung",
  "body": "Akute Eisbildung wahrscheinlich"
}
```

Alternative for production-like environments:

```http
POST /api/test/push/
X-Test-Push-Secret: your-secret
Content-Type: application/json
```

Example with curl:

```bash
curl -X POST http://localhost:8000/api/test/push/ \
  -H "Content-Type: application/json" \
  -H "X-Test-Push-Secret: your-secret" \
  -d "{\"device_token\":\"TOKEN\",\"sensor_id\":5,\"alert_status\":\"red\",\"sensor_name\":\"Test Sensor\",\"municipality_name\":\"Hof\",\"title\":\"Test\",\"body\":\"Testnachricht\"}"
```

## Logging

The backend logs:

- successful push delivery with message id
- Firebase errors
- invalid/unregistered tokens (token is removed from `push_tokens`)

Logger name: `devices`

Example log lines:

```text
INFO devices.services.push Push sent successfully to abcd1234...xyz (sensor_id=5, alert_status=red, message_id=...)
WARNING devices.services.push Invalid FCM token removed: abcd1234...xyz
ERROR devices.services.push Firebase error while sending push to abcd1234...xyz: ...
```

## Database tables

### `alert_preferences`

| Field | Type | Description |
|---|---|---|
| `user_id` | string | Local app user identifier |
| `severity_filter` | string | `orange` or `red` |
| `notifications_enabled` | bool | Master switch |
| `selected_municipality` | string/null | Municipality subscription |
| `selected_sensor_ids` | JSON array | Sensor subscriptions |

### `push_tokens`

| Field | Type | Description |
|---|---|---|
| `user_id` | string | Local app user identifier |
| `fcm_token` | string | Unique Firebase device token |
| `platform` | string | `android` or `ios` |
| `created_at` | datetime | First registration |
| `updated_at` | datetime | Last update |

## Flutter integration checklist

1. Request notification permission in Flutter.
2. Read the FCM device token from Firebase Messaging.
3. Call `POST /api/v1/push-tokens/` on app start and whenever the token refreshes.
4. Call `POST /api/v1/alerts/preferences/` whenever the user changes filters in the app.
5. Handle incoming data payload in Flutter to navigate to the sensor detail screen.
