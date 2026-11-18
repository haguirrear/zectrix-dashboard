# systemd user timer (your PC)

Runs `zectrix-collect` every 5 minutes as your user, with no root and no cron.

```zsh
systemctl --user link ~/Documents/projects/zectrix-dashboard/host/systemd/zectrix-collector.service
systemctl --user link ~/Documents/projects/zectrix-dashboard/host/systemd/zectrix-collector.timer
systemctl --user enable --now zectrix-collector.timer
```

`link` points systemd at the files in the repo, so a `git pull` updates them (then run
`systemctl --user daemon-reload`).

- Logs: `journalctl --user -u zectrix-collector.service -n 20` (`-f` to follow)
- Run now: `systemctl --user start zectrix-collector.service`
- Next run: `systemctl --user list-timers zectrix-collector.timer`

Notes:
- **PATH:** systemd jobs get a minimal PATH, so tools installed via mise/asdf/nvm aren't
  found. The service calls uv by its full path (`%h/.local/bin/uv`) for that reason.
- **Repo location:** if the repo isn't at `~/Documents/projects/zectrix-dashboard`, change
  `WorkingDirectory=` in the service file (or override it with `systemctl --user edit`).
- **Which sources:** once the server is on the VPS, which sends weather and GitHub itself
  (`host/vps/`), limit this PC to its own data:
  `systemctl --user edit zectrix-collector.service` and add
  ```ini
  [Service]
  Environment=SOURCES=claude,pet
  ```
- **Laptop asleep:** timers don't run while the machine is suspended; the screen keeps the last
  data it received (each section independently).
