"""Bounce / export tools for Logic Pro Creator Studio.

Reliability: BEST-EFFORT. Bouncing is a two-dialog flow (Bounce settings →
Save dialog) with no AppleScript dictionary, so these tools drive the menu and
optionally accept defaults. They cannot reliably read the final file path back;
they return the conventional Exports location for the caller to poll.
"""

import executor
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# Convention from the music workspace folder structure.
_EXPORTS_HINT = "~/Developer/music/Exports/Drafts/"


def register_bounce_tools(mcp: FastMCP) -> None:

    @mcp.tool(
        annotations={
            "title": "Bounce project (open dialog)",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def logic_bounce(confirm_defaults: bool = False) -> str:
        """Start a Project bounce in Logic Pro (File > Bounce > Project or Section...).

        Opens the Bounce settings dialog. If confirm_defaults is True, presses
        Return twice to accept the current bounce settings and the save dialog
        defaults — use only when you trust the existing settings, since it
        commits a render. Leave False to let the user complete the dialog.

        Returns guidance and the conventional Exports path to poll for output.
        """
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        open_script = executor.keystroke_block(
            '        click menu item "Project or Section..." of menu "Bounce" '
            'of menu item "Bounce" of menu "File" of menu bar 1'
        )
        try:
            executor.run_applescript(open_script)
        except RuntimeError as exc:
            # Menu structure varies; fall back to the flat menu path.
            fallback = executor.keystroke_block(
                '        click menu item "Bounce" of menu "File" of menu bar 1'
            )
            try:
                executor.run_applescript(fallback)
            except RuntimeError:
                raise RuntimeError(
                    f"Could not open the Bounce menu ({exc}). Inspect with "
                    "'entire contents of menu \"File\" of menu bar 1' to find the item name."
                )

        if confirm_defaults:
            confirm_script = executor.keystroke_block(
                "        delay 0.5\n        key code 36\n        delay 0.8\n        key code 36"
            )
            executor.run_applescript(confirm_script)
            return f"Bounce started with default settings. Check {_EXPORTS_HINT}"
        return (
            "Bounce settings dialog opened. Complete it in Logic, or call "
            f"logic_bounce(confirm_defaults=True) to accept defaults. Output goes to {_EXPORTS_HINT}"
        )

    @mcp.tool(
        annotations={
            "title": "Open Export menu",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    def logic_export(item_name: str = "All MIDI as MIDI File...") -> str:
        """Trigger a File > Export submenu item in Logic Pro.

        item_name defaults to MIDI export; pass another File > Export item name
        verbatim (e.g. 'Selection as Audio File...'). Opens its dialog.
        """
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        item = executor.as_applescript_str(item_name)
        script = executor.keystroke_block(
            f'        click menu item "{item}" of menu "Export" '
            'of menu item "Export" of menu "File" of menu bar 1'
        )
        executor.run_applescript(script)
        return f"Opened Export > {item_name}"
