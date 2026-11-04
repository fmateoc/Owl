"""Named downturn sequences (run-library design section 14.1, I11; build step 5b).

A scenario's downturn event names one of these sequences and a placement year; the builder
writes the run's `rates.csv` as the case's own rate path with the sequence's window overlaid
on the placement year (`library.builder.rates_table`). The windows and their sources live in
`src/owlplanner/data/downturn_sequences.toml` (the fork's data files carry their sources).
"""

from __future__ import annotations

from pathlib import Path

SEQUENCES_FILE = Path(__file__).resolve().parents[1] / "data" / "downturn_sequences.toml"

# The window's columns, in the rates table's order (rate_models.table.RATE_TABLE_COLUMNS).
WINDOW_COLUMNS = ("S&P 500", "Bonds Baa", "T-Notes", "Inflation")


class SequenceError(ValueError):
    """The sequences data file does not hold what a downturn event needs."""


def load_sequences(path=None) -> dict:
    """{name: {"description": str, "source": str, "window": [[S&P 500, Bonds Baa, T-Notes, Inflation], ...]}}
    for every named sequence (returns in percent per year). Read at every call (no cache): the
    file is tiny, and a live server must see an edit (review Z7)."""
    import toml

    path = Path(path) if path is not None else SEQUENCES_FILE
    try:
        with open(path, encoding="utf-8") as f:
            doc = toml.load(f)
    except OSError as e:
        raise SequenceError(f"the downturn sequences file {path} cannot be read: {e}") from e
    sequences = doc.get("sequences")
    if not isinstance(sequences, dict) or not sequences:
        raise SequenceError(f"the downturn sequences file {path} holds no [sequences.<name>] tables")
    out = {}
    for name, entry in sequences.items():
        window = entry.get("window")
        if not isinstance(window, list) or not window:
            raise SequenceError(f"sequence {name!r} has no 'window' rows")
        rows = []
        for i, row in enumerate(window):
            if not isinstance(row, list) or len(row) != len(WINDOW_COLUMNS):
                raise SequenceError(
                    f"sequence {name!r}, window row {i + 1}: expected {len(WINDOW_COLUMNS)} values "
                    f"({', '.join(WINDOW_COLUMNS)})"
                )
            try:
                rows.append([float(v) for v in row])
            except (TypeError, ValueError) as e:
                raise SequenceError(f"sequence {name!r}, window row {i + 1}: not numbers: {row!r}") from e
        out[name] = {
            "description": str(entry.get("description", "")),
            "source": str(entry.get("source", "")),
            "window": rows,
        }
    return out


def sequences() -> dict:
    """The named sequences (see `load_sequences`)."""
    return load_sequences()
