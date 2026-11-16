# Device ↔ server API

The firmware (`firmware/trmnl`) speaks the TRMNL device API. LaraPaper implements it today; our
own server must implement the same endpoints, or we change both sides in one PR. This file is
that contract. It describes what our firmware actually sends, from `firmware/trmnl/src/api-client/`
and `lib/trmnl/src/`.

Base URL: the "API Server" set in the captive portal, e.g. `https://eink.example.com`.

## `GET /api/setup`: first boot / pairing

| Request header | Value |
|---|---|
| `ID` | Wi-Fi MAC address |
| `FW-Version`, `Model` | firmware version, `zectrix_note4c` |

Response `200`: `{"status": 200, "api_key": "...", "friendly_id": "...", "image_url": "...", "filename": "..."}`.
The device stores `api_key` in NVS and uses it from then on.
LaraPaper only answers for new devices, or for known ones while **Permit Auto-Join** is on. Otherwise it returns `404`.

## `GET /api/display`: every wake

| Request header | Value |
|---|---|
| `ID` | MAC address |
| `Access-Token` | the `api_key` from setup (this is the device's authentication) |
| `Refresh-Rate` | current sleep interval, seconds |
| `Battery-Voltage`, `Percent-Charged`, `Battery-Charging`, `USB-Connected` | power state |
| `RSSI`, `WiFi-Band` | Wi-Fi signal |
| `FW-Version`, `FW-Commit`, `Model`, `Width` (400), `Height` (300) | device info |
| `Image-Cached`, `Wake-Time`, `Update-Source`, `Temperature-Profile` | misc |
| `SENSORS` | optional sensor readings |

Response JSON (fields the firmware reads):

| Field | Meaning |
|---|---|
| `status` | `0` = OK |
| `image_url` | PNG/BMP to download and show, 400×300 |
| `filename` | the image's identity; unchanged = skip the download (saves battery) |
| `refresh_rate` | seconds until the next wake |
| `update_firmware`, `firmware_url` | OTA. **Keep `false`**: stock TRMNL firmware would replace this fork |
| `reset_firmware`, `special_function`, `action`, `image_url_timeout`, `maximum_compatibility`, `temperature_profile`, `touchbar_mode` | rarely used |

**Image format.** A PNG that uses only the exact panel colours displays 1:1: black `#000`,
white `#fff`, yellow `#ff0`, red `#f00`. The firmware maps each pixel to the nearest of these
four colours.

## `POST /api/log`: device logs

JSON body with log entries. Same `ID` / `Access-Token` headers.

## Images

The `image_url` is downloaded with a plain GET and no auth headers. LaraPaper serves generated
screens under `/storage/images/...` with random file names.

## Transport notes

- **HTTPS without certificate checks.** The firmware's HTTPS client calls `setInsecure()`
  (`lib/trmnl/include/http_client.h`), so traffic is encrypted but the server certificate is not
  verified. Any certificate works (Let's Encrypt, Cloudflare), but anyone able to intercept the
  connection could impersonate the server and read the `Access-Token`. A future firmware change could
  pin the root CA, e.g. ISRG Root X1 for Let's Encrypt.
- Each wake makes one TLS handshake. That adds roughly 0.5 s of awake time compared with plain HTTP on the LAN.

## Data for the screen (not part of the device API)

Senders push data to the server, and the server renders it into the image above:

- **LaraPaper:** `POST /api/custom_plugins/<plugin-uuid>` with
  `{"merge_variables": {...}, "merge_strategy": "deep_merge"}`. Public deployments also require
  `Authorization: Bearer <token>`, which the Caddy proxy checks.
- The shape of `merge_variables`: [`schema/dashboard.schema.json`](../schema/dashboard.schema.json).
