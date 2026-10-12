"""Command-line entry point: `random-walk` and `py -m random_walk` both run main()."""

from __future__ import annotations

import sys


def main() -> int:
    # Imported here so the core package can be used without loading Qt.
    from random_walk.gui.app import run

    return run()


if __name__ == "__main__":
    sys.exit(main())
