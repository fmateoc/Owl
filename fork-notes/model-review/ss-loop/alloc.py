"""Break the TD/Roth growth tie: Roth at a different stock share than the other accounts."""
import io, sys
argv = sys.argv[1:]
sys.argv = ["x", "/dev/null"]
sys.path.insert(0, "fork-notes/model-review/phase3-review")
import itemized_convergence as ic
import pandas as pd
STATES = [(x, "Yonkers" if x == "NY" else "") for x in argv[0].split(",")]
YOB = int(argv[1]) if len(argv) > 1 else 2032
for state, loc in STATES:
    for pt in (20000.0, 25000.0, 30000.0):
        for roth in (60, 59, 61, 70):
            for ssopt in ("loop", "optimize"):
                log = io.StringIO()
                p = ic.couple(state, loc, 600000.0, YOB, log)
                p.houseLists["Budget"] = ic.cond(pd.DataFrame([ic.line("core", "core", 80000.0),
                                                               ic.line("pt", "property tax", pt)]), "Budget")
                a = [[60, 40, 0, 0], [60, 40, 0, 0]]
                r_ = [[roth, 100 - roth, 0, 0], [roth, 100 - roth, 0, 0]]
                p.setAllocationRatios("account", taxable=[a] * 2, taxDeferred=[a] * 2, taxFree=[r_] * 2)
                p.solve("maxBequest", options={"noRothConversions": "None", "withItemized": "none",
                                               "withSSTaxability": ssopt})
                r = ic.record(p, log, 0.0)
                print(f"{state} {YOB} pt{pt/1000:.0f}k roth{roth} SS={ssopt:8s} it={r['iters']:2d} {r['conv']:30s} obj={r.get('obj')} {r.get('resid_worst')}", flush=True)
