import subprocess


class NoProjectWindowError(RuntimeError):
    """Logic is running but has no open project window (e.g. the chooser is up)."""


def as_applescript_str(value: str) -> str:
    """Escape a Python string for safe embedding in an AppleScript double-quoted literal.

    AppleScript string literals only need backslash and double-quote escaped.
    Escape backslash first so the added escapes aren't themselves re-escaped.
    Use for any caller-supplied value interpolated into a script (paths, menu
    names) to prevent the script breaking or AppleScript injection.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


def run_applescript(script: str, timeout: int = 10) -> str:
    result = subprocess.run(
        ["osascript"],
        input=script,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip() or "(no output)"
        low = err.lower()
        if "assistive access" in low or "not allowed" in low or "1002" in low:
            raise RuntimeError(
                "Accessibility permission not granted. Enable it for your terminal/IDE in "
                "System Settings > Privacy & Security > Accessibility, then retry. "
                f"(osascript: {err})"
            )
        if "isn't running" in low or "can't get process" in low or "not running" in low:
            raise RuntimeError(
                "Logic Pro Creator Studio doesn't appear to be running — open it first. "
                f"(osascript: {err})"
            )
        if "invalid index" in low or "get window" in low or "-1719" in low:
            raise NoProjectWindowError(
                "No project window open in Logic Pro Creator Studio — open or create a "
                f"project first. (osascript: {err})"
            )
        raise RuntimeError(f"osascript: {err}")
    return result.stdout.strip()


def logic_is_running() -> bool:
    script = """
tell application "System Events"
    return (name of every process) contains "Logic Pro Creator Studio"
end tell
"""
    try:
        return run_applescript(script).lower() == "true"
    except RuntimeError:
        return False
