import executor
from fastmcp import FastMCP


def register_transport_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def logic_play() -> str:
        """Toggle playback in Logic Pro (Space bar)."""
        script = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke " "
    end tell
end tell
"""
        executor.run_applescript(script)
        return "Playback toggled"

    @mcp.tool()
    def logic_stop() -> str:
        """Stop playback in Logic Pro (Space bar while playing)."""
        script = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke " "
    end tell
end tell
"""
        executor.run_applescript(script)
        return "Stopped"

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
