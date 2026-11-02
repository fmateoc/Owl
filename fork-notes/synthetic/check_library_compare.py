"""Step-3 acceptance check: the synthetic baseline against a variant (run-library-design.md,
section 11, "the synthetic baseline against a variant").

    uv run python fork-notes/synthetic/check_library_compare.py

Import the synthetic baseline (fork-notes/synthetic/cases/Case_ari+noa.toml + its workbook)
and a variant of it ($400k less in the taxable account) into a fresh library, solve each the
way the library's worker does, and read the results back exactly as the run page and the
comparison page do (`owlplanner.library.view` / `compare`, from the durable files alone):

1. the baseline solves and its numbers derive (score, home at the end, savings left, taxes,
   claiming ages, the quality line);
2. the variant solves and moves the score by more than the 1% loop-noise band (R2);
3. the numbers survive without `plan.pkl` (D7: charts and figures from summary.json/plan.json);
4. the comparison judges the pair: the score difference resolved, the two numbers read as
   leads or trade-off (R3), no day/preset/commit flags (S13), the inputs' difference in
   words, and "what moved" rows;
5. the same inputs solved twice compare as "no difference";
6. the exact model (decision_exact) on both runs agrees with the pair's ordering (R2's
   agreement check).

Prints one line per check and a summary; exits 1 if any check fails.
"""

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from owlplanner.library import (  # noqa: E402
    Library,
    compare as C,
    import_case,
    view,
)
from owlplanner.library import results as R  # noqa: E402
from owlplanner.library.scenario import diff_summaries  # noqa: E402
from owlplanner.library.worker import run_job  # noqa: E402

CASES = Path(__file__).parent / "cases"
CASE = CASES / "Case_ari+noa.toml"
WORKBOOK = CASES / "HFP_ari+noa.xlsx"

# The plan's logger writes DEBUG to stdout/stderr; keep the script's own output readable.
_quiet = contextlib.redirect_stdout(io.StringIO())
_real_out = sys.stdout


def _solve(library, run, name, preset):
    """One solve through the worker's own route (like the detached worker, in-process)."""
    job = R.JobRecord.create(run.path / "results" / name, run_id=run.id, run_name=run.name,
                             preset=preset, options={},
                             plan_year=json.loads(
                                 (run.path / "inputs" / "scenario.json").read_text(encoding="utf-8")
                             )["plan_year"])
    run_job(job.results_dir, job.token)
    return view.load_result(job.results_dir)


def main() -> int:
    if not CASE.exists() or not WORKBOOK.exists():
        print(f"missing {CASE.name} / {WORKBOOK.name} (run make_cases.py first)")
        return 2

    failures = 0
    checks = 0
    with tempfile.TemporaryDirectory() as tmp, _quiet:
        library = Library.open(Path(tmp) / "library")
        base = library.save_run(name="ari+noa baseline", scenario=import_case(CASE, hfp_path=WORKBOOK)).run

        variant_scenario = import_case(CASE, hfp_path=WORKBOOK)
        balances = variant_scenario["case"]["savings_assets"]["taxable_savings_balances"]
        variant_scenario["case"]["savings_assets"]["taxable_savings_balances"] = [
            float(v) - 200.0 for v in balances
        ]
        variant = library.save_run(name="ari+noa, 400k less saved", scenario=variant_scenario,
                                   parent=base.id).run

        # 1. the baseline solves and its numbers derive -----------------------------
        checks += 1
        a = _solve(library, base, "2026-11-02T10-00-00_quick", "quick")
        ok = a.solved and view.score(a) is not None and view.score(a) > 0
        failures += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'} baseline: {view.score_label(a)} = "
              f"{view.score(a) or 0.0:,.0f}, home {view.home_at_end(a) or 0.0:,.0f}, "
              f"savings {view.savings_left(a) or 0.0:,.0f}, "
              f"taxes {view.total_taxes_today(a) or 0.0:,.0f}, "
              f"{view.claiming_ages_text(a)}, quality: {view.quality_line(a)}",
              file=_real_out)

        # 2. the variant solves and moves the score beyond the noise band -----------
        checks += 1
        b = _solve(library, variant, "2026-11-02T10-30-00_quick", "quick")
        d_score = (view.score(b) or 0.0) - (view.score(a) or 0.0)
        beyond = abs(d_score) > view.NOISE_FRACTION * abs(view.score(a) or 0.0)
        ok = b.solved and beyond
        failures += 0 if ok else 1
        pct = 100 * d_score / (view.score(a) or 1.0)
        print(f"{'ok  ' if ok else 'FAIL'} variant: score "
              f"{view.score(b) if view.score(b) is not None else float('nan'):,.0f} "
              f"({d_score:+,.0f} = {pct:+.2f}%: "
              f"{'beyond the 1% band' if beyond else 'inside the 1% band, not a difference'})",
              file=_real_out)

        # 3. the numbers survive without plan.pkl (D7) ------------------------------
        checks += 1
        (a.results_dir / R.PLAN_PKL).unlink(missing_ok=True)
        (b.results_dir / R.PLAN_PKL).unlink(missing_ok=True)
        a2, b2 = view.load_result(a.results_dir), view.load_result(b.results_dir)
        ok = (R.load_plan(a.results_dir) is None and view.score(a2) == view.score(a)
              and view.home_at_end(b2) == view.home_at_end(b))
        failures += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'} durable files: the numbers survive without plan.pkl",
              file=_real_out)

        # 4. the comparison judges the pair ----------------------------------------
        checks += 1
        changes = diff_summaries(library.scenario(base), library.scenario(variant))
        out = C.compare(a2, b2)
        by_label = {row.label: row for row in out.rows}
        ok = (by_label["score"].resolved
              and out.lead["verdict"] in ("the first result leads", "the second result leads",
                                          "trade-off")
              and out.flags == ()
              and any("taxable_savings_balances" in change for change in changes)
              and out.what_moved)
        failures += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'} comparison: score {by_label['score'].verdict}, "
              f"lead: {out.lead['verdict']}, flags: {len(out.flags)}, "
              f"{len(changes)} input change(s), {len(out.what_moved)} year(s) moved",
              file=_real_out)

        # 5. the same inputs solved twice are "no difference" -----------------------
        checks += 1
        again = _solve(library, base, "2026-11-02T11-00-00_quick", "quick")
        out = C.compare(a2, again)
        ok = all(row.verdict == "no difference" for row in out.rows)
        failures += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'} re-solve: "
              + ", ".join(f"{row.label} {row.delta:+,.0f}" for row in out.rows),
              file=_real_out)

        # 6. the exact model agrees with the ordering (R2) --------------------------
        checks += 1
        a_ex = _solve(library, base, "2026-11-02T11-30-00_decision_exact", "decision_exact")
        b_ex = _solve(library, variant, "2026-11-02T12-00-00_decision_exact", "decision_exact")
        out = C.compare(a2, b2, a_exact=a_ex, b_exact=b_ex)
        agree = out.agreement
        ok = (agree is not None and agree["verdict"].startswith("resolved")
              and (agree["delta_pair"] > 0) == (agree["delta_exact"] > 0))
        failures += 0 if ok else 1
        d_pair = f"{agree['delta_pair']:+,.0f}" if agree else "-"
        d_ex = f"{agree['delta_exact']:+,.0f}" if agree else "-"
        print(f"{'ok  ' if ok else 'FAIL'} agreement: d_pair {d_pair}, d_exact {d_ex}: "
              f"{agree['verdict'] if agree else 'no agreement check'}",
              file=_real_out)

    print(f"{checks - failures}/{checks} step-3 checks pass", file=_real_out)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
