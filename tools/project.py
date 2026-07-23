import executor
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError


def register_project_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def logic_get_current_project() -> str:
        """Return the name of the currently open Logic Pro project, or a status message."""
        if not executor.logic_is_running():
            return "Logic Pro is not running"
        script = f"""
tell application "System Events"
    {executor.TELL_PROC}
        set winTitle to name of front window
    end tell
end tell
"""
        try:
            title = executor.run_applescript(script)
        except executor.NoProjectWindowError:
            return "Logic Pro is running but no project is open"
        # Window title format: "ProjectName - Logic Pro Creator Studio"
        if " - " in title:
            return title.split(" - ")[0].strip()
        return title

    @mcp.tool()
    def logic_open_project(path: str) -> str:
        """Open a Logic Pro project file at the given absolute path."""
        import os

        expanded = os.path.expanduser(path)
        if not os.path.exists(expanded):
            raise ToolError(
                f"No file at {expanded}. Pass an absolute path to a .logicx project."
            )
        if not expanded.endswith(".logicx"):
            raise ToolError(f"{expanded} is not a .logicx project bundle.")
        path = expanded
        script = f"""
tell application "{executor.APP}"
    open POSIX file "{executor.as_applescript_str(path)}"
end tell
"""
        executor.run_applescript(script, timeout=30)
        return f"Opened {path}"

    @mcp.tool()
    def logic_save() -> str:
        """Save the current Logic Pro project (Cmd+S)."""
        executor.run_ui(
            executor.keystroke_block('        keystroke "s" using {command down}')
        )
        return "Saved"

    @mcp.tool()
    def logic_new_project() -> str:
        """Create a new Logic Pro project (Cmd+N)."""
        executor.run_ui(
            executor.keystroke_block('        keystroke "n" using {command down}')
        )
        return "New project dialog opened"
