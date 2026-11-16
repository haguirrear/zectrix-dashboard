# Firmware

`trmnl/` is the [TRMNL firmware](https://github.com/usetrmnl/firmware) with ZecTrix NOTE4/NOTE4C
support from [LitoMore/trmnl-firmware](https://github.com/LitoMore/trmnl-firmware) (branch
`zectrix`). It is imported as a **git subtree**: the code lives in this repo, so you can make normal
commits that touch firmware and server together, and upstream updates can still be pulled in.
License: GPL-3.0 (`trmnl/LICENSE`).

## Our changes on top of upstream

See `git log -- firmware/trmnl` for the details.

- **Wi-Fi status crash:** `wifiStatusStr()` returned `nullptr` for `WL_STOPPED`.
- **DHCP grace:** if the device is already associated, the connect timeout is extended once by 15 s
  instead of dropping the link. This matters for WPA3-SAE, which is slow on the ESP32-S3.
- **Captive portal:** the retry after the access point shuts down now reuses the credentials
  that were entered. Before, it retried with empty ones.
- **Wi-Fi give-up:** when the retry ladder is exhausted, the device retries every 30 min instead
  of sleeping until a button press.
- **NOTE4C status LED (GPIO3):** blinks while awake. In deep sleep it stays on while charging
  and is off otherwise. Before, it floated and glowed all the time.

## Build, test and flash

```zsh
cd firmware/trmnl
pio run -e zectrix_note4c
pio test -e native
```

- Flashing (app-only vs full): [`docs/flashing.md`](../docs/flashing.md). App-only flashing keeps Wi-Fi and pairing.
- CI builds the firmware on every push and attaches `firmware.bin` and `merged_firmware.bin` as artifacts.
- `trmnl/.github/` holds upstream's workflows. GitHub ignores workflows in subdirectories, so they never run here.
- `test_serialize_log` fails to compile with old host compilers (GCC 9, Ubuntu 20.04), upstream too; CI's newer GCC builds it.

## Pulling upstream updates

```zsh
git subtree pull --prefix=firmware/trmnl https://github.com/LitoMore/trmnl-firmware zectrix --squash
```

This creates one squashed commit plus a merge. Resolve any conflicts with our changes as in a
normal merge, then build and run the tests. Keep upstream pulls as their own commits; don't mix them with feature work.

## Sending fixes upstream

The Wi-Fi fixes are useful to everyone. To open a PR:
1. Fork `LitoMore/trmnl-firmware` (or `usetrmnl/firmware`).
2. Cherry-pick the relevant commits. `git subtree split --prefix=firmware/trmnl` gives a history
   with upstream-relative paths.
3. Open the PR from that branch.
