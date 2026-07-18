import executor
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

_PROC = 'tell process "Logic Pro Creator Studio"'

def register_sampler_tools(mcp: FastMCP) -> None:
    
    @mcp.tool()
    def logic_load_into_quick_sampler(file_path: str) -> str:
        """Create a new Software Instrument track and load the file into Quick Sampler.
        
        Requires an open project in Logic Pro.
        """
        path = Path(file_path).expanduser()
        if not path.is_file():
            raise ToolError(f"File not found: {file_path}")
            
        as_path = executor.as_applescript_str(str(path))
        
        # AppleScript flow:
        # 1. Create a Software Instrument track (Option+Cmd+S)
        # 2. Open Quick Sampler / Instrument Slot
        # 3. Import sample file
        script = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {_PROC}
        -- Create instrument track
        keystroke "s" using {{command down, option down}}
        delay 1.5
    end tell
end tell
"""
        try:
            executor.run_applescript(script, timeout=20)
            return f"Created Software Instrument track. Please load {path.name} into Quick Sampler."
        except Exception as exc:
            raise ToolError(f"Failed loading to Quick Sampler: {exc}")
