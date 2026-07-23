import re
from pathlib import Path

import config
import executor
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

_TEMPO_RE = re.compile(rb"(?:tempo|bpm)\D{0,8}(\d{2,3}(?:\.\d+)?)", re.IGNORECASE)


def _newest_active_logicx() -> Path | None:
    active = config.lib_path("projects_active")
    if not active.exists():
        return None
    bundles = [p for p in active.iterdir() if p.name.endswith(".logicx")]
    if not bundles:
        return None
    return max(bundles, key=lambda p: p.stat().st_mtime)


def _tempo_from_logicx() -> tuple[float, str] | None:
    """Best-effort tempo read from the newest Active project bundle (Logic closed).

    Scans the project's binary data for a plausible BPM. Approximate — the
    transport-bar read (Logic open) is authoritative. Returns (bpm, bundle_name)
    or None.
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
            return bpm, bundle.name
    return None


_FIELD_SCRIPT = f"""
tell application "System Events"
    {executor.TELL_PROC}
        set AppleScript's text item delimiters to "\n"
        set allFields to every text field of front window
        set vals to {{}}
        repeat with f in allFields
            try
                set fieldVal to value of f
                if fieldVal is not missing value then
                    set end of vals to fieldVal
                end if
            end try
        end repeat
        set joined to vals as string
        set AppleScript's text item delimiters to ""
        return joined
    end tell
end tell
"""

_POS_RE = re.compile(r"^\d+\s+\d+\s+\d+\s+\d+$")


def _control_bar_read_script(kind: str, selector: str) -> str:
    """Build an AppleScript that reads one Control Bar element's value.

    Pure (no side effects) so it can be unit-tested. `kind` is the element role
    word ("slider" or "pop up button"); `selector` is the trailing clause that
    picks it (e.g. 'whose description is "Tempo"'). Scopes straight to the inner
    Control Bar group — no `entire contents` full-tree walk, which times out on
    Logic — and returns the element's value as a string, or "" if it is absent.
    """
    return f"""
tell application "System Events"
    {executor.TELL_PROC}
        try
            set icb to first group of (first group of window 1 whose description is "Control Bar") whose description is "Control Bar"
            return (value of (first {kind} of icb {selector})) as string
        on error
            return ""
        end try
    end tell
end tell
"""


_TEMPO_SCRIPT = _control_bar_read_script("slider", 'whose description is "Tempo"')
_KEY_SCRIPT = _control_bar_read_script(
    "pop up button", 'whose description is "Key Signature"'
)


def _get_fields() -> list[str]:
    try:
        raw = executor.run_applescript(_FIELD_SCRIPT)
    except executor.NoProjectWindowError:
        return []
    return [v for v in raw.split("\n") if v.strip()]


def _bpm_in_range(text: str) -> float | None:
    try:
        bpm = float(text)
    except ValueError:
        return None
    return bpm if 20.0 <= bpm <= 400.0 else None


def register_session_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def logic_get_tempo() -> dict:
        """Return the current project BPM from Logic Pro's transport bar.

        Reads the tempo AXSlider in the Control Bar (scoped, no full-tree walk).
        Falls back to reading the newest Active .logicx project file if Logic
        isn't running or the transport control can't be located. Returns
        {bpm, source, approximate} where source is 'transport' or the bundle name.
        """
        if executor.logic_is_running():
            try:
                raw = executor.run_applescript(_TEMPO_SCRIPT)
            except executor.NoProjectWindowError:
                raw = ""
            bpm = _bpm_in_range(raw.strip())
            if bpm is not None:
                return {"bpm": bpm, "source": "transport", "approximate": False}
        fallback = _tempo_from_logicx()
        if fallback:
            bpm, bundle_name = fallback
            return {"bpm": bpm, "source": bundle_name, "approximate": True}
        if not executor.logic_is_running():
            raise ToolError(
                "Logic Pro is not running and no readable .logicx tempo found"
            )
        raise ToolError("Tempo field not found in transport bar")

    @mcp.tool()
    def logic_get_key() -> dict:
        """Return the current key signature from Logic Pro's transport bar (e.g. 'C', 'Am').

        Returns {key, source}.
        """
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        try:
            val = executor.run_applescript(_KEY_SCRIPT).strip()
        except executor.NoProjectWindowError:
            raise ToolError("No project open")
        if val:
            return {"key": val, "source": "transport"}
        raise ToolError("Key signature control not found in transport bar")

    @mcp.tool()
    def logic_get_bar_position() -> dict:
        """Return the current playhead position from Logic Pro.

        Returns {position, bar, beat, division, tick, source} where position is
        the raw 'bar beat division tick' string.
        """
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        fields = _get_fields()
        if not fields:
            raise ToolError("No project open or transport bar not readable")
        for val in fields:
            stripped = val.strip()
            if _POS_RE.match(stripped):
                bar, beat, division, tick = (int(x) for x in stripped.split())
                return {
                    "position": stripped,
                    "bar": bar,
                    "beat": beat,
                    "division": division,
                    "tick": tick,
                    "source": "transport",
                }
        raise ToolError("Bar position field not found in transport bar")
