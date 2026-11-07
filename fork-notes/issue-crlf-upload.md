# Issue draft: a case file with Windows line endings uploads as its name alone

Status: **draft, not filed** (2026-11-07; `ux-qw-handoff-2.md` N1, review AN9). For the user
to file on `mdlacasse/Owl`. Checked on upstream `dev` `73dc8815` (2026-11-07). Patch:
`fork-notes/issue-crlf-upload.patch` (`src/owlplanner/config/toml_io.py` and a new
`tests/config/test_toml_crlf.py`; applies to stock `dev` with `git apply`; verified there:
the new test fails on stock `dev` (both cases) and passes with the patch; `tests/config` and
`tests/ui` 409 passed with it). Repro script: `fork-notes/issue-crlf-upload-repro.py` (run from
a stock `dev` checkout with `PYTHONPATH=src`). The output below is from real runs in this
container.

The fork carries the same fix since the QW-1-QW-8 build (`claude/ui-remediation-qw`,
`toml_io._lf`).

---

**Title:** Create Case: a case file with CRLF line endings fails with "Failed to parse case file: 'basic_info'"

`load_toml` reads a path with `toml.load` and an upload with `toml.loads`
(`src/owlplanner/config/toml_io.py`, the `BytesIO` and `StringIO` branches). On text with
CRLF line endings, `toml` 0.10.2's string parser drops a triple-quoted string and **every key
after it**, with no error; `toml.load` on a path is not affected (the file is read through
universal newlines). Create Case uploads through `StringIO(file.read().decode("utf-8"))`
(`ui/Create_Case.py`), so such a case parses as its `case_name` alone and the page then says
*"Failed to parse case file: 'basic_info'"*.

How a user gets such a file: `.gitattributes` covers `*.sh` only, so a Git-for-Windows checkout
(`core.autocrlf` on by default) writes the examples with CRLF. 14 of the 19
`examples/Case_*.toml` hold a `"""` string (the `description`), so 14 of them fail to upload
from such a checkout. A CRLF file without one loads whole (`Case_avery+quinn.toml`: 11 keys).

**Repro (stock `dev` `73dc8815`):** `Case_jack+jill.toml` with its line endings changed to
CRLF in memory, through `load_toml` and through Create Case's upload path
(`owlbridge.createCaseFromFile`, with `st.error` captured):

```text
$ PYTHONPATH=src python issue-crlf-upload-repro.py examples/Case_jack+jill.toml
from a path (LF file):     ['asset_allocation', 'basic_info', 'case_name', 'description', 'fixed_income', 'household_financial_profile', 'optimization_parameters', 'rates_selection', 'results', 'savings_assets', 'solver_options']
from StringIO, LF text:    ['asset_allocation', 'basic_info', 'case_name', 'description', 'fixed_income', 'household_financial_profile', 'optimization_parameters', 'rates_selection', 'results', 'savings_assets', 'solver_options']
from StringIO, CRLF text:  ['case_name']
from BytesIO, CRLF bytes:  ['case_name']
Create Case, CRLF upload: name = '' | st.error: ["Failed to parse case file: 'basic_info'"]
```

**With the patch** (a `_lf` helper normalizing line endings before `toml.loads` in both
branches):

```text
from StringIO, CRLF text:  ['asset_allocation', 'basic_info', 'case_name', 'description', 'fixed_income', 'household_financial_profile', 'optimization_parameters', 'rates_selection', 'results', 'savings_assets', 'solver_options']
from BytesIO, CRLF bytes:  ['asset_allocation', 'basic_info', 'case_name', 'description', 'fixed_income', 'household_financial_profile', 'optimization_parameters', 'rates_selection', 'results', 'savings_assets', 'solver_options']
Create Case, CRLF upload: name = 'jack+jill' | st.error: []
```

A second, complementary option: `*.toml text eol=lf` in `.gitattributes`, so checkouts keep LF.
It protects the examples, not a case file a user saved with Windows line endings themselves;
the patch covers both.

(Not checked: whether other `toml.loads` callers in the code base read uploaded text.)
