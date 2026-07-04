#!/usr/bin/env python3
"""CLI wrapper: build a new Logic project from a stems folder.

Invoked by the music toolkit menu so the shell does not need an MCP client.
Usage: build_project.py <stems_dir> [--tempo BPM] [--key KEY]
"""

import argparse
import sys

from fastmcp.exceptions import ToolError
from tools.build import build_project_with_stems


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Build a Logic project from a stems folder"
    )
    ap.add_argument("stems_dir")
    ap.add_argument("--tempo", type=float, default=None)
    ap.add_argument("--key", default=None)
    return ap.parse_args(argv)


def main(argv: list[str]) -> int:
    ns = parse_args(argv)
    try:
        print(build_project_with_stems(ns.stems_dir, ns.tempo, ns.key))
    except ToolError as exc:
        print(f"build_project: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
