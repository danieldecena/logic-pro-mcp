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


    @mcp.tool(
        annotations={
            "title": "Mute selected track",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def logic_mute_track() -> str:
        """Toggle mute on the currently selected track in Logic Pro (M key).

        Select the target track first (in Logic or via a future select tool);
        M toggles, so call logic_list_tracks to know current state if needed.
        """
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        script = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {_PROC}
        keystroke "m"
    end tell
end tell
"""
        executor.run_applescript(script)
        return "Toggled mute on selected track"

    @mcp.tool(
        annotations={
            "title": "Solo selected track",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def logic_solo_track() -> str:
        """Toggle solo on the currently selected track in Logic Pro (S key).

        Note: S only solos when a track is selected and the Tracks area has
        focus; if a text field is focused it types 's' instead.
        """
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        script = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {_PROC}
        keystroke "s"
    end tell
end tell
"""
        executor.run_applescript(script)
        return "Toggled solo on selected track"
