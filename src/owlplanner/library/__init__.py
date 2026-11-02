"""The run library: storage and scenario handling for named runs.

Design: `fork-notes/run-library-design.md` (sections 4-8). Schema version 1 holds hand rows
only: Owl's case dictionary and the HFP workbook tables as JSON, plus the run's plan year (the
year its balances and year rows were entered for, R1). Build step 2 adds the jobs: `JobManager`
queues solves in detached workers (`worker.py`), each in its own results folder (`results.py`);
a run is solved only in its plan year (`check_plan_year`).
"""

from .scenario import (  # noqa: F401
    BUILDER_VERSION,
    SCHEMA_VERSION,
    ScenarioError,
    canonical_json,
    diff_summaries,
    migrate,
    scenario_hash,
    validate,
)
from .casefiles import (  # noqa: F401
    canonical_case,
    canonicalize,
    check_plan_year,
    df_to_table,
    export_case,
    import_case,
    scenario_from_case,
    scenario_from_ui,
    table_to_df,
)
from .jobs import JobManager, JobsError  # noqa: F401
from .presets import PRESETS, preset_options, resolve_options  # noqa: F401
from .results import (  # noqa: F401
    JobRecord,
    ResultsError,
    build_record,
    environment,
    load_plan,
    save_plan,
)
from .store import Library, LibraryError, LibraryLocked, RunInfo, SaveResult  # noqa: F401
