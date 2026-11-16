# collector

Gathers the dashboard data and pushes it to the server that renders the e-ink screen.

```
sources/   weather.py  github.py  claude.py  pet.py   -> one top-level key each in the payload
render/    eink.py (BWRY dithering, PNG, .bin packing)  heatmap.py
sinks/     larapaper.py (webhook, deep_merge)          -> later: our own server
cli.py     zectrix-collect
```

The payload shape is documented in [`../schema/dashboard.schema.json`](../schema/dashboard.schema.json);
the template in `server/larapaper/templates/` reads the same keys.

## Run

```zsh
cd collector
cp .env.example .env        # then fill it in
uv run zectrix-collect --dry-run
uv run zectrix-collect
```

`--only weather,github` limits the run to some sources. Who sends what:

| Where | Sources | How |
|---|---|---|
| GitHub Actions | `weather,github` | `.github/workflows/collect.yml`, every 15 min |
| Your PC | `claude,pet` | `host/systemd/` timer (runs everything while LaraPaper is on the LAN) |

Because the LaraPaper sink sends `merge_strategy: deep_merge`, each sender only updates its own
keys. A source that fails is left out of the payload, so the screen keeps its last good value;
the run then exits with status 1 so the failure shows up in Actions / `journalctl`.

## Adding things

- **A data source:** add `sources/<name>.py` with `collect(cfg) -> dict` and `summary(dict) -> str`,
  register it in `sources/__init__.py`, document it in the schema, then use it in the template.
- **A server:** add `sinks/<name>.py` with `send(data, cfg) -> str`, register it in
  `sinks/__init__.py`, and set `SINK=<name>`.

## Tests

```zsh
uv run pytest
uv run ruff check
```

## Image converter

`eink-convert` turns any photo into the NOTE4C's 30000-byte 2bpp frame. It can also upload it to the
stock firmware's LAN API:

```zsh
uv run eink-convert photo.jpg -o out.bin --preview out.png
```
