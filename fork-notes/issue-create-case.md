# Issue draft: Create Case loses the first click on *Create case*, and says nothing after an upload

Status: **draft, not filed** (2026-11-07, UX review Q18 and Q11, `fork-notes/ux-review.md`). For
the user to file on `mdlacasse/Owl`. Checked on upstream `dev` `73dc8815` (2026-11-07). Patch:
`fork-notes/issue-create-case.patch` (applies to stock `dev` with `git apply`; verified there:
`tests/ui` 162 passed; its new test file fails on stock `dev`, 2 of 3). Repro script:
`fork-notes/issue-create-case-repro.js` (Node + Playwright against a running Owl). The output
below is from real runs of that script in this container: stock `dev` on one server, `dev`
with the patch on another.

---

**Title:** Create Case: the first click on *Create case* does nothing, and a workbook upload is not confirmed

Two small things on the same page.

**1. The first click on *Create case* is lost.** The button is disabled while
`cantcreate = kz.isIncomplete() or diz1` (`ui/Create_Case.py` 267 and 320). A text field commits its value when it loses focus, so after
typing the first name the button is still disabled; the mouse-down on it is what takes the
focus away, and that click lands on a disabled button. The page then reruns with the name in,
the button turns on, and a second click creates the case. Someone who clicks once sees the
*"Any parameter on this page can now be changed ..."* note and no case.

**2. Nothing confirms a workbook upload.** After a case is created, *Upload Financial Profile
(Optional)* offers the HFP uploader; once `owlbridge.readHFP` succeeds, the whole block is
hidden (`stHFP` is set) and nothing says that the file was read or what it held.

**Repro (stock `dev` `73dc8815`):** start Owl, then run the script with the example workbook.
It opens Create Case, *Create a New Case*, types a case name (Enter) and a first name, clicks
*Create case* with the mouse right after typing, then uploads the workbook.

```text
$ OWL_URL=http://localhost:8501 node issue-create-case-repro.js examples/HFP_jack+jill.xlsx
Create case disabled at the click: true
after one click: no case created | alerts: ["Any parameter on this page can now be changed, including the case name. Once changes are complete, click the Create case button."]
after a second click: ["Created new case 'probe'. You can now move to the next page."]
upload heading still shown: 0
captions mentioning the workbook: []
```

**With the patch:**

```text
Create case disabled at the click: false
after one click: Created new case 'probe'. You can now move to the next page. | alerts: []
upload heading still shown: 0
captions mentioning the workbook: ["✅ HFP_jack+jill.xlsx loaded: wages and contributions for Jack; 1 debt, 1 fixed asset."]
```

(The script creates a single person, so the workbook's second sheet is not read.)

**Patch (attached), `ui/Create_Case.py` only:**

- *Create case* is disabled only once the case exists (`diz1`). Its callback `_createCase`
  checks the names `isIncomplete` checks; when one is missing it does not create the case,
  and the page says which: *"Enter your first name first."* (or the case name, or the
  spouse's first name).
- When the case has a plan and a workbook was read, the place of the upload block shows one
  line built from what `readHFP` stored: the file's name, whose wages and contributions, and
  the number of Debts and Fixed Assets rows.
- New `tests/ui/test_create_case_button.py` (AppTest): the button is enabled before the
  names and a blank click names what is missing; with the names in, one click creates; the
  confirmation line for jack+jill's workbook. AppTest cannot move the focus, so the lost
  click itself is shown by the Playwright script above, not by the test. Two of the three
  fail on stock `dev`; all three pass with the patch.
- A note on the test file: the session's date freeze (`tests/conftest.py`, `freeze_year`)
  also rebinds `date` inside Streamlit's date widget, which then refuses the plain `date`
  values AppTest hands back on a rerun of a page with a date input ("Invalid `value` type
  ... Provided type: date"). The test puts the real class back in that one module.

Found by a review of the interface in our fork (`fmateoc/Owl`); the fork carries the same
change, plus a fork-only Budget-sheet count.
