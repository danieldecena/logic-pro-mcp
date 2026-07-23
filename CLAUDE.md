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

## Structure — unified "Creator Studio" MCP (34 tools)

| File | Purpose |
|------|---------|
| `server.py` | FastMCP entry + registers all 8 tool modules |
| `executor.py` | `run_applescript()` wrapper (classifies accessibility vs not-running errors) |
| `config.py` | music-workspace root + library paths; `LOGIC_STUDIO_MUSIC_ROOT` env override |
| `tools/transport.py` | play, stop, record, rewind, go_to_start, fast_forward |
| `tools/project.py` | get_current_project, open_project (validates path), save, new_project |
| `tools/utility.py` | undo, redo, navigate_menu, get_status |
| `tools/session.py` | get_tempo (with .logicx fallback), get_key, get_bar_position — return structured dicts |
| `tools/tracks.py` | list_tracks, add_track, mute, solo *(best-effort UI scripting)* |
| `tools/bounce.py` | bounce *(best-effort)*, export |
| `tools/pipeline.py` | download, separate_stems, chop_vocals, run_full — wraps `music-core.sh` |
| `tools/library.py` | list projects/samples/stems/exports (structured + paginated); new-from-template, archive, promote |
| `tests/test_studio.py` | pytest: config, pipeline command-builder, library ops (temp workspace) |
| `evals/logic_studio_eval.xml` | mcp-builder Phase-4 eval questions |

## Music workspace

The `pipeline_*` and `library_*` tools operate on the music workspace at
`~/Developer/music` (override with `LOGIC_STUDIO_MUSIC_ROOT`). Pipeline tools
shell out to `<root>/lib/music-core.sh` and need `demucs`, `gamdl`/`yt-dlp`,
`ffmpeg` on PATH. Run tests: `python -m pytest -q tests/`.

### Tool tiers (reliability)
- ★★★ deterministic: all `pipeline_*`, `library_*`, transport, open/save.
- ★★ solid-but-brittle: track ops, menu navigation, session reads (UI scripting).
- ★ best-effort: `logic_bounce` (two-dialog flow). Verify against a live session.

### Conventions

- **Structured output**: data-returning tools return Python types (`dict`/`list`)
  so FastMCP derives an outputSchema + structuredContent. Applies to
  `library_list_*` and `session.logic_get_{tempo,key,bar_position}`. Action tools
  (play, save, mute, bounce, …) still return human-readable `str`.
- **Pagination**: `library_list_{projects,samples,stems,exports}` take
  `limit` (default 50) and `offset` (default 0); results include
  `total/offset/limit/returned/has_more`. Pure helper: `library.paginate()`.
- **Error signaling**: genuine errors (invalid args, "Logic Pro is not running"
  where the tool can't proceed, missing files) `raise ToolError(...)`
  (`from fastmcp.exceptions import ToolError`) so the framework flags `isError`.
  Empty results (e.g. an empty project list) are NOT errors — they return an
  empty structure. `logic_get_status` still returns a "not running" string since
  reporting that state is its purpose.

## Add to Claude

```bash
claude mcp add -s user logic-pro -- /Users/home/Developer/music/logic-pro-mcp/.venv/bin/python /Users/home/Developer/music/logic-pro-mcp/server.py
```

## Key rules

- All AppleScript variable names must NOT start with `_`
- **Never hardcode the app or process name in a script.** The app is
  `Logic Pro Creator Studio` here, `Logic Pro` on a stock install — both come
  from `config.LOGIC_APP_NAME` / `config.LOGIC_PROCESS_NAME`, surfaced as
  `executor.APP` / `executor.PROC` / `executor.ACTIVATE` / `executor.TELL_PROC`.
  Interpolate those; a literal `tell application "Logic Pro"` fails with -1728
  on this machine.
- **Keystroke/menu tools**: build the script with `executor.keystroke_block(body)`
  (wraps activate + `tell process`; `body` is verbatim so `{command down}` stays
  literal) and run it via `executor.run_ui(script)`, which launches Logic first
  if it isn't running. Read-only tools that report the not-running state
  themselves call `executor.run_applescript` directly.
- Logic Pro has no `.sdef` — never use `tell application "Logic Pro" to play`
- See `.claude/skills/logic-pro-mcp/references/automation.md` for recipes
