"""Command-line entry point: `random-walk` and `py -m random_walk` both run main()."""

from __future__ import annotations

import sys

PLACEHOLDER = """\
random-walk: the GUI is being rebuilt.

The simulation core (random_walk.simulation, .theory, .params, .playback) is available
as a library. The previous Dear PyGui interface is on the ui_prototype branch
(tag dpg-final):

    git checkout ui_prototype
"""


def main() -> int:
    print(PLACEHOLDER, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
