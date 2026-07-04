"""Build a new Logic Pro project pre-loaded with a track's stems.

Reliability: BEST-EFFORT UI scripting. Logic has no AppleScript dictionary, so
this drives the template chooser and a single Import Audio dialog via System
Events. Requires Logic to be running (the tool launches it if needed). If a
Logic update moves a dialog, re-derive selectors with
`entire contents of front window`. Process name is "Logic Pro Creator Studio".

v1 reports the analyzed tempo/key in the summary but does not set them in Logic.
"""

import subprocess
import time
from pathlib import Path

import executor
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

_PROC = 'tell process "Logic Pro Creator Studio"'
_CANONICAL = ("drums.wav", "bass.wav", "other.wav", "vocals.wav")


def _wavs_in(d: Path) -> list[str]:
    """Stem WAVs directly in d: canonical drums/bass/other/vocals first, else all *.wav."""
    canonical = [str(d / n) for n in _CANONICAL if (d / n).exists()]
    if canonical:
        return canonical
    return sorted(str(p) for p in d.glob("*.wav"))


def collect_stems(stems_dir: str) -> list[str]:
    """Absolute paths of the stem WAVs to import from a Stems/<model>/<track> folder.

    Prefers the canonical drums/bass/other/vocals.wav in that order; falls back
    to every *.wav (sorted). If handed a model folder (no WAVs directly, but one
    track subfolder that has them) it descends into that subfolder. Raises
    ToolError if the folder is missing, empty, or ambiguous (multiple tracks).
    """
    d = Path(stems_dir).expanduser()
    if not d.is_dir():
        raise ToolError(f"Not a folder: {stems_dir}")
    here = _wavs_in(d)
    if here:
        return here
    subdirs = [sub for sub in sorted(d.iterdir()) if sub.is_dir() and _wavs_in(sub)]
    if len(subdirs) == 1:
        return _wavs_in(subdirs[0])
    if len(subdirs) > 1:
        names = ", ".join(s.name for s in subdirs)
        raise ToolError(
            f"{stems_dir} holds multiple track folders ({names}) — pass one."
        )
    raise ToolError(f"No .wav files in {stems_dir}")


def _ensure_logic_running(timeout: float = 30.0) -> None:
    """Launch Logic Pro if needed and wait until System Events sees it."""
    if executor.logic_is_running():
        return
    subprocess.run(["open", "-a", "Logic Pro"], check=False)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if executor.logic_is_running():
            return
        time.sleep(1.0)
    raise ToolError("Logic Pro did not start within 30s — open it and retry.")


def _new_empty_project() -> None:
    """Cmd+N -> best-effort pick 'Empty Project' -> escape the New Tracks sheet.

    The template chooser is the most build-fragile step. If it moves, re-derive
    with `entire contents of front window` and update the click target.
    """
    script = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {_PROC}
        keystroke "n" using {{command down}}
        delay 1.2
        set picked to false
        try
            repeat with el in (entire contents of front window)
                try
                    set d to (description of el) as string
                    if d contains "Empty Project" then
                        click el
                        set picked to true
                        exit repeat
                    end if
                end try
            end repeat
        end try
        delay 0.4
        try
            click button "Choose" of front window
        end try
        delay 1.0
        key code 53
    end tell
end tell
"""
    executor.run_applescript(script, timeout=20)


def _import_stems(stems_dir: str) -> None:
    """Drive one File > Import > Audio File dialog to add every file in
    stems_dir to new tracks at the playhead."""
    folder = executor.as_applescript_str(str(Path(stems_dir).expanduser()))
    script = f"""
tell application "Logic Pro" to activate
tell application "System Events"
    {_PROC}
        key code 36
        delay 0.3
        click menu item "Audio File..." of menu "Import" of menu item "Import" of menu "File" of menu bar 1
        delay 1.0
        keystroke "g" using {{command down, shift down}}
        delay 0.5
        keystroke "{folder}"
        delay 0.3
        key code 36
        delay 0.6
        key code 36
        delay 0.6
        keystroke "a" using {{command down}}
        delay 0.3
        key code 36
        delay 1.2
        key code 36
    end tell
end tell
"""
    executor.run_applescript(script, timeout=30)


def build_project_with_stems(
    stems_dir: str, tempo: float | None = None, key: str | None = None
) -> str:
    """Create a new Logic project with the stems in stems_dir as audio tracks.

    Best-effort UI scripting: launches Logic if needed, opens an empty project,
    and imports the stems in one dialog. tempo/key are reported for manual entry
    (v1 does not set them). Returns a summary string.
    """
    stems = collect_stems(stems_dir)
    _ensure_logic_running()
    _new_empty_project()
    _import_stems(stems_dir)
    names = ", ".join(Path(s).name for s in stems)
    lines = [
        f"Created a new Logic project and imported {len(stems)} stems as tracks: {names}.",
        "Verify the tracks appear at bar 1; if the import sheet differed, re-run "
        "or complete it in Logic.",
    ]
    if tempo is not None:
        lines.append(f"Set the project tempo to {tempo} (not auto-set in v1).")
    if key:
        lines.append(f"Analyzed key: {key} (set manually if you want it labeled).")
    lines.append("Save with Cmd+S when it looks right.")
    return " ".join(lines)


def register_build_tools(mcp: FastMCP) -> None:

    @mcp.tool(
        annotations={
            "title": "New Logic project from stems",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    def logic_new_project_with_stems(
        stems_dir: str, tempo: float | None = None, key: str | None = None
    ) -> str:
        """Create a new Logic Pro project with a folder of stems loaded as tracks.

        stems_dir is a Stems/<model>/<track> folder. Best-effort UI scripting;
        Logic is launched if not already open. tempo/key are reported, not set.
        """
        return build_project_with_stems(stems_dir, tempo, key)
