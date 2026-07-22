---
name: logic-pro-mcp
description: >
  Build, extend, and use the Logic Pro MCP server that lets Claude control Logic Pro on macOS.
  Trigger whenever the user mentions Logic Pro and automation, controlling playback, managing tracks,
  opening projects, building an MCP for Logic Pro, or scripting their DAW workflow — even if they
  don't say "MCP." Use for requests like "play my Logic project", "add a track in Logic",
  "control Logic Pro from Claude", "start recording in Logic", or "what project is open in Logic."
---

# Logic Pro MCP

Logic Pro has no AppleScript dictionary (`.sdef`). All interactive control goes through
**System Events (Accessibility API) + keyboard shortcuts** as the primary tier.

**Server location:** `~/Developer/music/logic-pro-mcp/`

---

## Step 1 — Check if server exists

```bash
ls ~/Developer/music/logic-pro-mcp/server.py 2>/dev/null && echo "exists" || echo "scaffold needed"
```

If present (the normal case) → jump to [Using Tools](#using-tools) or [Extending](#extending). If missing → rebuild it from the layout in [Server layout](#server-layout).

---

## Server layout

The server is already built and working — a unified "Creator Studio" MCP (34 tools across 8
modules). This is the reference layout: read the existing files before modifying, or recreate
this structure if the server is ever missing.

```
~/Developer/music/logic-pro-mcp/
├── server.py          FastMCP entry point — registers all 8 modules
├── executor.py        osascript wrapper + logic_is_running()
├── config.py          music-workspace root + library paths (LOGIC_STUDIO_MUSIC_ROOT override)
├── tools/
│   ├── transport.py   play, stop, record, rewind, ff, go_to_start        ← implemented
│   ├── project.py     get_current_project, open_project, save, new        ← implemented
│   ├── session.py     get_tempo, get_key, get_bar_position (structured)   ← implemented
│   ├── utility.py     undo, redo, navigate_menu, get_status               ← implemented
│   ├── tracks.py      list_tracks, add_track, mute, solo (best-effort)    ← implemented
│   ├── bounce.py      bounce (best-effort), export                        ← implemented
│   ├── pipeline.py    download, separate_stems, chop_vocals, run_full     ← wraps music-core.sh
│   └── library.py     list/organize projects, samples, stems, exports     ← implemented
├── requirements.txt
├── .mcp.json
└── CLAUDE.md
```

Tested under FastMCP 3.4.2 (Python 3.14). Track + bounce tools are best-effort
UI scripting — verify against a live session and re-derive selectors with
`entire contents of front window` if a Logic update moves them.

To create the venv and install:
```bash
cd ~/Developer/music/logic-pro-mcp
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

---

## Core Patterns

### osascript wrapper

All AppleScript runs through `executor.run_applescript(script, timeout=10)`. Never use
`os.system` or inline subprocess calls in tool functions.

**Critical rules (from codebase experience):**
- AppleScript variable names must NOT start with `_` — causes parse errors
- Always `tell application "Logic Pro" to activate` before sending keystrokes
- Shell state doesn't persist between osascript calls — one call per action
- Use `key code` (numeric) for non-letter keys (space=49, return=36); use `keystroke` for letters

### Automation tiers (use in priority order)

| Tier | When to use | Example |
|------|-------------|---------|
| 1. Keystroke | Transport, undo, navigation | `keystroke " "` for play/stop |
| 2. Menu navigation | Actions with no shortcut | `click menu item "New Track"` |
| 3. Accessibility read | State queries (tempo, track names) | AXValue of tempo field |
| 4. `.logicx` XML read | Project inspection when Logic isn't open | Parse bundle XML directly |

---

## Using Tools

Run the server:
```bash
cd ~/Developer/music/logic-pro-mcp
source .venv/bin/activate
python server.py
```

Or via MCP config (already in `.mcp.json` — add to Claude's MCP with `claude mcp add`).

**Verify connectivity:**
```bash
claude mcp list  # should show "logic-pro"
```

**Implemented transport tools:**
- `logic_play` — toggle playback (Space)
- `logic_stop` — stop (Space if playing)
- `logic_record` — start recording (R)
- `logic_go_to_start` — return to bar 1 (Return)
- `logic_rewind` — step back (,)
- `logic_fast_forward` — step forward (.)

---

## Extending

To add a new tool, follow this pattern in the relevant `tools/*.py` file:

```python
@mcp.tool()
def logic_my_tool(param: str) -> str:
    """One-line description for Claude to understand when to call this."""
    script = f'''
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        -- action here
    end tell
end tell
'''
    executor.run_applescript(script)
    return "done"
```

Register it in `server.py` if adding a new module: `from tools.mymodule import register_my_tools`.

See `references/automation.md` for AppleScript recipes per feature area (tracks, tempo, menus, project state).

---

## Wiring up `.mcp.json`

The server project already has `.mcp.json`. To wire Claude Code globally:
```bash
claude mcp add logic-pro -- /Users/home/Developer/music/logic-pro-mcp/.venv/bin/python /Users/home/Developer/music/logic-pro-mcp/server.py
```

Or per-project, copy/reference `.mcp.json` from the server directory.

---

## Gotchas

- **Accessibility permission required:** System Events control of Logic Pro needs Accessibility access for Terminal/Claude Code. Grant in System Settings → Privacy & Security → Accessibility.
- **Logic Pro must be open:** All System Events tools fail silently if the app isn't running. `get_current_project` returns `"Logic Pro not running"` as the sentinel.
- **Keyboard locale:** `keystroke` sends the character, not the physical key. If the user has a non-US keyboard layout and a shortcut uses a symbol (`,`, `.`), prefer `key code` over `keystroke`.
- **Space bar edge case:** Space toggles play/stop — the tool can't distinguish state without reading the transport bar first. There is no dedicated transport-state tool; `logic_play`/`logic_stop` both send Space, so the caller must track intended state.
- **No .sdef:** `tell application "Logic Pro" to play` does NOT work. Always go through System Events.
- **Process name:** `tell process "Logic Pro Creator Studio"` — NOT `"Logic Pro"`. Confirmed on Logic Pro 12 (Creator Studio edition). `tell application "Logic Pro"` still works for `open`/`activate`.
