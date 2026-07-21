"""Configuration for the unified Logic Pro Creator Studio MCP.

Resolves the music workspace root (where the download/stems/chop pipeline and
the Projects/Samples/Stems/Exports library live). Override with the
LOGIC_STUDIO_MUSIC_ROOT environment variable; otherwise defaults to
~/Developer/music.
"""

import os
from pathlib import Path

_DEFAULT_ROOT = Path.home() / "Developer" / "music"

LOGIC_PROCESS_NAME = "Logic Pro Creator Studio"

# The macOS application name used to launch/activate Logic. On this machine the
# app is "Logic Pro Creator Studio.app", not "Logic Pro" — override with
# LOGIC_APP_NAME for a stock install.
LOGIC_APP_NAME = os.environ.get("LOGIC_APP_NAME", "Logic Pro Creator Studio")


def music_root() -> Path:
    """Absolute path to the music workspace root."""
    env = os.environ.get("LOGIC_STUDIO_MUSIC_ROOT")
    return Path(env).expanduser().resolve() if env else _DEFAULT_ROOT


def core_lib() -> Path:
    """Path to lib/music-core.sh (the shell pipeline source of truth)."""
    return music_root() / "lib" / "music-core.sh"


# Canonical library subfolders (see folder-structure spec).
LIBRARY_DIRS = {
    "projects": ("Projects",),
    "projects_active": ("Projects", "Active"),
    "projects_archive": ("Projects", "Archive"),
    "projects_templates": ("Projects", "Templates"),
    "samples": ("Samples",),
    "stems": ("Stems",),
    "exports": ("Exports",),
    "exports_drafts": ("Exports", "Drafts"),
    "exports_finals": ("Exports", "Finals"),
}

SAMPLE_CATEGORIES = ("One-Shots", "Loops", "Chops", "Kits", "Vocals")


def lib_path(key: str) -> Path:
    """Resolve a canonical library dir key to an absolute path."""
    parts = LIBRARY_DIRS[key]
    return music_root().joinpath(*parts)
