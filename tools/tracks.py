"""Track management tools for Logic Pro Creator Studio.

All control goes through System Events (no AppleScript dictionary). Track
operations that depend on selection (mute/solo) act on the currently selected
track(s); call logic_list_tracks first to see what exists.

Reliability: list/add are best-effort UI scripting and may shift across Logic
versions — re-derive selectors with `entire contents of front window` if they
break. Process name is "Logic Pro Creator Studio".
"""

import executor
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

_PROC = 'tell process "Logic Pro Creator Studio"'

# Track headers are AXTextFields whose parent is an AXGroup inside an AXList
# (the tracks-header area). This distinguishes them from the channel-strip name
# field (whose parent chain is AXLayoutItem -> AXLayoutArea). Derived from the
# live AX tree — re-inspect with `entire contents of front window` if it breaks.
_LIST_SCRIPT = """
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set trackNames to {}
        set ec to entire contents of front window
        repeat with el in ec
            try
                if role of el is "AXTextField" then
                    set p1 to (value of attribute "AXParent" of el)
                    set p2 to (value of attribute "AXParent" of p1)
                    if (role of p1 is "AXGroup") and (role of p2 is "AXList") then
                        set v to (value of el) as string
                        if v is not "" and v is not "missing value" then
                            set end of trackNames to v
                        end if
                    end if
                end if
            end try
        end repeat
        set AppleScript's text item delimiters to linefeed
        set joined to trackNames as string
        set AppleScript's text item delimiters to ""
        return joined
    end tell
end tell
"""


def _select_track_script(name: str | None = None, index: int | None = None) -> str:
    """Build an AppleScript that selects a track header by name or 1-based index.

    Pure (no side effects) so it can be unit-tested. Clicks the header AXGroup
    (the row container) rather than the AXTextField, to select the track without
    triggering inline rename. Returns "selected:<name>" or "notfound".
    """
    if name:
        match = f'if v is equal to "{executor.as_applescript_str(name)}" then'
    elif index:
        match = f'if idx is equal to {int(index)} then'
    else:
        raise ValueError("select track needs a non-empty name or a positive index")
    return f"""
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set ec to entire contents of front window
        set idx to 0
        repeat with el in ec
            try
                if role of el is "AXTextField" then
                    set p1 to (value of attribute "AXParent" of el)
                    set p2 to (value of attribute "AXParent" of p1)
                    if (role of p1 is "AXGroup") and (role of p2 is "AXList") then
                        set idx to idx + 1
                        set v to (value of el) as string
                        {match}
                            click p1
                            return "selected:" & v
                        end if
                    end if
                end if
            end try
        end repeat
        return "notfound"
    end tell
end tell
"""


def register_track_tools(mcp: FastMCP) -> None:

    @mcp.tool(
        annotations={
            "title": "List Logic tracks",
            "readOnlyHint": True,
            "openWorldHint": True,
        }
    )
    def logic_list_tracks() -> str:
        """List the names of tracks in the open Logic Pro project, one per line.

        Reads the track-header accessibility table. Returns a status message if
        Logic isn't running or no tracks are found.
        """
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        try:
            out = executor.run_applescript(_LIST_SCRIPT).strip()
        except executor.NoProjectWindowError as exc:
            raise ToolError(str(exc))
        if not out:
            return "No tracks found (project may be empty or UI tree differs)"
        names = [n for n in out.split("\n") if n.strip()]
        return "\n".join(f"{i}. {n}" for i, n in enumerate(names, 1))

    @mcp.tool(
        annotations={
            "title": "Add a new track",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    def logic_add_track() -> str:
        """Open Logic Pro's New Track dialog (Track > New Track...).

        A dialog appears for track type/options; accept defaults or drive it
        with logic_navigate_menu / keystrokes afterward.
        """
        script = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {_PROC}
        click menu item "New Track..." of menu "Track" of menu bar 1
    end tell
end tell
"""
        executor.run_applescript(script)
        return "New Track dialog opened"

    def _select(name: str = "", index: int = 0) -> str:
        """Select a track header; returns the selected name. Raises if not found."""
        if not name and not index:
            raise ToolError("Pass a track name or a 1-based index")
        try:
            out = executor.run_applescript(_select_track_script(name=name or None, index=index or None)).strip()
        except executor.NoProjectWindowError as exc:
            raise ToolError(str(exc))
        if out.startswith("selected:"):
            return out.split(":", 1)[1]
        try:
            avail = [n for n in executor.run_applescript(_LIST_SCRIPT).strip().split("\n") if n.strip()]
        except Exception:
            avail = []
        hint = ("; available: " + ", ".join(avail)) if avail else ""
        raise ToolError(f"Track not found: {name or ('#' + str(index))}{hint}")

    @mcp.tool(
        annotations={
            "title": "Select a track",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    def logic_select_track(name: str = "", index: int = 0) -> str:
        """Select a track by exact name or 1-based index (name wins if both given).

        Clicks the track header so subsequent logic_mute_track / logic_solo_track
        act on it. Call logic_list_tracks first to see names and positions.
        """
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        return f"Selected track: {_select(name, index)}"

    @mcp.tool(
        annotations={
            "title": "Mute a track",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def logic_mute_track(track: str = "") -> str:
        """Toggle mute (M). Pass `track` (name) to select it first; otherwise acts
        on the currently selected track. M toggles, so check state via
        logic_list_tracks if needed.
        """
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        selected = _select(name=track) if track else None
        script = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {_PROC}
        keystroke "m"
    end tell
end tell
"""
        executor.run_applescript(script)
        return f"Toggled mute on {selected!r}" if selected else "Toggled mute on selected track"

    @mcp.tool(
        annotations={
            "title": "Solo selected track",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def logic_solo_track(track: str = "") -> str:
        """Toggle solo (S). Pass `track` (name) to select it first; otherwise acts
        on the currently selected track.

        Note: S only solos when the Tracks area has focus; selecting the track
        first (via `track=`) also focuses the Tracks area.
        """
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        selected = _select(name=track) if track else None
        script = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {_PROC}
        keystroke "s"
    end tell
end tell
"""
        executor.run_applescript(script)
        return f"Toggled solo on {selected!r}" if selected else "Toggled solo on selected track"
