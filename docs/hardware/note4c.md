# ZECTRIX NOTE4C DevKit — Hardware & Firmware Reference

Compiled 2026-11-14 from:
- Product page: https://www.zectrix.com/en/note4c.html
- Wiki quick-start: https://wiki.zectrix.com/en/hardware/note4c/quick-start
- Wiki spec: https://wiki.zectrix.com/en/hardware/note4c/spec
- Reference firmware (MIT, branch `2bp`): https://github.com/LazyYoun/youn-ink-fourcolor-firmware/tree/2bp
  - Board dir: `firmware/main/boards/zectrix-s3-epaper-4.2/` (`config.h`, `custom_lcd_display.cc`)

> NOTE4 (mono, 1bpp/4-bit gray) and NOTE4C (4-color) use **different panels/drivers**. Never flash NOTE4C firmware onto a NOTE4 or vice versa.

## Hardware summary

| Item | Value |
|---|---|
| MCU | ESP32-S3 N16R8 (dual-core LX7, 16 MB flash, 8 MB PSRAM) |
| Display | 4.2" E Ink, 400×300, 4 colors: black/white/red/yellow (BWRY) |
| Display controller | SSD2683, SPI, 2 bpp |
| Refresh | Full refresh only, >10 s (up to ~20 s); flicker/inversion during refresh is normal |
| Wireless | 2.4 GHz Wi-Fi, BLE 5.0 |
| Audio | ES8311 codec (I2C), mic, speaker + amp |
| RTC | PCF8563 @ I2C 0x51 (interrupt on GPIO5) |
| NFC | GT23SC6699 @ I2C 0x55 (PCB V1.0) |
| Battery | 2000+ mAh Li-ion, USB-C charging |
| Other | Status LED, 3 buttons + reset pinhole, magnetic back, 97×97×8.75 mm |
| Logic | 3.3 V only — no 5 V on GPIOs |

## GPIO map

| Function | GPIO | Notes |
|---|---|---|
| BOOT / Confirm button | 0 | active low |
| Charge full (STDBY) | 1 | |
| Charging (CHRG) | 2 | low = charging |
| Status LED | 3 | active-low (0 = on). TRMNL fork: blinks 2 Hz while awake; in deep sleep RTC-held on if charging, else off |
| Battery voltage ADC | 4 | |
| RTC INT | 5 | |
| EPD power enable | 6 | high = on (uses `gpio_hold_en`) |
| NFC field detect | 7 | active low |
| EPD BUSY | 8 | **low = busy** (driver waits while level == 0) |
| EPD RST | 9 | |
| EPD DC | 10 | 0 = command, 1 = data |
| EPD CS | 11 | manual GPIO CS (spics_io_num = -1) |
| EPD SCK | 12 | |
| EPD MOSI | 13 | (also used as MISO for 3-wire reads) |
| I2S MCLK | 14 | |
| I2S BCLK | 15 | |
| I2S DIN (codec DOUT → MCU) | 16 | |
| Power hold (VBAT_PWR) | 17 | drive high to stay powered on battery |
| Down / Power button | 18 | active low; also power-on key |
| USB D- / D+ | 19 / 20 | |
| NFC power | 21 | |
| I2S WS/LRCK | 38 | |
| Up button | 39 | active low |
| Audio power enable | 42 | |
| UART0 TX / RX | 43 / 44 | |
| I2S DOUT (MCU → codec) | 45 | |
| Speaker amp enable | 46 | |
| I2C SDA / SCL | 47 / 48 | shared: ES8311, PCF8563, NFC |

Expansion header (3.3 V): 1=3.3V, 2=GND, 3=TX, 4=RX, 5=GPIO, 6=GPIO.

## SSD2683 4-color driver (from reference firmware)

- SPI3_HOST, mode 0, 40 MHz, MOSI-only.
- **Pixel format:** 2 bpp, MSB-first, 4 pixels/byte (pixel 0 in bits 7..6). 100 bytes/row, 30,000 bytes/frame.
- **Color codes:** `0b00` black, `0b01` white, `0b10` yellow, `0b11` red.
  - Solid fills: black `0x00`, white `0x55`, yellow `0xAA`, red `0xFF`.

Sequence (4-color panel):
```
EPD_PWR(GPIO6)=1; delay 10ms
RST=1 10ms, RST=0 20ms, RST=1 10ms
wait BUSY high
CMD 0xE9, DATA 0x01            # init (4-color path stops here; no 0x00 panel-setting cmd)
CMD 0x10 (DTM1); wait BUSY     # then stream 30,000 bytes of 2bpp data (DC=1)
CMD 0x04 (power on); wait BUSY; delay 10ms
CMD 0x12, DATA 0x00 (refresh); delay 10ms; wait BUSY (up to ~120 s timeout)
CMD 0x02, DATA 0x00 (power off); wait BUSY; delay 20ms
CMD 0x07, DATA 0xA5 (deep sleep)
EPD_PWR(GPIO6)=0
```

## Build / flash

- Framework: ESP-IDF (docs say v6.0). Kconfig: `CONFIG_ZECTRIX_EPD_PANEL_4COLOR_SSD2683=y`.
```
idf.py set-target esp32s3
idf.py menuconfig   # ZecTrix EPD panel type -> 4-color BWRY SSD2683 EPD
idf.py build
idf.py -p <PORT> flash monitor
```
- Flash merged binary: `python3 -m esptool --chip esp32s3 --port <PORT> --baud 460800 write-flash 0x0 <fw>.bin`
- **Back up the full 16 MB flash first:** `python3 -m esptool --chip esp32s3 --port <PORT> read-flash 0 0x1000000 backup.bin`
- Download mode: hold BOOT, tap RESET, release BOOT. Use a data USB-C cable.
- Stock merged image: `notellm-2bp-v6.5.9-2bp-3fbbabb-20260705-mergebin.bin` (3,054,752 B, SHA-256 `26f209f7cdea8f62bff73f2e877e3ab421917c17497a2a23340129c6ef43fc36`). Browser updater: https://zectrix.com/en/firmware-updater.html
  - Download URLs, checksum and flashing notes: [docs/flashing.md](../flashing.md#stock-firmware).
- Keep your factory flash backup **outside the repo** (it can contain Wi-Fi credentials and device keys).

Reference partition table (16 MB): nvs 0x9000/0x4000, otadata 0xd000/0x2000, phy_init 0xf000/0x1000, ota_0 0x20000/0x3f0000, ota_1 /0x3f0000, assets (spiffs) 0x800000/8M.

## Stock firmware behavior (reference fw)

- Wi-Fi provisioning: hold Up+Down ~1 s → join open `ZecTrix...` AP → http://192.168.4.1 (2.4 GHz only).
- Gallery upload: hold BOOT on Gallery page → join `InkScreen-AP` (pw `12345678`) → http://192.168.4.1.
- LAN service: enable in Settings, browse to IP shown on screen.
- Companion server (`server/` in repo, Python): HTTP on 8766, e.g.
  `curl -X POST http://host:8766/api/upload_image -F image=@photo.jpg -F format=bwry2bpp -F title=...`
  Formats: `bwry2bpp` (4-color) or 1bpp. UDP discovery also on 8766.

## Stock firmware on-device HTTP API (LAN / AP mode)

Source: `docs/LAN_PHOTO_PUSH_API.md` and `firmware/main/ui/renderers/rawdraw/ap_transfer_server.cc` in the reference repo.
The same `esp_http_server` runs in AP mode (192.168.4.1) and LAN mode (the device's station IP; it starts automatically when Wi-Fi connects). It has no authentication.

| Method | Path | Body / query | Notes |
|---|---|---|---|
| GET | `/` | — | Upload/management HTML page. Browser JS does resize, Floyd–Steinberg dither and packing. |
| GET | `/status` | — | `{"status":"ready","mode":"lan"\|"ap","ip":...,"url":...}` |
| POST | `/upload?format=bwry2bpp` | raw `application/octet-stream`, exactly 30000 B | also `format=1bpp` (15000 B). Returns `{"success":true,"id":"..."}` |
| GET | `/photos` | — | list `{id,title,date,location,body,width,height,size,format}` |
| GET | `/photo?id=` | — | raw bin |
| DELETE | `/photo?id=` | — | |
| POST | `/photo/meta` | JSON `{id,title,date,location,body}` | |
| POST | `/photos/move` | JSON `{id,delta:±1}` | reorder |
| POST | `/photo/show` | JSON `{id}` | display that photo full-screen now |
| GET/POST | `/settings` | JSON `{slideshow_interval:0\|5\|10\|30, service_enabled, wifi_enabled, sleep}` | |

- Storage: SPIFFS `assets` partition (8 MB), max **50** photos (`PHOTO_MAX_PHOTOS`).
- Converter: `docs/inkscreen_image_converter.js` uses the palette black (0,0,0), white (255,255,255), red (255,0,0), yellow (255,255,0), weighted RGB distance and Floyd–Steinberg dithering. Its CLI uses `sharp`.
- Power: deep sleep is skipped while the LAN service is running or the slideshow is on. Deep sleep wakes **only on BOOT (ext0)**, with no timer wake, so the stock firmware cannot do a sleep → wake → fetch → sleep loop.
- `common/photo_downloader.cc` (pulls `GET /api/photos`, `/api/photos/{id}.bin` from a server) is never called and handles 1bpp only.
- The Python `server/` from the README (`llmserve.py`, `push_image.py`) is **not in the public repo**. Only `server/mock_client.py` is published.

## Other resources

- Wiki home: https://wiki.zectrix.com/en/home (community firmware: `/en/software/Community-OpenSource-Firmware`, cloud API: `/en/software/api-docs`)
- NOTE4 mono EPD demo (useful patterns, different panel): https://github.com/itopinion/zectrix-note4-epd-demo
- Datasheets: ESP32-S3 https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf · PCF8563 https://www.nxp.com/docs/en/data-sheet/PCF8563.pdf · ES8311 https://www.everest-semi.com/pdf/ES8311%20PB.pdf
- Discord: https://discord.gg/4u4jcXR3jK
