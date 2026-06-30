import subprocess


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
