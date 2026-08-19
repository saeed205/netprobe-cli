"""Allow `python -m netprobe` alongside the installed console script.

This indirection matters: running `python -m netprobe.cli` would load the CLI
module twice - once as ``__main__`` and once as ``netprobe.cli`` when a command
module imports it - leaving the command registry in the copy nobody reads.
"""

from .cli import main

raise SystemExit(main())
