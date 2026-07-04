# Live smoke test — Logic Pro MCP

How to verify the app-control tools against a running Logic session, and the
one-time macOS permissions they require. The deterministic tools (`library_*`,
`pipeline_*`) don't need any of this — they're covered by `pytest tests/`.

## One-time permissions

The tools drive Logic through AppleScript → System Events, which macOS gates
behind **two independent** TCC permissions on whatever process runs the server:

1. **Accessibility** — System Settings → Privacy & Security → Accessibility.
   Add/enable the app that launches the server (your terminal for `claude` CLI,
   or `python3` directly).
2. **Automation** — System Settings → Privacy & Security → Automation. Under
   that app's entry, tick **System Events** and **Logic Pro Creator Studio**.

Automation entries only appear *after* the app first tries to send an Apple
event and macOS shows a consent dialog — so run the verify command below from a
**foreground terminal** (not a headless/spawned process) the first time, and
click **OK** on the prompts. A headless process gets a silent `-1743
"Not authorized to send Apple events"` and can't surface the dialog.

The app is named **"Logic Pro Creator Studio.app"** (bundle `com.apple.mobilelogic`),
so `open -a "Logic Pro"` fails — use `open -a "Logic Pro Creator Studio"`.

## Verify read-only tools (Logic open, any project)

```bash
cd ~/Developer/music/logic-pro-mcp && ./.venv/bin/python -c '
import asyncio, server
from fastmcp import Client
async def m():
    async with Client(server.mcp) as c:
        for t in ["logic_get_status","logic_get_current_project","logic_get_tempo","logic_get_key","logic_list_tracks"]:
            try: r=await c.call_tool(t,{}); print(t,"->",r.data)
            except Exception as e: print(t,"ERR:",e)
asyncio.run(m())'
```

Expected: status/project/key/tracks return live values. `logic_get_tempo` is
best-effort (see below).

## Verify write tools (self-reversing)

```bash
cd ~/Developer/music/logic-pro-mcp && ./.venv/bin/python -c '
import asyncio, server
from fastmcp import Client
async def m():
    async with Client(server.mcp) as c:
        async def call(n):
            try: r=await c.call_tool(n,{}); print(n,"->",r.data)
            except Exception as e: print(n,"ERR:",e)
        await call("logic_play"); await asyncio.sleep(1.5); await call("logic_stop")
        await call("logic_mute_track"); await call("logic_mute_track")
        await call("logic_solo_track"); await call("logic_solo_track")
asyncio.run(m())'
```

Watch Logic: the playhead should move ~1.5s then stop, and the selected track's
M and S buttons blink on then off. `logic_add_track` opens Logic's New Track
**dialog** (press Escape to dismiss) — test it separately; it's not self-reversing.
`logic_record` and `logic_bounce` commit real state — verify manually with a
scratch project.

## Known issue: `logic_get_tempo`

On Logic Pro Creator Studio 12 the tempo is not exposed as a text-field value.
`logic_get_tempo` first reads text fields, then scans every element's
value/title/description for a decimal BPM ("120.0000"), then falls back to the
newest saved `.logicx`. If it still returns "not found," the tempo LCD isn't
surfacing the number via any AX attribute we scan — dump the tree with a probe
(role + value + title + description of each element) to find where it lives:

```python
# probe.py — run: ./.venv/bin/python probe.py
import executor
SCRIPT = 'tell application "System Events" to tell process "Logic Pro Creator Studio"\nset out to ""\nrepeat with el in (entire contents of front window)\ntry\nset out to out & (role of el) & " | val=" & ((value of el) as string) & " | title=" & ((title of el) as string) & " | desc=" & ((description of el) as string) & linefeed\nend try\nend repeat\nreturn out\nend tell'
raw = executor.run_applescript(SCRIPT, timeout=30)
for line in raw.splitlines():
    if any(c.isdigit() for c in line):
        print(line)
```
