# Common tasks. Install just: `uv tool install rust-just` (or your package manager). `just` lists them.

port := env("PORT", "/dev/ttyACM0")
esptool := env("ESPTOOL", "~/.platformio/penv/bin/esptool")
fw := "firmware/trmnl"

default:
    @just --list

# --- collector -------------------------------------------------------------------

# Collect and print without sending (e.g. `just collect-dry weather,github`)
collect-dry sources="weather,github,claude,pet":
    cd collector && uv run zectrix-collect --dry-run --only {{sources}}

# Collect and send
collect sources="weather,github,claude,pet":
    cd collector && uv run zectrix-collect --only {{sources}}

# Lint and test the collector
test:
    cd collector && uv run ruff check && uv run pytest -q

# --- firmware --------------------------------------------------------------------

# Build the NOTE4C firmware
fw-build:
    cd {{fw}} && pio run -e zectrix_note4c

# Firmware unit tests (host)
fw-test:
    cd {{fw}} && pio test -e native

# Flash the app only at 0x20000: keeps Wi-Fi and pairing
flash-app: fw-build
    {{esptool}} --chip esp32s3 -p {{port}} -b 460800 write-flash 0x20000 {{fw}}/.pio/build/zectrix_note4c/firmware.bin

# Flash bootloader + partitions + app at 0x0: ERASES Wi-Fi credentials and pairing
flash-full: fw-build
    @echo "This erases Wi-Fi credentials and the API key (re-pair with Permit Auto-Join). Ctrl-C to abort."
    @sleep 5
    {{esptool}} --chip esp32s3 -p {{port}} -b 460800 write-flash 0x0 {{fw}}/.pio/build/zectrix_note4c/merged_firmware.bin

# Serial logs
monitor:
    cd {{fw}} && pio device monitor -b 115200 -p {{port}}

# Pull upstream firmware changes into the subtree
fw-pull-upstream:
    git subtree pull --prefix={{fw}} https://github.com/LitoMore/trmnl-firmware zectrix --squash

# --- server ----------------------------------------------------------------------

# Push the dashboard template into LaraPaper and re-render
push-template:
    server/larapaper/scripts/push-template.sh

# --- repo hygiene ----------------------------------------------------------------

# Scan the git history for secrets
leaks:
    gitleaks git --config .gitleaks.toml --redact .
