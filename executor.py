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
