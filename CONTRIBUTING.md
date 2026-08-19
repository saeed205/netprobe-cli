# Contributing

## Setup

No dependencies to install for the library or the tests:

```bash
git clone https://github.com/saeed205/netprobe-cli
cd netprobe-cli
python -m unittest discover -s tests -v
```

Only the linter needs installing:

```bash
pip install ruff
ruff check .
```

## Adding a command

Commands self-register, so nothing in the argument parser needs editing.

1. Create `netprobe/yourcommand.py`.
2. Write the logic as **plain functions that take and return data** - no
   printing, no `argparse` types in the signature. That is what makes it
   testable without a network.
3. Add a `_handle(args)` that calls those functions and hands the rows to
   `output.emit()`.
4. Register the parser:

   ```python
   from .cli import register

   @register
   def _add_parser(subparsers):
       p = subparsers.add_parser("yourcommand", help="one line of help")
       p.add_argument("target")
       p.set_defaults(handler=_handle)
   ```

5. Import the module in `netprobe/commands.py` and add it to `_MODULES`,
   keeping both alphabetical.

## House rules

- **Standard library only.** A diagnostics tool that cannot be installed on a
  locked-down jump box is not much use. A dependency needs a strong argument.
- **Python 3.9 is the floor.** Typing-module spellings (`Dict`, `Optional`)
  are used deliberately - see the comment in `ruff.toml` before "modernising"
  them.
- **Exit status is an interface.** `0` success, `1` the check failed, `2`
  usage error. People put these commands in monitoring checks; do not return
  `0` for a failed probe.
- **Never print from a helper.** Rendering belongs in `output.py` so that
  `--json` keeps working everywhere for free.

## Tests

Plain `unittest`. Anything that opens a socket does not belong in the suite -
CI runs on sandboxed runners with no egress. Test the parsing, the arithmetic
and the precedence rules; those are where the bugs actually live.

Worth testing explicitly: boundary values (`/31`, `/32`, empty input, single
element), and anything where a plausible-looking implementation gives a wrong
answer.

## Pull requests

Say what changed and why. If you made a non-obvious choice, put the reasoning
in the description - that is the part nobody can reconstruct from the diff six
months later.
