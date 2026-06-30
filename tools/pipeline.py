"""Asset-pipeline tools — download, stem separation, vocal chopping.

These wrap the shell functions in `<music_root>/lib/music-core.sh` (the single
source of truth) rather than reimplementing demucs/gamdl/yt-dlp logic. Reliable
and deterministic, but stem separation and downloads can be slow (minutes).

External tools required on PATH: demucs, gamdl/yt-dlp, ffmpeg. Apple Music
downloads use the existing interactive cookie flow and are NOT for untrusted URLs.
"""

import shlex
import subprocess

import config
from fastmcp import FastMCP

# Generous default — demucs on a full track can take minutes.
_DEFAULT_TIMEOUT = 1800

_STEM_MODES = ("instrumental", "4stem", "6stem")
_SENSITIVITIES = ("tight", "loose")


def build_core_command(func: str, args: list[str]) -> list[str]:
    """Build the zsh command that sources music-core.sh and calls `func`.

    Pure (no side effects) so it can be unit-tested. Args are individually
    quoted; the core lib path is resolved from config.
    """
    quoted = " ".join(shlex.quote(a) for a in args)
    inner = f"source {shlex.quote(str(config.core_lib()))}; {func} {quoted}".strip()
    return ["zsh", "-c", inner]


def _run_core(func: str, args: list[str], timeout: int = _DEFAULT_TIMEOUT) -> str:
    if not config.core_lib().exists():
        raise RuntimeError(
            f"music-core.sh not found at {config.core_lib()}. Set "
            "LOGIC_STUDIO_MUSIC_ROOT to your music workspace root."
        )
    result = subprocess.run(
        build_core_command(func, args),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    if result.returncode != 0:
        raise RuntimeError(f"{func} failed: {err or out or '(no output)'}")
    return out


def register_pipeline_tools(mcp: FastMCP) -> None:

    @mcp.tool(
        annotations={
            "title": "Download audio from URL",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    def pipeline_download(url: str) -> str:
        """Download audio from an Apple Music / SoundCloud / YouTube / Bandcamp URL.

        Routes by host (Apple Music via gamdl, others via yt-dlp) and saves into
        the workspace. Returns the output directory. Apple Music needs the
        interactive cookie setup already configured.
        """
        dest = str(config.music_root() / "Apple Music")
        return _run_core("download_url", [url, dest]) or f"Downloaded to {dest}"

    @mcp.tool(
        annotations={
            "title": "Separate stems",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    def pipeline_separate_stems(input_path: str, mode: str = "instrumental") -> str:
        """Split an audio file into stems with demucs. Returns the vocals.wav path.

        mode: 'instrumental' (vocals + backing), '4stem', or '6stem'. Slow —
        may take several minutes per track.
        """
        if mode not in _STEM_MODES:
            return f"Invalid mode '{mode}'. Use one of: {', '.join(_STEM_MODES)}"
        out = str(config.lib_path("stems"))
        return _run_core("separate_stems", [input_path, mode, out])

    @mcp.tool(
        annotations={
            "title": "Chop vocals into clips",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    def pipeline_chop_vocals(input_path: str, sensitivity: str = "loose") -> str:
        """Slice a vocals.wav (or Stems folder) into phrase clips via silence detection.

        sensitivity: 'tight' (more, shorter clips) or 'loose' (fewer, longer).
        Clips land in Samples/Vocals/<source>/.
        """
        if sensitivity not in _SENSITIVITIES:
            return f"Invalid sensitivity '{sensitivity}'. Use 'tight' or 'loose'."
        out = str(config.music_root() / "Samples" / "Vocals")
        return _run_core("chop_vocals", [input_path, out, sensitivity])


    @mcp.tool(
        annotations={
            "title": "Run full pipeline",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    def pipeline_run_full(
        url: str, stem_mode: str = "instrumental", chop_sensitivity: str = "loose"
    ) -> str:
        """Download a URL, separate stems, then chop vocals — the full chain.

        Mirrors the `music` CLI's pipeline: downloads, detects the new tracks by
        timestamp, separates each, and chops the resulting vocals. Can take a
        while (download + demucs per track).
        """
        if stem_mode not in _STEM_MODES:
            return f"Invalid stem_mode '{stem_mode}'. Use one of: {', '.join(_STEM_MODES)}"
        if chop_sensitivity not in _SENSITIVITIES:
            return f"Invalid chop_sensitivity '{chop_sensitivity}'. Use 'tight' or 'loose'."
        root = config.music_root()
        am = str(root / "Apple Music")
        stems = str(config.lib_path("stems"))
        vocals_out = str(root / "Samples" / "Vocals")
        script = f"""
source {shlex.quote(str(config.core_lib()))}
STAMP=$(date +%s)
download_url {shlex.quote(url)} {shlex.quote(am)}
new_files=$(find_new_m4a {shlex.quote(am)} "$STAMP")
[[ -z "$new_files" ]] && {{ echo "Nothing downloaded."; exit 0; }}
echo "$new_files" | while read -r track; do
  vocals=$(separate_stems "$track" {shlex.quote(stem_mode)} {shlex.quote(stems)} | tail -1)
  [[ -f "$vocals" ]] && chop_vocals "$vocals" {shlex.quote(vocals_out)} {shlex.quote(chop_sensitivity)}
done
echo "Pipeline complete."
"""
        result = subprocess.run(
            ["zsh", "-c", script], capture_output=True, text=True, timeout=_DEFAULT_TIMEOUT
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if result.returncode != 0:
            raise RuntimeError(f"Pipeline failed: {err or out or '(no output)'}")
        return out or "Pipeline complete."
