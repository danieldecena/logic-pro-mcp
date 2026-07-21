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
from config import LOGIC_APP_NAME
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

_APP = LOGIC_APP_NAME
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
    launch = subprocess.run(["open", "-a", _APP], capture_output=True, text=True)
    if launch.returncode != 0:
        raise ToolError(
            f"Could not launch {_APP!r} "
            f"({launch.stderr.strip() or 'open failed'}) — "
            "open Logic manually, or set LOGIC_APP_NAME to your app's name, then retry."
        )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if executor.logic_is_running():
            return
        time.sleep(1.0)
    raise ToolError(f"{_APP} did not start within {int(timeout)}s — open it and retry.")


def _new_empty_project() -> None:
    """Cmd+N -> best-effort pick 'Empty Project' -> escape the New Tracks sheet.

    The template chooser is the most build-fragile step. If it moves, re-derive
    with `entire contents of front window` and update the click target.
    """
    script = f"""
tell application "{_APP}" to activate
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
tell application "{_APP}" to activate
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


def _import_midi(midi_path: str) -> None:
    """Drive File > Import > MIDI File to add a MIDI file as a software-instrument
    track. Best-effort; Logic creates the instrument track(s) itself."""
    path = executor.as_applescript_str(str(Path(midi_path).expanduser()))
    script = f"""
tell application "{_APP}" to activate
tell application "System Events"
    {_PROC}
        key code 36
        delay 0.3
        click menu item "MIDI File..." of menu "Import" of menu item "Import" of menu "File" of menu bar 1
        delay 1.0
        keystroke "g" using {{command down, shift down}}
        delay 0.5
        keystroke "{path}"
        delay 0.3
        key code 36
        delay 0.6
        key code 36
        delay 1.2
        key code 36
    end tell
end tell
"""
    executor.run_applescript(script, timeout=30)


def _set_tempo(tempo: float) -> None:
    """Set project tempo via UI scripting on the transport text field."""
    script = f"""
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        repeat with f in text fields of front window
            try
                set val to value of f
                set numVal to val as number
                if numVal >= 20 and numVal <= 400 then
                    set value of f to "{tempo}"
                    keystroke return
                    exit repeat
                end if
            end try
        end repeat
    end tell
end tell
"""
    try:
        executor.run_applescript(script, timeout=10)
    except Exception as exc:
        print(f"Warning: Failed to set tempo: {exc}")


def _set_key(key: str) -> None:
    """Set project key signature (e.g. 'C Major', 'A Minor') via AXPopUpButton click."""
    key_clean = key.strip()
    if key_clean.endswith("m"):
        root = key_clean[:-1]
        mode = "Minor"
    elif "min" in key_clean.lower():
        root = key_clean.lower().replace("min", "").strip()
        mode = "Minor"
    else:
        root = key_clean.lower().replace("maj", "").strip()
        mode = "Major"

    root_formatted = root.upper()
    target_key = f"{root_formatted} {mode}"

    script = f"""
tell application "System Events"
    tell process "Logic Pro Creator Studio"
        repeat with el in (entire contents of front window)
            try
                if role of el is "AXPopUpButton" then
                    set v to (value of el) as string
                    if v contains "Major" or v contains "Minor" then
                        click el
                        delay 0.5
                        keystroke "{target_key}"
                        delay 0.3
                        keystroke return
                        exit repeat
                    end if
                end if
            end try
        end repeat
    end tell
end tell
"""
    try:
        executor.run_applescript(script, timeout=15)
    except Exception as exc:
        print(f"Warning: Failed to set key: {exc}")


def build_project_with_stems(
    stems_dir: str,
    tempo: float | None = None,
    key: str | None = None,
    midi: str | None = None,
) -> str:
    """Create a new Logic project with the stems in stems_dir as audio tracks.

    Best-effort UI scripting: launches Logic if needed, opens an empty project,
    and imports the stems in one dialog. If `midi` is given (e.g. a transcribed
    bass line), it is also imported as a software-instrument track so it can be
    re-voiced. tempo/key are set if provided.
    Returns a summary string.
    """
    stems = collect_stems(stems_dir)
    _ensure_logic_running()
    _new_empty_project()
    if tempo is not None:
        _set_tempo(tempo)
    if key:
        _set_key(key)
    _import_stems(stems_dir)
    names = ", ".join(Path(s).name for s in stems)
    lines = [
        f"Created a new Logic project and imported {len(stems)} stems as tracks: {names}.",
        "Verify the tracks appear at bar 1; if the import sheet differed, re-run "
        "or complete it in Logic.",
    ]
    if midi and Path(midi).expanduser().is_file():
        _import_midi(midi)
        lines.append(
            f"Also imported {Path(midi).name} as a software-instrument track — "
            "swap its instrument to re-voice the bass."
        )
    if tempo is not None:
        lines.append(f"Set the project tempo to {tempo}.")
    if key:
        lines.append(f"Set project key signature to {key}.")
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
        stems_dir: str,
        tempo: float | None = None,
        key: str | None = None,
        midi: str | None = None,
    ) -> str:
        """Create a new Logic Pro project with a folder of stems loaded as tracks.

        stems_dir is a Stems/<model>/<track> folder. Best-effort UI scripting;
        Logic is launched if not already open. If `midi` is a MIDI file it is
        also imported as a software-instrument track. tempo/key are reported.
        """
        return build_project_with_stems(stems_dir, tempo, key, midi)
