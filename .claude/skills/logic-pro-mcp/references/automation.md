# Logic Pro Automation Reference

AppleScript / System Events recipes for each feature area. All scripts assume Logic Pro is open.

---

## Transport Controls

### Keyboard shortcuts (Tier 1 — always prefer)

| Action | Shortcut | key code / keystroke |
|--------|----------|----------------------|
| Play / Stop | Space | `keystroke " "` |
| Record | R | `keystroke "r"` |
| Go to Start | Return | `key code 36` |
| Go to End | End / Fn+Right | `key code 119` |
| Rewind (step) | , | `keystroke ","` |
| Fast Forward (step) | . | `keystroke "."` |
| Cycle / Loop on | C | `keystroke "c"` |
| Punch In/Out | / | `keystroke "/"` |

Template:
```applescript
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke " "
    end tell
end tell
```

---

## Project Management

### Open a project
```applescript
tell application "Logic Pro"
    open POSIX file "/Users/home/Music/MyProject.logicx"
end tell
```

### Save current project
```applescript
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "s" using {command down}
    end tell
end tell
```

### Get current project name (via window title)
Logic Pro window title format: `"ProjectName - Logic Pro"`
```applescript
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set winTitle to name of front window
    end tell
end tell
-- winTitle = "MyProject - Logic Pro Creator Studio"
-- parse: everything before " - Logic Pro"
```

### Create new project
```applescript
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "n" using {command down}
    end tell
end tell
-- A dialog may appear for template selection — handle via accessibility
```

---

## Track Management

### List tracks (via accessibility)
Logic Pro's main window has an AXTable containing track rows. Each row has AXTextField children.
```applescript
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set mainWindow to front window
        -- Track header area is typically the first AXScrollArea > AXTable
        set trackTable to (first UI element of mainWindow whose role is "AXScrollArea")
        set trackRows to every row of (first UI element of trackTable whose role is "AXTable")
        set trackNames to {}
        repeat with rowItem in trackRows
            try
                set trackName to value of (first UI element of rowItem whose role is "AXTextField")
                set end of trackNames to trackName
            end try
        end repeat
    end tell
end tell
```
Note: UI element hierarchy varies by Logic Pro version. If this fails, use `entire contents` to inspect.

### Add track (via menu)
```applescript
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        click menu item "New Track..." of menu "Track" of menu bar 1
    end tell
end tell
-- A dialog appears — navigate via accessibility or press Return to accept defaults
```

### Mute track (keyboard shortcut)
Select the track first (click), then:
```applescript
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "m"
    end tell
end tell
```

### Solo track
```applescript
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "s"
    end tell
end tell
```

---

## Session State

### Read tempo (via transport bar accessibility)
The transport bar shows tempo in an AXTextField. The exact path depends on Logic version.
Strategy: search for AXTextField whose value matches a number (the tempo):
```applescript
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set allFields to every text field of front window
        -- filter by value matching BPM range (60–300)
    end tell
end tell
```
Easier fallback: Read `~/Library/Preferences/com.apple.logic10.plist` (requires `defaults read`).

### Read project settings from .logicx bundle
A `.logicx` project is a bundle (directory). The project XML is inside:
```
MyProject.logicx/
└── projectData          ← main XML file (no extension)
```
Read it:
```bash
cat "/path/to/MyProject.logicx/projectData" | grep -i tempo | head -5
```
Parse with Python's `xml.etree.ElementTree`.

---

## Menu Navigation

### Click any menu item
```applescript
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        click menu item "ITEM_NAME" of menu "MENU_NAME" of menu bar 1
    end tell
end tell
```

### Common menu paths
| Action | Menu | Item |
|--------|------|------|
| New Track | Track | New Track... |
| Bounce | File | Bounce > Project or Section... |
| Export MIDI | File | Export > All MIDI as MIDI File... |
| Undo | Edit | Undo |
| Redo | Edit | Redo |
| Preferences | Logic Pro | Settings... |
| Smart Controls | View | Show Smart Controls |
| Mixer | View | Show Mixer |

---

## Undo / Redo

```applescript
-- Undo
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "z" using {command down}
    end tell
end tell

-- Redo
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        keystroke "z" using {command down, shift down}
    end tell
end tell
```

---

## Inspect Accessibility Tree

When adding new tools, inspect Logic Pro's UI hierarchy first:
```python
# Run this from executor.py context to dump UI tree
script = '''
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        return entire contents of front window
    end tell
end tell
'''
```
This is verbose — pipe through grep to find specific elements.

---

## Python MCP Tool Template

```python
from fastmcp import FastMCP
import executor

def register_my_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def logic_my_action() -> str:
        """What this does — one line, Claude reads this to decide when to call it."""
        script = """
tell application "Logic Pro" to activate
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        -- AppleScript here
        -- Remember: no variable names starting with _
    end tell
end tell
"""
        executor.run_applescript(script)
        return "action completed"
```

---

## Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `osascript: execution error: System Events got an error` | Accessibility permission not granted | Grant in System Settings → Privacy → Accessibility |
| `Can't get process "Logic Pro"` | Logic Pro not running | Check `logic_get_status()` first |
| `Variable _ not defined` | Variable name starts with `_` | Rename variable (e.g. `trackName` not `_name`) |
| `Can't get menu item "X"` | Menu item name differs by locale/version | Use `entire contents of menu bar 1` to inspect |
