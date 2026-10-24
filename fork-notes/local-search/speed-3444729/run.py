"""Local-search preset on every example; one line per case: name, status, method used, seconds, basis, bequest."""
import glob, io, os, sys, time
import owlplanner as owl

root = sys.argv[1]
out = open(sys.argv[2], "w")
print("owlplanner", owl.__file__, file=out, flush=True)
for path in sorted(glob.glob(os.path.join(root, "examples", "Case_*.toml"))):
    name = os.path.basename(path)[5:-5]
    p = owl.readConfig(path, verbose=False, logstreams=[io.StringIO()])
    t0 = time.perf_counter()
    p.solve(p.objective, options={**p.solverOptions, "breakpointMethod": "local-search"})
    dt = time.perf_counter() - t0
    print(f"{name}\t{p.caseStatus}\t{getattr(p, 'breakpointMethodUsed', '?')}\t{dt:.1f}\t{float(p.basis):.2f}\t{float(p.bequest):.2f}",
          file=out, flush=True)
