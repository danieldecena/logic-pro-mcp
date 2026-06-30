import re

import executor
from fastmcp import FastMCP

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
    raw = executor.run_applescript(_FIELD_SCRIPT)
    return [v for v in raw.split("\n") if v.strip()]


def register_session_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def logic_get_tempo() -> str:
        """Return the current project BPM from Logic Pro's transport bar."""
        if not executor.logic_is_running():
            return "Logic Pro is not running"
        for val in _get_fields():
            try:
                bpm = float(val.strip())
                if 20.0 <= bpm <= 400.0:
                    return str(bpm)
            except ValueError:
                continue
        return "Tempo field not found in transport bar"

    @mcp.tool()
    def logic_get_key() -> str:
        """Return the current key signature from Logic Pro's transport bar (e.g. 'C', 'Am')."""
        if not executor.logic_is_running():
            return "Logic Pro is not running"
        for val in _get_fields():
            if _KEY_RE.match(val.strip()):
                return val.strip()
        return "Key signature field not found in transport bar"

    @mcp.tool()
    def logic_get_bar_position() -> str:
        """Return the current playhead position as 'bar beat division tick' from Logic Pro."""
        if not executor.logic_is_running():
            return "Logic Pro is not running"
        for val in _get_fields():
            if _POS_RE.match(val.strip()):
                return val.strip()
        return "Bar position field not found in transport bar"
