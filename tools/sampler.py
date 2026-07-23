import executor
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError


def register_sampler_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def logic_load_into_quick_sampler(file_path: str) -> str:
        """Create a new Software Instrument track and load the file into Quick Sampler.

        Requires an open project in Logic Pro.
        """
        path = Path(file_path).expanduser()
        if not path.is_file():
            raise ToolError(f"File not found: {file_path}")

        # Create a Software Instrument track (Option+Cmd+S); the caller then
        # loads the sample into Quick Sampler manually (best-effort — importing
        # the file itself isn't scripted here).
        script = executor.keystroke_block(
            '        keystroke "s" using {command down, option down}\n        delay 1.5'
        )
        try:
            executor.run_ui(script, timeout=20)
            return f"Created Software Instrument track. Please load {path.name} into Quick Sampler."
        except Exception as exc:
            raise ToolError(f"Failed loading to Quick Sampler: {exc}")
