"""Library tools — browse and organize the music workspace.

Pure filesystem operations over the workspace folder structure
(Projects/{Active,Archive,Templates}, Samples/*, Stems, Exports/{Drafts,Finals}).
The core functions take an explicit root so they can be unit-tested on a temp dir.
"""

import shutil
from pathlib import Path

import config
from fastmcp import FastMCP


def _ls(path: Path, want: str = "any") -> list[str]:
    """Sorted names directly under `path`. want: 'dir', 'file', or 'any'."""
    if not path.exists():
        return []
    names = []
    for p in sorted(path.iterdir()):
        if p.name.startswith("."):
            continue
        if want == "dir" and not p.is_dir():
            continue
        if want == "file" and not p.is_file():
            continue
        names.append(p.name)
    return names


def list_projects(root: Path, state: str = "Active") -> list[str]:
    return _ls(root / "Projects" / state, "any")


def list_samples(root: Path, category: str | None = None) -> dict[str, list[str]]:
    base = root / "Samples"
    cats = [category] if category else list(config.SAMPLE_CATEGORIES)
    return {c: _ls(base / c) for c in cats if (base / c).exists()}


def list_stems(root: Path) -> list[str]:
    # demucs writes Stems/<model>/<track>/; surface the track folders.
    base = root / "Stems"
    tracks: list[str] = []
    if base.exists():
        for model in sorted(base.iterdir()):
            if model.is_dir():
                tracks.extend(f"{model.name}/{t}" for t in _ls(model, "dir"))
    return tracks


def list_exports(root: Path, stage: str = "Drafts") -> list[str]:
    return _ls(root / "Exports" / stage, "file")


def new_project_from_template(root: Path, template: str, name: str) -> Path:
    """Copy a Templates/<template> bundle into Projects/Active/<name>.logicx."""
    tdir = root / "Projects" / "Templates"
    src = tdir / template
    if not src.exists():
        src = tdir / f"{template}.logicx"
    if not src.exists():
        raise FileNotFoundError(
            f"Template '{template}' not found in {tdir}. Available: {_ls(tdir) or '(none)'}"
        )
    dest_name = name if name.endswith(".logicx") else f"{name}.logicx"
    dest = root / "Projects" / "Active" / dest_name
    if dest.exists():
        raise FileExistsError(f"Project already exists: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)
    return dest


def archive_project(root: Path, name: str) -> Path:
    """Move a project from Projects/Active to Projects/Archive."""
    proj = name if name.endswith(".logicx") else f"{name}.logicx"
    src = root / "Projects" / "Active" / proj
    if not src.exists():
        raise FileNotFoundError(f"Active project not found: {src}")
    dest_dir = root / "Projects" / "Archive"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / proj
    if dest.exists():
        raise FileExistsError(f"Archive already has {proj}")
    shutil.move(str(src), str(dest))
    return dest


def promote_export(root: Path, draft_name: str, final_name: str) -> Path:
    """Copy a Drafts bounce to Exports/Finals — write-once (never overwrite)."""
    src = root / "Exports" / "Drafts" / draft_name
    if not src.exists():
        raise FileNotFoundError(f"Draft not found: {src}")
    finals = root / "Exports" / "Finals"
    finals.mkdir(parents=True, exist_ok=True)
    dest = finals / final_name
    if dest.exists():
        raise FileExistsError(
            f"Final already exists: {dest}. Finals are write-once — use a versioned name."
        )
    shutil.copy2(src, dest)
    return dest


def _fmt(items: list[str], empty: str) -> str:
    return "\n".join(items) if items else empty


def register_library_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations={"title": "List projects", "readOnlyHint": True})
    def library_list_projects(state: str = "Active") -> str:
        """List Logic projects in Projects/<state>. state: Active, Archive, or Templates."""
        if state not in ("Active", "Archive", "Templates"):
            return "state must be Active, Archive, or Templates"
        items = list_projects(config.music_root(), state)
        return _fmt(items, f"No projects in {state}.")

    @mcp.tool(annotations={"title": "List samples", "readOnlyHint": True})
    def library_list_samples(category: str = "") -> str:
        """List sample files by category (One-Shots, Loops, Chops, Kits, Vocals). Empty = all."""
        result = list_samples(config.music_root(), category or None)
        if not result:
            return "No samples found."
        lines = []
        for cat, files in result.items():
            lines.append(f"## {cat} ({len(files)})")
            lines.extend(f"  {f}" for f in files) if files else lines.append("  (empty)")
        return "\n".join(lines)

    @mcp.tool(annotations={"title": "List stems", "readOnlyHint": True})
    def library_list_stems() -> str:
        """List separated stem folders (model/track) under Stems/."""
        return _fmt(list_stems(config.music_root()), "No stems yet.")

    @mcp.tool(annotations={"title": "List exports", "readOnlyHint": True})
    def library_list_exports(stage: str = "Drafts") -> str:
        """List exported files in Exports/<stage>. stage: Drafts or Finals."""
        if stage not in ("Drafts", "Finals"):
            return "stage must be Drafts or Finals"
        return _fmt(list_exports(config.music_root(), stage), f"No exports in {stage}.")

    @mcp.tool(
        annotations={"title": "New project from template", "readOnlyHint": False, "destructiveHint": False}
    )
    def library_new_project_from_template(template: str, name: str) -> str:
        """Copy a Templates/<template> bundle to Projects/Active/<name>.logicx."""
        try:
            dest = new_project_from_template(config.music_root(), template, name)
            return f"Created {dest}"
        except (FileNotFoundError, FileExistsError) as exc:
            return f"Error: {exc}"

    @mcp.tool(
        annotations={"title": "Archive project", "readOnlyHint": False, "destructiveHint": True}
    )
    def library_archive_project(name: str) -> str:
        """Move a project from Projects/Active to Projects/Archive."""
        try:
            dest = archive_project(config.music_root(), name)
            return f"Archived to {dest}"
        except (FileNotFoundError, FileExistsError) as exc:
            return f"Error: {exc}"

    @mcp.tool(
        annotations={"title": "Promote export to Finals", "readOnlyHint": False, "destructiveHint": False}
    )
    def library_promote_export(draft_name: str, final_name: str) -> str:
        """Copy a Drafts bounce to Exports/Finals (write-once — won't overwrite)."""
        try:
            dest = promote_export(config.music_root(), draft_name, final_name)
            return f"Promoted to {dest}"
        except (FileNotFoundError, FileExistsError) as exc:
            return f"Error: {exc}"
