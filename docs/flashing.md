# Flashing the NOTE4C

All commands run from `firmware/trmnl/`. `esptool` ships with PlatformIO:
`~/.platformio/penv/bin/esptool`. The examples use `/dev/ttyACM0`; check yours with
`ls /dev | grep -E 'ttyACM|ttyUSB'`.

If the port doesn't connect, enter download mode: hold **BOOT**, tap **RESET**, release **BOOT**.
Use a USB-C cable that carries data.

## Build

```zsh
pio run -e zectrix_note4c
```

This produces two files in `.pio/build/zectrix_note4c/`. CI uploads both as a build artifact:

| File | Contains | Flash at | Keeps Wi-Fi + pairing? |
|---|---|---|---|
| `firmware.bin` | the app only | `0x20000` | **yes** |
| `merged_firmware.bin` | bootloader + partition table + app, padded with `0xFF` | `0x0` | **no** (padding overwrites NVS) |

## Update the app (normal case)

```zsh
~/.platformio/penv/bin/esptool --chip esp32s3 -p /dev/ttyACM0 -b 460800 write-flash 0x20000 .pio/build/zectrix_note4c/firmware.bin
```

Or `just flash-app` from the repo root.

## First install / full flash

Use this the first time, or when the bootloader or partition table changes:

```zsh
~/.platformio/penv/bin/esptool --chip esp32s3 -p /dev/ttyACM0 -b 460800 write-flash 0x0 .pio/build/zectrix_note4c/merged_firmware.bin
```

This erases the Wi-Fi credentials and the server API key. Afterwards:

1. Set up Wi-Fi again in the captive portal.
2. Re-pair the device: open **Permit Auto-Join** in LaraPaper (Devices page, 15 minutes), then
   press the button. An already-registered device only gets its API key back while Auto-Join is open.

Partition map (`firmware/trmnl/boards/trmnl_x_partitions.csv`): nvs `0xE000`, otadata `0x13000`,
app0 `0x20000`, app1 `0x320000`, spiffs `0x620000`.

## Logs

```zsh
pio device monitor -b 115200
```

## Back up the factory flash first

Before the first flash of a new device, back up the whole flash:

```zsh
~/.platformio/penv/bin/esptool --chip esp32s3 -p /dev/ttyACM0 read-flash 0 0x1000000 note4c-factory.bin
sha256sum note4c-factory.bin > note4c-factory.bin.sha256
```

Keep the backup **outside this repo**: it contains NVS (Wi-Fi credentials) and the device's
factory data. To restore it: `esptool ... write-flash 0 note4c-factory.bin`.

## Stock firmware

This is ZecTrix's "Four-Color Gallery Reference" firmware. It is a vendor binary, so it is not committed.

- File: `notellm-2bp-v6.5.9-2bp-3fbbabb-20260705-mergebin.bin`
- Version: v6.5.9-2bp, commit 3fbbabb. Source:
  https://github.com/LazyYoun/youn-ink-fourcolor-firmware/tree/2bp (MIT)
- Download: https://wiki.zectrix.com/notellm-2bp-v6.5.9-2bp-3fbbabb-20260705-mergebin.bin
  (mirror: https://www.zectrix.com/developer/firmware/note4c-reference.bin)
- Size: 3054752 bytes
- SHA-256: `26f209f7cdea8f62bff73f2e877e3ab421917c17497a2a23340129c6ef43fc36`
- Merged image: flash at `0x0`. **Never flash it onto a monochrome NOTE4.**
- Browser updater: https://zectrix.com/en/firmware-updater.html
