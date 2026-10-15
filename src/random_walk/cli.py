"""Command-line entry point: `random-walk` and `py -m random_walk` both run main()."""

from __future__ import annotations

import argparse
import sys

from random_walk import __version__


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="random-walk", description="1D random walk explorer")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parse_args(argv)
    # Imported here so the core package (and --help) work without loading Qt.
    from random_walk.gui.app import run

    return run()


if __name__ == "__main__":
    sys.exit(main())
