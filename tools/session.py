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
        set joined to vals as string
        set AppleScript's text item delimiters to ""
        return joined
    end tell
end tell
"""

_KEY_RE = re.compile(r"^[A-Ga-g][b#]?\s*(m|maj|min|major|minor)?$", re.IGNORECASE)
_POS_RE = re.compile(r"^\d+\s+\d+\s+\d+\s+\d+$")

# The control-bar key signature is an AXPopUpButton (value like "C Major"),
# not a text field — scan the window's elements for it.
_KEY_POPUP_SCRIPT = """
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set ec to entire contents of front window
        repeat with el in ec
            try
                if role of el is "AXPopUpButton" then
                    set v to (value of el) as string
                    if v contains "Major" or v contains "Minor" then return v
                end if
            end try
        end repeat
        return ""
    end tell
end tell
"""


def _get_fields() -> list[str]:
    try:
        raw = executor.run_applescript(_FIELD_SCRIPT)
    except executor.NoProjectWindowError:
        return []
    return [v for v in raw.split("\n") if v.strip()]


# The tempo/BPM readout is not always a plain text field — depending on the
# Logic build it can be an LCD-style element that exposes the number via its
# value, title, OR description rather than a text-field value. Scan the whole
# front-window element tree (like the key read) and collect all three attributes
# from every element, so we can pattern-match a BPM regardless of where it lives.
_UI_VALUES_SCRIPT = """
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set AppleScript's text item delimiters to linefeed
        set vals to {}
        repeat with el in (entire contents of front window)
            try
                set v to (value of el) as string
                if v is not "" and v is not "missing value" then set end of vals to v
            end try
            try
                set t to (title of el) as string
                if t is not "" and t is not "missing value" then set end of vals to t
            end try
            try
                set d to (description of el) as string
                if d is not "" and d is not "missing value" then set end of vals to d
            end try
        end repeat
        set out to vals as string
        set AppleScript's text item delimiters to ""
        return out
    end tell
end tell
"""

# A decimal-bearing number in BPM range — the tempo LCD characteristically
# shows trailing decimals ("120.0000"), distinctive enough to avoid colliding
# with other numeric controls.
_BPM_DECIMAL_RE = re.compile(r"(?<!\d)(\d{2,3}\.\d+)(?!\d)")


def _bpm_in_range(text: str) -> float | None:
    try:
        bpm = float(text)
    except ValueError:
        return None
    return bpm if 20.0 <= bpm <= 400.0 else None


def _tempo_from_ui() -> float | None:
    """Best-effort tempo read by scanning the whole element tree (Logic open)."""
    try:
        raw = executor.run_applescript(_UI_VALUES_SCRIPT, timeout=20)
    except (executor.NoProjectWindowError, RuntimeError):
        return None
    values = [v for v in raw.split("\n") if v.strip()]
    # Match a decimal-bearing BPM ("120.0000") anywhere in the collected
    # value/title/description strings — distinctive enough to avoid colliding
    # with bare integers like a "100" pan/volume readout. If the build shows the
    # tempo without decimals we return None (caller reports not-found) rather
    # than risk returning a wrong number.
    for v in values:
        m = _BPM_DECIMAL_RE.search(v)
        if m:
            bpm = _bpm_in_range(m.group(1))
            if bpm is not None:
                return bpm
    return None


def register_session_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def logic_get_tempo() -> dict:
        """Return the current project BPM from Logic Pro's transport bar.

        Falls back to reading the newest Active .logicx project file if Logic
        isn't running or the transport field can't be located. Returns
        {bpm, source, approximate} where source is 'transport' or the bundle name.
        """
        if executor.logic_is_running():
            for val in _get_fields():
                try:
                    bpm = float(val.strip())
                    if 20.0 <= bpm <= 400.0:
                        return {"bpm": bpm, "source": "transport", "approximate": False}
                except ValueError:
                    continue
            # text-field scan missed it — scan the full element tree (LCD tempo)
            ui_bpm = _tempo_from_ui()
            if ui_bpm is not None:
                return {"bpm": ui_bpm, "source": "transport", "approximate": False}
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
            val = executor.run_applescript(_KEY_POPUP_SCRIPT).strip()
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
