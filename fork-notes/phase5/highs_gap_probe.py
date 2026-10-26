"""
Why does HiGHS report "Optimal" with a MIP gap above mip_rel_gap? (2026-10-26)

The branch-and-bound dry run (`work_sweep_chris+pat_bb_2026-10-26.json`) accepted 12 of 84 plans
whose HiGHS runs all ended "Optimal" at --gap 1e-5 but whose reported gap was 1.0-2.0e-5. This
re-solves one of them (pat-stops-2027, Chris 68y3m / Pat 62y1m: reported 1.43e-5) and prints, for
every HiGHS run of the solve: the options it was given (mip_rel_gap, mip_abs_gap, time_limit,
presolve), its status, primal and dual bounds as HiGHS reports them, the reported mip_gap and the
gap recomputed from the bounds. HiGHS's own log goes to the file named by --highs-log.

Run from the repository root (plans start today):

    .venv/bin/python fork-notes/phase5/highs_gap_probe.py [--variant pat-stops-2027] [--ages 68.25 62.0833]
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import highspy  # noqa: E402

import work_sweep as ws  # noqa: E402

HERE = os.path.dirname(__file__)
CASE = os.path.join(HERE, "..", "..", "examples", "Case_chris+pat.toml")
SPEC = os.path.join(HERE, "work_sweep_chris+pat.json")
RUNS = []


class RecordedHighs(highspy.Highs):
    """Highs that logs to a file and records every run's options and outcome."""

    log_file = None

    def setOptionValue(self, name, value):
        if name == "output_flag":
            value = True
        return super().setOptionValue(name, value)

    def run(self):
        super().setOptionValue("log_file", RecordedHighs.log_file)
        super().setOptionValue("log_to_console", False)
        keys = ("mip_rel_gap", "mip_abs_gap", "time_limit", "presolve", "mip_feasibility_tolerance")
        opts = {k: self.getOptionValue(k)[1] for k in keys}
        st = super().run()
        info = self.getInfo()
        primal, dual = info.objective_function_value, info.mip_dual_bound
        RUNS.append({
            "status": self.modelStatusToString(self.getModelStatus()),
            "is_mip": info.mip_node_count >= 0 and self.getLp().integrality_ != [],
            "options": opts, "primal": primal, "dual": dual, "mip_gap": info.mip_gap,
            "gap_recomputed": abs(primal - dual) / abs(primal) if primal else None,
            "nodes": info.mip_node_count,
        })
        return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="pat-stops-2027")
    ap.add_argument("--ages", type=float, nargs=2, default=[68.25, 62 + 1 / 12])
    ap.add_argument("--gap", type=float, default=1e-5)
    ap.add_argument("--out-dir", default=os.path.join(HERE, "..", "..", "otherFiles", "sweep-probe"))
    ap.add_argument("--highs-log", default="highs_gap_probe.log")
    args = ap.parse_args()

    with open(SPEC, encoding="utf-8") as f:
        spec = json.load(f)
    by = {v[0]: v for v in ws.build_variants(CASE, spec, args.out_dir)}
    _, d, dirname, _ = by[args.variant]
    RecordedHighs.log_file = args.highs_log
    highspy.Highs = RecordedHighs  # Plan._run_highs imports highspy and builds highspy.Highs()

    p, _ = ws.make_plan(d, dirname, args.ages)
    opts = ws.base_options(p, withSSAges="fixed", breakpointMethod="branch-and-bound", gap=args.gap)
    p.solve(p.objective, opts)
    print(f"{args.variant} at {'/'.join(ws.ym(a) for a in args.ages)}: {p.caseStatus}, "
          f"value {p._objectiveValue(p.objective):,.2f}, solverGap {p.solverGap:.3e}")
    print(f"{'run':>4} {'status':<12}{'mip':>4}{'rel_gap':>9}{'abs_gap':>9}{'time':>6}{'presolve':>9}"
          f"{'primal':>16}{'dual':>16}{'mip_gap':>11}{'recomp':>11}{'nodes':>8}")
    for k, r in enumerate(RUNS):
        o = r["options"]
        rec = f"{r['gap_recomputed']:.3e}" if r["gap_recomputed"] is not None else "-"
        print(f"{k:>4} {r['status']:<12}{'y' if r['is_mip'] else 'n':>4}{o['mip_rel_gap']:>9.1e}"
              f"{o['mip_abs_gap']:>9.1e}{o['time_limit']:>6.0f}{o['presolve']:>9}{r['primal']:>16.6f}"
              f"{r['dual']:>16.6f}{r['mip_gap']:>11.3e}{rec:>11}{r['nodes']:>8}")


if __name__ == "__main__":
    main()
