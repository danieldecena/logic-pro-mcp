import executor
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError


# Two AppleScript traps this script exists to avoid, both found against Logic 12.3:
#
#   1. `entire contents of front window` returns ZERO elements for Logic, even
#      when it is frontmost, while `every UI element` returns them normally. Any
#      dump built on `entire contents` silently yields "" and looks like an empty
#      window rather than a broken query.
#   2. Storing UI element references in a list and re-reading them after mutating
#      that list invalidates them (AppleEvent handler failed, -10000). So the walk
#      recurses through a handler parameter instead of a worklist.
#
# Indentation encodes depth. Capped so a deep hierarchy can't hang the tool.
_UI_DUMP_SCRIPT = """
property nodeCount : 0
property maxNodes : 600

on dumpEl(el, d, maxD)
    if nodeCount > maxNodes then return ""
    set nodeCount to nodeCount + 1
    set out to ""
    tell application "System Events"
        set pad to ""
        repeat d times
            set pad to pad & "  "
        end repeat
        set info to pad
        try
            set info to info & ((role of el) as string)
        on error
            set info to info & "?"
        end try
        try
            set nm to (name of el) as string
            if nm is not "missing value" and nm is not "" then set info to info & " | Name: " & nm
        end try
        try
            set tt to (title of el) as string
            if tt is not "missing value" and tt is not "" then set info to info & " | Title: " & tt
        end try
        try
            set ds to (description of el) as string
            if ds is not "missing value" and ds is not "" then set info to info & " | Desc: " & ds
        end try
        try
            set vl to (value of el) as string
            if vl is not "missing value" and vl is not "" then
                if (count of vl) > 60 then set vl to (text 1 thru 60 of vl) & "..."
                set info to info & " | Val: " & vl
            end if
        end try
        set out to out & info & linefeed
        if d < maxD then
            try
                set kids to every UI element of el
                repeat with k in kids
                    set out to out & my dumpEl(contents of k, d + 1, maxD)
                end repeat
            end try
        end if
    end tell
    return out
end dumpEl

set nodeCount to 0
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set w to front window
    end tell
end tell
return my dumpEl(w, 0, 5)
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
