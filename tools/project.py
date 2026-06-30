import executor
from fastmcp import FastMCP


def register_project_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def logic_get_current_project() -> str:
        """Return the name of the currently open Logic Pro project, or a status message."""
        if not executor.logic_is_running():
            return "Logic Pro is not running"
        script = """
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set winTitle to name of front window
    end tell
end tell
"""
        title = executor.run_applescript(script)
        # Window title format: "ProjectName - Logic Pro Creator Studio"
        if " - " in title:
            return title.split(" - ")[0].strip()
        return title

    @mcp.tool()
    def logic_open_project(path: str) -> str:
        """Open a Logic Pro project file at the given absolute path."""
        script = f"""
tell application "Logic Pro"
    open POSIX file "{path}"
end tell
"""
        executor.run_applescript(script, timeout=30)
        return f"Opened {path}"

    @mcp.tool()
    def logic_save() -> str:
        """Save the current Logic Pro project (Cmd+S)."""
        script = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "s" using {command down}
    end tell
end tell
"""
        executor.run_applescript(script)
        return "Saved"

    @mcp.tool()
    def logic_new_project() -> str:
        """Create a new Logic Pro project (Cmd+N)."""
        script = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "n" using {command down}
    end tell
end tell
"""
        executor.run_applescript(script)
        return "New project dialog opened"
