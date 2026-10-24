"""run2.py plus an optional flat spending profile: argv[3] JSON may hold "__flat": survivor percent."""
import io, json, os, sys, time
import owlplanner as owl

root, outf, extra = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
flat = extra.pop("__flat", None)
out = open(outf, "w")
print("owlplanner", owl.__file__, extra, "flat" if flat else "", file=out, flush=True)
for name in sys.argv[4:]:
    p = owl.readConfig(os.path.join(root, "examples", f"Case_{name}.toml"), verbose=False, logstreams=[io.StringIO()])
    if flat is not None:
        p.setSpendingProfile("flat", percent=flat)
    t0 = time.perf_counter()
    p.solve(p.objective, options={**p.solverOptions, "breakpointMethod": "local-search", **extra})
    dt = time.perf_counter() - t0
    print(f"{name}\t{p.caseStatus}\t{getattr(p, 'breakpointMethodUsed', '?')}\t{dt:.1f}\t{float(p.basis):.2f}\t{float(p.bequest):.2f}",
          file=out, flush=True)
