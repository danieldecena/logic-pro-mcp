# logic-pro-mcp

FastMCP server that exposes Logic Pro controls to Claude via macOS System Events + AppleScript.

## Stack

- Python 3 + FastMCP
- Automation: `osascript` via `subprocess` (no AppleScript dictionary — System Events only)
- No external APIs or auth

## Run

```bash
source .venv/bin/activate
python server.py
```

## Setup (first time)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Grant Terminal (or Claude Code's shell) Accessibility permission:
System Settings → Privacy & Security → Accessibility → add Terminal / your IDE.

## Structure

| File | Purpose |
|------|---------|
| `server.py` | FastMCP entry + tool registration |
| `executor.py` | `run_applescript()` wrapper — all osascript goes through here |
| `tools/transport.py` | play, stop, record, rewind, go_to_start, fast_forward |
| `tools/project.py` | get_current_project, open_project, save, new_project |
| `tools/utility.py` | undo, redo, navigate_menu, get_status |
| `tools/session.py` | get_tempo, get_key, get_bar_position |

## Add to Claude

```bash
claude mcp add logic-pro -- /Users/home/Developer/projects/logic-pro-mcp/.venv/bin/python /Users/home/Developer/projects/logic-pro-mcp/server.py
```

## Key rules

- All AppleScript variable names must NOT start with `_`
- Always `tell application "Logic Pro" to activate` before sending keystrokes
- Logic Pro has no `.sdef` — never use `tell application "Logic Pro" to play`
- See `~/.claude/skills/logic-pro-mcp/references/automation.md` for recipes
