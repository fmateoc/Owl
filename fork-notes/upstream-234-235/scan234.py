"""How much does _netSurplusRoundTrip net in each example (fork code), and in which years:
state tax, a tracked cost basis, the gain fraction there."""
import glob, io, os, sys
import numpy as np
import owlplanner as owl
from owlplanner.plan import Plan

EX = "/home/user/Owl/examples"
real = Plan._netSurplusRoundTrip
log = []


def spy(self):
    w0 = self.w_ijn[:, 0, :].copy()
    real(self)
    log.append(w0 - self.w_ijn[:, 0, :])


Plan._netSurplusRoundTrip = spy
files = sorted(glob.glob(f"{EX}/Case_*.toml"))
if len(sys.argv) > 1:
    files = [f for f in files if any(k in f for k in sys.argv[1:])]
for f in files:
    log.clear()
    p = owl.readConfig(f, verbose=False, logstreams=[io.StringIO()])
    hfp = f.replace("Case_", "HFP_").replace("-spending", "").replace("-bequest", "").replace(".toml", ".xlsx")
    if os.path.exists(hfp):
        p.readHFP(hfp)
    p.resolve()
    name = os.path.basename(f)[5:-5]
    if not log:
        print(f"{name:22s} status {p.caseStatus}: netting not reached", flush=True)
        continue
    d = log[-1]
    yrs = [(int(p.year_n[n]), round(float(d[:, n].sum())), round(float(p.st_T_n[n])),
            "basis" if p.gain_fraction_in is not None and not np.all(np.isnan(p.gain_fraction_in[:, n])) else "no basis")
           for n in range(p.N_n) if d[:, n].sum() > 0.5]
    states = ",".join(sorted(set(p._states_n()))) if hasattr(p, "_states_n") else "?"
    print(f"{name:22s} {states:6s} eta {p.eta:.1f} netted ${d.sum():>10,.0f} in {len(yrs):2d} years; "
          f"(year, netted, st_T_n, basis): {yrs[:6]}{' ...' if len(yrs) > 6 else ''}", flush=True)
