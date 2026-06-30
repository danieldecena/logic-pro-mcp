import re
from pathlib import Path

import config
import executor
from fastmcp import FastMCP

_TEMPO_RE = re.compile(rb"(?:tempo|bpm)\D{0,8}(\d{2,3}(?:\.\d+)?)", re.IGNORECASE)


def _newest_active_logicx() -> Path | None:
    active = config.lib_path("projects_active")
    if not active.exists():
        return None
    bundles = [p for p in active.iterdir() if p.name.endswith(".logicx")]
    if not bundles:
        return None
    return max(bundles, key=lambda p: p.stat().st_mtime)


def _tempo_from_logicx() -> str | None:
    """Best-effort tempo read from the newest Active project bundle (Logic closed).

    Scans the project's binary data for a plausible BPM. Approximate — the
    transport-bar read (Logic open) is authoritative.
    """
    bundle = _newest_active_logicx()
    if not bundle:
        return None
    data_file = bundle / "projectData"
    if not data_file.exists():
        candidates = list(bundle.rglob("projectData"))
        if not candidates:
            return None
        data_file = candidates[0]
    try:
        raw = data_file.read_bytes()
    except OSError:
        return None
    for m in _TEMPO_RE.finditer(raw):
        try:
            bpm = float(m.group(1))
        except ValueError:
            continue
        if 40.0 <= bpm <= 300.0:
            return f"{bpm} (from {bundle.name}, approximate)"
    return None

_FIELD_SCRIPT = """
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set AppleScript's text item delimiters to "\n"
        set allFields to every text field of front window
        set vals to {}
        repeat with f in allFields
            try
                set fieldVal to value of f
                if fieldVal is not missing value then
                    set end of vals to fieldVal
                end if
            end try
        end repeat
        set result to vals as string
        set AppleScript's text item delimiters to ""
        return result
    end tell
end tell
"""

_KEY_RE = re.compile(r"^[A-Ga-g][b#]?\s*(m|maj|min|major|minor)?$", re.IGNORECASE)
_POS_RE = re.compile(r"^\d+\s+\d+\s+\d+\s+\d+$")


def _get_fields() -> list[str]:
    try:
        raw = executor.run_applescript(_FIELD_SCRIPT)
    except executor.NoProjectWindowError:
        return []
    return [v for v in raw.split("\n") if v.strip()]


def register_session_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def logic_get_tempo() -> str:
        """Return the current project BPM from Logic Pro's transport bar.

        Falls back to reading the newest Active .logicx project file if Logic
        isn't running or the transport field can't be located.
        """
        if executor.logic_is_running():
            for val in _get_fields():
                try:
                    bpm = float(val.strip())
                    if 20.0 <= bpm <= 400.0:
                        return str(bpm)
                except ValueError:
                    continue
        fallback = _tempo_from_logicx()
        if fallback:
            return fallback
        if not executor.logic_is_running():
            return "Logic Pro is not running and no readable .logicx tempo found"
        return "Tempo field not found in transport bar"

    @mcp.tool()
    def logic_get_key() -> str:
        """Return the current key signature from Logic Pro's transport bar (e.g. 'C', 'Am')."""
        if not executor.logic_is_running():
            return "Logic Pro is not running"
        fields = _get_fields()
        if not fields:
            return "No project open or transport bar not readable"
        for val in fields:
            if _KEY_RE.match(val.strip()):
                return val.strip()
        return "Key signature field not found in transport bar"

    @mcp.tool()
    def logic_get_bar_position() -> str:
        """Return the current playhead position as 'bar beat division tick' from Logic Pro."""
        if not executor.logic_is_running():
            return "Logic Pro is not running"
        fields = _get_fields()
        if not fields:
            return "No project open or transport bar not readable"
        for val in fields:
            if _POS_RE.match(val.strip()):
                return val.strip()
        return "Bar position field not found in transport bar"
