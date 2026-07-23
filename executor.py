import subprocess
import time

import config

# Single source of truth for how AppleScript addresses Logic. The application
# name (used by `tell application ... to activate` and to launch) and the
# System Events process name are BOTH configurable via config.py — on this
# machine the app is "Logic Pro Creator Studio", on a stock install both are
# "Logic Pro". Never hardcode either in a tool script; interpolate these.
APP = config.LOGIC_APP_NAME
PROC = config.LOGIC_PROCESS_NAME
ACTIVATE = f'tell application "{APP}" to activate'
TELL_PROC = f'tell process "{PROC}"'


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


def keystroke_block(body: str) -> str:
    """Wrap System Events `body` in activate + `tell process` boilerplate.

    `body` is inserted verbatim (indent it yourself), so AppleScript brace
    literals such as `{command down}` are preserved — do NOT f-string them at
    the call site. Interpolate caller values into `body` before passing it in.
    """
    return (
        f"{ACTIVATE}\n"
        'tell application "System Events"\n'
        f"    {TELL_PROC}\n"
        f"{body}\n"
        "    end tell\n"
        "end tell\n"
    )


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
        if (
            "-1728" in err
            or "-10814" in err
            or "isn’t running" in low
            or "isn't running" in low
        ):
            # -1728: app name doesn't resolve (wrong LOGIC_APP_NAME). -10814: no
            # such application. Either way the addressed app couldn't be found.
            raise RuntimeError(
                f"Could not address {APP!r}. If your Logic install uses a different "
                "name, set LOGIC_APP_NAME (and LOGIC_PROCESS_NAME) in the environment. "
                f"(osascript: {err})"
            )
        if (
            "can't get process" in low
            or "can’t get process" in low
            or "not running" in low
        ):
            raise RuntimeError(
                f"{PROC} doesn't appear to be running — open it first. "
                f"(osascript: {err})"
            )
        if "invalid index" in low or "get window" in low or "-1719" in low:
            raise NoProjectWindowError(
                f"No project window open in {PROC} — open or create a "
                f"project first. (osascript: {err})"
            )
        raise RuntimeError(f"osascript: {err}")
    return result.stdout.strip()


def logic_is_running() -> bool:
    script = f"""
tell application "System Events"
    return (name of every process) contains "{PROC}"
end tell
"""
    try:
        return run_applescript(script).lower() == "true"
    except RuntimeError:
        return False


def ensure_logic_running(timeout: float = 40.0) -> None:
    """Launch Logic (via LOGIC_APP_NAME) if it isn't already running, then wait
    until System Events sees the process. Raises if it doesn't come up in time.

    Uses `open -g` so launching doesn't steal focus from the user. First launch
    can be slow; the wait is generous.
    """
    if logic_is_running():
        return
    subprocess.run(["open", "-g", "-a", APP], check=False)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if logic_is_running():
            return
        time.sleep(1.0)
    raise RuntimeError(
        f"{APP} did not start within {int(timeout)}s. Open it manually, or set "
        "LOGIC_APP_NAME if your install has a different name, then retry."
    )


def run_ui(script: str, timeout: int = 10) -> str:
    """Ensure Logic is running (launching it if needed), then run `script`.

    Use for action tools (keystrokes, menu clicks) so a not-running Logic is
    launched rather than erroring. Read-only tools that want to report the
    not-running state themselves should call run_applescript directly.
    """
    ensure_logic_running()
    return run_applescript(script, timeout=timeout)
