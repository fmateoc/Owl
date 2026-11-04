"""
Table rate model: a year-by-year rates table the case file names.

A case whose `[rates_selection]` names `method = "table"` and a `rates_file` reads its
returns from that CSV instead of generating them, so one frozen table reproduces a run
everywhere -- `owlcli run` and the interface read the same file (run-library design,
D11 / R13). The file sits beside the case file (`rates.csv` next to `Case.toml`) and has
the shape of Owl's own rate history (`src/owlplanner/data/rates.csv`): a `year` column
and the four rate columns, values in percent. Extra columns are ignored, so that history
file itself can be named. Rows are matched to the plan's calendar years by the `year`
column; the plan's first year is passed in as `start_year` (`Plan.setRates`).

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

###########################################################################
import csv
import os

import numpy as np

from owlplanner.rate_models.base import BaseRateModel
from owlplanner.rate_models.constants import REQUIRED_RATE_COLUMNS

# The CSV's header: the year key plus the four rate columns (the DataFrame model's order).
RATE_TABLE_COLUMNS = ("year",) + tuple(REQUIRED_RATE_COLUMNS)


def read_rates_csv(path):
    """The table in `path` as rows of [year (int), S&P 500, Bonds Baa, T-Notes, Inflation]
    (numbers in percent). The header must hold the five columns (extra columns are ignored,
    so Owl's own rate history `data/rates.csv` can be named); rows may come in any order.
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next((row for row in reader if any(cell.strip() for cell in row)), None)
        if header is None:
            raise ValueError(f"Rates table '{path}' is empty.")
        header = [cell.strip() for cell in header]
        missing = [c for c in RATE_TABLE_COLUMNS if c not in header]
        if missing:
            raise ValueError(
                f"Rates table '{path}' is missing the column(s) {missing}: "
                f"its header must hold {list(RATE_TABLE_COLUMNS)} (extra columns are ignored)."
            )
        take = [header.index(c) for c in RATE_TABLE_COLUMNS]
        rows = []
        for line in reader:
            if not any(cell.strip() for cell in line):
                continue
            try:
                cells = [line[i].strip() for i in take]
                rows.append([int(cells[0])] + [float(v) for v in cells[1:]])
            except (IndexError, ValueError) as e:
                raise ValueError(f"Rates table '{path}': bad row {line!r}") from e
    return rows


class TableRateModel(BaseRateModel):
    """
    Rate model that reads a year-by-year rates table from a CSV file named in the case file.

    The table is deterministic: the same file gives the same plan on every machine and in
    every process (`owlcli run` reproduces a run of the interface). `rows` may carry the
    table in memory instead (the library builder and the interface hold it); the file is
    read only when `rows` is absent.
    """

    model_name = "table"
    description = (
        "Year-by-year rates read from a CSV file named in the case file (a `year` column and "
        "the columns 'S&P 500', 'Bonds Baa', 'T-Notes', 'Inflation', values in percent). "
        "The file sits beside the case file; its years are matched to the plan's years."
    )

    deterministic = True
    constant = False

    required_parameters = {
        "rates_file": {
            "type": "str",
            "description": "The rates CSV, resolved beside the case file (as the HFP workbook is).",
            "example": '"rates.csv"',
        },
    }

    optional_parameters = {
        "base_dir": {
            "type": "str",
            "default": "",
            "description": "Directory the file name is resolved against (set when the case is loaded, not stored).",
        },
        "start_year": {
            "type": "int",
            "default": None,
            "description": "The plan's first calendar year (set by Plan.setRates, not stored).",
        },
        "in_percent": {
            "type": "bool",
            "default": True,
            "description": "If True (default), table values are in percent (7.0 = 7%) and are divided by 100.",
        },
        "rows": {
            "type": "list[list[float]]",
            "default": None,
            "description": "The table in memory ([year, S&P 500, Bonds Baa, T-Notes, Inflation] per row).",
        },
    }

    #######################################################################
    # TOML Serialization
    #######################################################################

    @classmethod
    def from_config(cls, rates_section: dict) -> dict:
        """Only what a case file may name: the file name (and the units)."""
        section = dict(rates_section)
        out = {"rates_file": section["rates_file"]}
        if section.get("in_percent") is not None:
            out["in_percent"] = bool(section["in_percent"])
        return out

    @classmethod
    def to_config(cls, **params) -> dict:
        """Only the file name (and the units) go back to the case file: `base_dir`, `start_year`
        and `rows` are machinery of the process that loaded the case."""
        out = {"rates_file": params["rates_file"]}
        if params.get("in_percent") is not None and not bool(params["in_percent"]):
            out["in_percent"] = bool(params["in_percent"])
        return out

    #######################################################################
    # Generate
    #######################################################################

    def generate(self, N):
        rows = self.get_param("rows")
        if rows is None:
            rows = self._read_rows()
        self.rows = rows  # kept in memory: a plan that cannot re-read the file reuses them
        start = self.get_param("start_year")
        if start is None:
            raise ValueError(
                "Rate model 'table' needs the plan's first calendar year ('start_year'): "
                "call it through Plan.setRates, which passes it."
            )
        start = int(start)

        by_year: dict[int, list[float]] = {}
        for i, row in enumerate(rows):
            try:
                year = int(row[0])
                values = [float(v) for v in row[1:5]]
            except (TypeError, ValueError, IndexError) as e:
                wanted = ", ".join(REQUIRED_RATE_COLUMNS)
                raise ValueError(f"rates table row {i + 1} is not [year, {wanted}]: {row!r}") from e
            if year in by_year:
                raise ValueError(f"rates table has two rows for {year}")
            by_year[year] = values

        missing = [y for y in range(start, start + N) if y not in by_year]
        if missing:
            shown = ", ".join(str(y) for y in missing[:5]) + ("..." if len(missing) > 5 else "")
            raise ValueError(
                f"rates table {self.get_param('rates_file')!r} has no row for {shown} "
                f"(the plan covers {start}-{start + N - 1})"
            )

        data = np.array([by_year[year] for year in range(start, start + N)], dtype=float)
        if self.get_param("in_percent"):
            data = data / 100.0
        return data

    def _read_rows(self):
        """The table from `rates_file`, resolved as the HFP workbook and budget_file are:
        the name as given (a path, or relative to the working directory), then beside the
        case file (`base_dir`)."""
        name = str(self.get_param("rates_file") or "").strip()
        candidates = [name] if os.path.isabs(name) else [name, os.path.join(self.get_param("base_dir") or "", name)]
        path = next((c for c in candidates if c and os.path.exists(c)), None)
        if path is None:
            where = f" or beside the case file ({self.get_param('base_dir')})" if self.get_param("base_dir") else ""
            raise FileNotFoundError(f"Rates table {name!r} not found{where}.")
        return read_rates_csv(path)
