#!/usr/bin/env python3
"""Thin CLI over the logic-pro-mcp AppleScript helpers.

Lets the Cowork Music Studio artifact drive Logic Pro through the Desktop
Commander bridge (start_process) instead of a live MCP connection. Reuses the
same executor.run_applescript scripts as the MCP tools so behavior matches.

Usage:  python logic_cli.py <command> [arg]
Commands:
  status | play | stop | record | gotostart | rewind | ff
  listtracks | mute | solo | save | newproject
  bounce [--confirm] | export [item] | project
"""
import re
import sys

import executor
import config

PROC = 'tell process "Logic Pro Creator Studio"'


def _keys(k):
    return f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {PROC}
        {k}
    end tell
end tell
"""


TOGGLE = _keys('keystroke " "')

_FIELD_SCRIPT = """
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set AppleScript's text item delimiters to "\n"
        set allFields to every text field of front window
        set vals to {}
        repeat with f in allFields
            try
                set fieldVal to value of f
                if fieldVal is not missing value then set end of vals to fieldVal
            end try
        end repeat
        set joined to vals as string
        set AppleScript's text item delimiters to ""
        return joined
    end tell
end tell
"""

_KEY_POPUP = """
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set ec to entire contents of front window
        repeat with el in ec
            try
                if role of el is "AXPopUpButton" then
                    set v to (value of el) as string
                    if v contains "Major" or v contains "Minor" then return v
                end if
            end try
        end repeat
        return ""
    end tell
end tell
"""

_LIST_SCRIPT = """
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        set trackNames to {}
        set ec to entire contents of front window
        repeat with el in ec
            try
                if role of el is "AXTextField" then
                    set p1 to (value of attribute "AXParent" of el)
                    set p2 to (value of attribute "AXParent" of p1)
                    if (role of p1 is "AXGroup") and (role of p2 is "AXList") then
                        set v to (value of el) as string
                        if v is not "" and v is not "missing value" then set end of trackNames to v
                    end if
                end if
            end try
        end repeat
        set AppleScript's text item delimiters to linefeed
        set joined to trackNames as string
        set AppleScript's text item delimiters to ""
        return joined
    end tell
end tell
"""

_POS_RE = re.compile(r"^\d+\s+\d+\s+\d+\s+\d+$")


def _fields():
    try:
        raw = executor.run_applescript(_FIELD_SCRIPT)
    except executor.NoProjectWindowError:
        return []
    return [v for v in raw.split("\n") if v.strip()]


def cmd_project():
    if not executor.logic_is_running():
        return "Logic Pro is not running"
    script = f"""
tell application "System Events"
    {PROC}
        set winTitle to name of front window
    end tell
end tell
"""
    try:
        title = executor.run_applescript(script)
    except executor.NoProjectWindowError:
        return "running, no project open"
    return title.split(" - ")[0].strip() if " - " in title else title


def cmd_status():
    running = executor.logic_is_running()
    if not running:
        print("running: no")
        return
    print("running: yes")
    print("project: " + cmd_project())
    # tempo
    bpm = None
    for v in _fields():
        try:
            f = float(v.strip())
            if 20.0 <= f <= 400.0:
                bpm = f
                break
        except ValueError:
            continue
    print("tempo: " + (f"{bpm:g}" if bpm else "?"))
    # key
    try:
        k = executor.run_applescript(_KEY_POPUP).strip()
    except Exception:
        k = ""
    print("key: " + (k or "?"))
    # bar position
    pos = "?"
    for v in _fields():
        s = v.strip()
        if _POS_RE.match(s):
            pos = s
            break
    print("bar: " + pos)


def cmd_listtracks():
    if not executor.logic_is_running():
        return "Logic Pro is not running"
    try:
        out = executor.run_applescript(_LIST_SCRIPT).strip()
    except executor.NoProjectWindowError as exc:
        return str(exc)
    if not out:
        return "No tracks found (project may be empty or UI tree differs)"
    names = [n for n in out.split("\n") if n.strip()]
    return "\n".join(f"{i}. {n}" for i, n in enumerate(names, 1))


def cmd_bounce(confirm=False):
    if not executor.logic_is_running():
        return "Logic Pro is not running"
    open_script = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {PROC}
        click menu item "Project or Section..." of menu "Bounce" of menu item "Bounce" of menu "File" of menu bar 1
    end tell
end tell
"""
    try:
        executor.run_applescript(open_script)
    except RuntimeError:
        fb = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {PROC}
        click menu item "Bounce" of menu "File" of menu bar 1
    end tell
end tell
"""
        executor.run_applescript(fb)
    if confirm:
        executor.run_applescript(_keys("delay 0.5\n        key code 36\n        delay 0.8\n        key code 36"))
        return "Bounce started with defaults. Check Exports/Drafts/"
    return "Bounce dialog opened — complete it in Logic (or pass --confirm)."


def cmd_export(item="All MIDI as MIDI File..."):
    if not executor.logic_is_running():
        return "Logic Pro is not running"
    it = executor.as_applescript_str(item)
    script = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {PROC}
        click menu item "{it}" of menu "Export" of menu item "Export" of menu "File" of menu bar 1
    end tell
end tell
"""
    executor.run_applescript(script)
    return f"Opened Export > {item}"


SIMPLE = {
    "play": (TOGGLE, "Playback toggled"),
    "stop": (TOGGLE, "Sent playback toggle (stops if playing)"),
    "record": (_keys('keystroke "r"'), "Recording started"),
    "gotostart": (_keys("key code 36"), "Playhead at start"),
    "rewind": (_keys('keystroke ","'), "Rewound"),
    "ff": (_keys('keystroke "."'), "Fast-forwarded"),
    "mute": (_keys('keystroke "m"'), "Toggled mute on selected track"),
    "solo": (_keys('keystroke "s"'), "Toggled solo on selected track"),
    "save": (_keys('keystroke "s" using {command down}'), "Saved"),
    "newproject": (_keys('keystroke "n" using {command down}'), "New project dialog opened"),
}


def main():
    if len(sys.argv) < 2:
        print("usage: logic_cli.py <command> [arg]")
        return 2
    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        if cmd == "status":
            cmd_status()
            return 0
        if cmd == "project":
            print(cmd_project()); return 0
        if cmd == "listtracks":
            print(cmd_listtracks()); return 0
        if cmd == "bounce":
            print(cmd_bounce(confirm=(arg == "--confirm"))); return 0
        if cmd == "export":
            print(cmd_export(arg or "All MIDI as MIDI File...")); return 0
        if cmd in SIMPLE:
            if cmd not in ("play", "stop") and cmd not in ("save", "newproject", "record", "gotostart", "rewind", "ff") and not executor.logic_is_running():
                print("Logic Pro is not running"); return 1
            script, msg = SIMPLE[cmd]
            executor.run_applescript(script)
            print(msg); return 0
        print(f"unknown command: {cmd}")
        return 2
    except Exception as exc:  # surface AppleScript/permission errors to the artifact
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
