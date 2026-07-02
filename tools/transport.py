import executor
from fastmcp import FastMCP

_TOGGLE_PLAYBACK = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke " "
    end tell
end tell
"""


def register_transport_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def logic_play() -> str:
        """Toggle playback in Logic Pro (Space bar).

        Space is a toggle: this starts playback if stopped and stops it if
        already playing. There is no separate non-toggling play key command.
        """
        executor.run_applescript(_TOGGLE_PLAYBACK)
        return "Playback toggled"

    @mcp.tool()
    def logic_stop() -> str:
        """Toggle playback in Logic Pro (Space bar) — intended to stop playback.

        NOTE: Logic has no non-toggling stop key command, so this sends the same
        Space toggle as logic_play. It stops playback ONLY if Logic is currently
        playing; if playback is already stopped it will START it. Playback state
        isn't read, so this is not idempotent — prefer logic_play for a plain
        toggle, and use this only when you know playback is running.
        """
        executor.run_applescript(_TOGGLE_PLAYBACK)
        return "Sent playback toggle (stops if playing)"

    @mcp.tool()
    def logic_record() -> str:
        """Start recording in Logic Pro (R key)."""
        script = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "r"
    end tell
end tell
"""
        executor.run_applescript(script)
        return "Recording started"

    @mcp.tool()
    def logic_go_to_start() -> str:
        """Move playhead to bar 1 (Return key)."""
        script = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        key code 36
    end tell
end tell
"""
        executor.run_applescript(script)
        return "Playhead at start"

    @mcp.tool()
    def logic_rewind() -> str:
        """Step playhead back (comma key)."""
        script = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke ","
    end tell
end tell
"""
        executor.run_applescript(script)
        return "Rewound"

    @mcp.tool()
    def logic_fast_forward() -> str:
        """Step playhead forward (period key)."""
        script = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "."
    end tell
end tell
"""
        executor.run_applescript(script)
        return "Fast-forwarded"
