"""The run library: storage and scenario handling for named runs.

Design: `fork-notes/run-library-design.md` (sections 4-7, build step 1). Schema version 1
holds hand rows only: Owl's case dictionary and the HFP workbook tables as JSON.
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
    df_to_table,
    export_case,
    import_case,
    scenario_from_case,
    scenario_from_ui,
    table_to_df,
)
from .store import Library, LibraryError, LibraryLocked, RunInfo, SaveResult  # noqa: F401
