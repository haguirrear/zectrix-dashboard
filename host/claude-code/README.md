# Claude Code usage tap (your PC)

Claude Code's [status line](https://code.claude.com/docs/en/statusline) receives your plan's
rate-limit usage (5-hour and 7-day windows) as JSON on every refresh. `claude_usage_tap.py`
saves that to `~/.cache/claude-usage.json`, and the collector's `claude` source reads it.

There is no API for these numbers, so this part must run on the machine where you use Claude Code.

## Install

Add one line to your status-line script (`~/.claude/statusline.sh` or whatever
`statusLine.command` in `~/.claude/settings.json` points to). It reads the same JSON your
script already gets and prints nothing, so your status line doesn't change:

```bash
#!/usr/bin/env bash
input=$(cat)
printf '%s' "$input" | python3 "$HOME/Documents/projects/zectrix-dashboard/host/claude-code/claude_usage_tap.py" 2>/dev/null
# ... the rest of your status line, using "$input" ...
```

If you don't have a status line yet, create the script above, end it with something like
`echo "$input" | jq -r '.model.display_name'`, `chmod +x` it, and set in `~/.claude/settings.json`:

```json
{ "statusLine": { "type": "command", "command": "~/.claude/statusline.sh" } }
```

## How it reaches the screen

The `host/systemd` timer runs `zectrix-collect --only claude,pet` (or everything, while the
server is on the LAN) every 5 minutes. The snapshot only updates while Claude Code is open; the
dashboard shows its age ("as of HH:MM") and marks it when older than 5 hours.
