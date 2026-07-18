import executor
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError


_UI_DUMP_SCRIPT = """
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set AppleScript's text item delimiters to linefeed
        set elList to {}
        try
            repeat with el in (entire contents of front window)
                try
                    set r to (role of el) as string
                    set n to (name of el) as string
                    set t to (title of el) as string
                    set d to (description of el) as string
                    set v to (value of el) as string
                    
                    set info to "Role: " & r
                    if n is not "" and n is not "missing value" then set info to info & " | Name: " & n
                    if t is not "" and t is not "missing value" then set info to info & " | Title: " & t
                    if d is not "" and d is not "missing value" then set info to info & " | Desc: " & d
                    if v is not "" and v is not "missing value" then set info to info & " | Val: " & v
                    
                    set end of elList to info
                end try
            end repeat
        on error err
            return "Error listing contents: " & err
        end try
        set out to elList as string
        set AppleScript's text item delimiters to ""
        return out
    end tell
end tell
"""


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

    @mcp.tool()
    def logic_dump_ui_hierarchy() -> str:
        """Dump the active window's UI element hierarchy.

        Use this tool when selectors or coordinates need to be derived or repaired.
        """
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        try:
            return executor.run_applescript(_UI_DUMP_SCRIPT, timeout=30)
        except Exception as exc:
            raise ToolError(f"Failed to dump UI hierarchy: {exc}")
