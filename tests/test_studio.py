"""Unit tests for the deterministic parts of the studio MCP.

Covers config resolution, the pipeline command-builder (pure), and library
filesystem ops on a temp workspace. App-control tools (System Events) are not
unit-tested here — they need a live Logic session.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from tools import library, pipeline


# ---- config ----

def test_music_root_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGIC_STUDIO_MUSIC_ROOT", str(tmp_path))
    assert config.music_root() == tmp_path.resolve()


def test_core_lib_path(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGIC_STUDIO_MUSIC_ROOT", str(tmp_path))
    assert config.core_lib() == tmp_path.resolve() / "lib" / "music-core.sh"


# ---- pipeline command builder (pure) ----

def test_build_core_command_quotes_args(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGIC_STUDIO_MUSIC_ROOT", str(tmp_path))
    cmd = pipeline.build_core_command("separate_stems", ["/a b/x.m4a", "instrumental", "/out"])
    assert cmd[0] == "zsh" and cmd[1] == "-c"
    assert "separate_stems" in cmd[2]
    assert "'/a b/x.m4a'" in cmd[2]  # space-containing path is quoted
    assert "source" in cmd[2]


def test_build_core_command_handles_special_chars(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGIC_STUDIO_MUSIC_ROOT", str(tmp_path))
    cmd = pipeline.build_core_command("download_url", ["https://x.com/a;rm -rf /", "/out"])
    # The malicious-looking arg must be single-quoted, not interpreted.
    assert "'https://x.com/a;rm -rf /'" in cmd[2]


# ---- library fixtures ----

@pytest.fixture
def workspace(tmp_path):
    for sub in (
        "Projects/Active", "Projects/Archive", "Projects/Templates",
        "Samples/Loops", "Samples/Chops", "Exports/Drafts", "Exports/Finals",
        "Stems/htdemucs/Song A",
    ):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "Projects/Templates/Trap.logicx").mkdir()
    (tmp_path / "Projects/Active/Beat1.logicx").mkdir()
    (tmp_path / "Samples/Loops/loop1.wav").write_bytes(b"x")
    (tmp_path / "Exports/Drafts/draft1.wav").write_bytes(b"x")
    return tmp_path


def test_list_projects(workspace):
    assert library.list_projects(workspace, "Active") == ["Beat1.logicx"]
    assert library.list_projects(workspace, "Archive") == []


def test_list_samples(workspace):
    samples = library.list_samples(workspace, "Loops")
    assert samples["Loops"] == ["loop1.wav"]


def test_list_stems(workspace):
    assert library.list_stems(workspace) == ["htdemucs/Song A"]


def test_new_project_from_template(workspace):
    dest = library.new_project_from_template(workspace, "Trap", "MyBeat")
    assert dest.exists()
    assert dest.name == "MyBeat.logicx"
    assert "MyBeat.logicx" in library.list_projects(workspace, "Active")


def test_new_project_missing_template(workspace):
    with pytest.raises(FileNotFoundError):
        library.new_project_from_template(workspace, "Nope", "X")


def test_archive_project(workspace):
    dest = library.archive_project(workspace, "Beat1")
    assert dest.exists()
    assert library.list_projects(workspace, "Active") == []
    assert "Beat1.logicx" in library.list_projects(workspace, "Archive")


def test_promote_export_write_once(workspace):
    dest = library.promote_export(workspace, "draft1.wav", "final1.wav")
    assert dest.exists()
    # Second promote to same final name must refuse (write-once).
    with pytest.raises(FileExistsError):
        library.promote_export(workspace, "draft1.wav", "final1.wav")


# ---- pagination helper (pure) ----

def test_paginate_first_page():
    items = [f"item{i}" for i in range(10)]
    page = library.paginate(items, limit=3, offset=0)
    assert page["items"] == ["item0", "item1", "item2"]
    assert page["total"] == 10
    assert page["offset"] == 0
    assert page["limit"] == 3
    assert page["returned"] == 3
    assert page["has_more"] is True


def test_paginate_last_page_no_more():
    items = [f"item{i}" for i in range(5)]
    page = library.paginate(items, limit=10, offset=0)
    assert page["items"] == items
    assert page["returned"] == 5
    assert page["has_more"] is False


def test_paginate_offset_beyond_end():
    items = ["a", "b", "c"]
    page = library.paginate(items, limit=5, offset=10)
    assert page["items"] == []
    assert page["returned"] == 0
    assert page["total"] == 3
    assert page["has_more"] is False


def test_paginate_middle_slice_has_more():
    items = [f"item{i}" for i in range(10)]
    page = library.paginate(items, limit=2, offset=4)
    assert page["items"] == ["item4", "item5"]
    assert page["has_more"] is True


# ---- build: stem collection (pure) ----

from fastmcp.exceptions import ToolError
from tools import build


def test_collect_stems_canonical_order(tmp_path):
    for n in ("vocals.wav", "drums.wav", "bass.wav", "other.wav"):
        (tmp_path / n).write_bytes(b"RIFF")
    got = build.collect_stems(str(tmp_path))
    assert [Path(p).name for p in got] == ["drums.wav", "bass.wav", "other.wav", "vocals.wav"]


def test_collect_stems_fallback_all_wavs(tmp_path):
    (tmp_path / "guitar.wav").write_bytes(b"RIFF")
    (tmp_path / "piano.wav").write_bytes(b"RIFF")
    got = build.collect_stems(str(tmp_path))
    assert sorted(Path(p).name for p in got) == ["guitar.wav", "piano.wav"]


def test_collect_stems_no_wavs_raises(tmp_path):
    with pytest.raises(ToolError):
        build.collect_stems(str(tmp_path))


def test_collect_stems_missing_dir_raises(tmp_path):
    with pytest.raises(ToolError):
        build.collect_stems(str(tmp_path / "nope"))


def test_build_tool_registers():
    from fastmcp import FastMCP
    m = FastMCP("t")
    build.register_build_tools(m)  # must not raise


def test_build_cli_parses_args():
    import build_project
    ns = build_project.parse_args(["/x/Stems/htdemucs/Song", "--tempo", "161.5", "--key", "Am"])
    assert ns.stems_dir == "/x/Stems/htdemucs/Song"
    assert ns.tempo == 161.5
    assert ns.key == "Am"


def test_build_cli_defaults():
    import build_project
    ns = build_project.parse_args(["/x/Stems/htdemucs/Song"])
    assert ns.tempo is None and ns.key is None


def test_collect_stems_descends_single_track(tmp_path):
    model = tmp_path / "htdemucs_6s"
    track = model / "Song"
    track.mkdir(parents=True)
    for n in ("drums.wav", "bass.wav", "other.wav", "vocals.wav"):
        (track / n).write_bytes(b"RIFF")
    got = build.collect_stems(str(model))
    assert [Path(p).name for p in got] == ["drums.wav", "bass.wav", "other.wav", "vocals.wav"]


def test_collect_stems_ambiguous_multiple_tracks_raises(tmp_path):
    model = tmp_path / "htdemucs_6s"
    for t in ("SongA", "SongB"):
        (model / t).mkdir(parents=True)
        (model / t / "vocals.wav").write_bytes(b"RIFF")
    with pytest.raises(ToolError):
        build.collect_stems(str(model))
