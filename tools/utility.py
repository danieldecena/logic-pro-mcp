import executor
from fastmcp import FastMCP


def register_utility_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def logic_undo() -> str:
        """Undo the last action in Logic Pro (Cmd+Z)."""
        script = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "z" using {command down}
    end tell
end tell
"""
        executor.run_applescript(script)
        return "Undone"

    @mcp.tool()
    def logic_redo() -> str:
        """Redo the last undone action in Logic Pro (Cmd+Shift+Z)."""
        script = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "z" using {command down, shift down}
    end tell
end tell
"""
        executor.run_applescript(script)
        return "Redone"

    @mcp.tool()
    def logic_navigate_menu(menu_name: str, item_name: str) -> str:
        """Click a menu item in Logic Pro's menu bar. menu_name e.g. 'Track', item_name e.g. 'New Track...'"""
        item = executor.as_applescript_str(item_name)
        menu = executor.as_applescript_str(menu_name)
        script = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        click menu item "{item}" of menu "{menu}" of menu bar 1
    end tell
end tell
"""
        executor.run_applescript(script)
        return f"Clicked {menu_name} > {item_name}"

    @mcp.tool()
    def logic_get_status() -> str:
        """Return whether Logic Pro is running and what project is open."""
        if not executor.logic_is_running():
            return "Logic Pro is not running"
        script = """
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set winTitle to name of front window
    end tell
end tell
"""
        try:
            title = executor.run_applescript(script)
            return f"Logic Pro is running — {title}"
        except RuntimeError:
            return "Logic Pro is running (no project open)"
