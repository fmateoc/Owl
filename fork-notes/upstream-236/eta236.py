"""#236 on the household's structure: fixed eta (0, 0.5, 1) vs the LP's own split.

Stand-in household: fork-notes/phase0/Case_us.template.toml with illustrative balances
(placeholders, not the household's). Horizons: as in the template (both born 1964, both 92:
equal, so no survivor years) and a sensitivity with SpouseA at 85. SS ages fixed at 67.
Deciders: local search (the template's families) and the exact LP (Medicare none, SS 0.85).
"Free" replaces the both-alive rows d_i = eta_i s_n by d_0 + d_1 = s_n (the proposal).
"""

import io
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import owlplanner as owl  # noqa: F401
from owlplanner import plan as plan_mod
from owlplanner.config import load_toml
from owlplanner.config.plan_bridge import config_to_plan
from owlplanner.export import _compute_estate

TEMPLATE = "/home/user/Owl/fork-notes/phase0/Case_us.template.toml"
HERE = sys.argv[1]

NET_SPENDING = 120.0  # $k, under maxSpending's ~156k: leaves money to deposit

STAND_IN = {
    "taxable_savings_balances": [600.0, 300.0],
    "taxable_cost_basis": [450.0, 120.0],  # gain shares 25% and 60%: the split can matter
    "tax_deferred_savings_balances": [1200.0, 500.0],
    "tax_free_savings_balances": [100.0, 50.0],
    "hsa_savings_balances": [0.0, 0.0],
}


def free_linking(self, options):
    """The proposal: one row per both-alive year, survivor rows as upstream."""
    for n in range(self.n_d):
        self.A.addNewRow({self.vm["d"].idx(0, n): 1, self.vm["d"].idx(1, n): 1, self.vm["s"].idx(n): -1},
                         0, 0, tag=("surplus_deposit", 0, n))
    for i in range(self.N_i):
        fac2 = 1.0 if i == self.i_s else 0.0
        for n in range(self.n_d, self.N_n):
            self.A.addNewRow({self.vm["d"].idx(i, n): 1, self.vm["s"].idx(n): -fac2},
                             0, 0, tag=("surplus_deposit", i, n))
    if options.get("noLateSurplus", False):
        self.B.setRange(self.vm["s"].idx(self.N_n - 2), 0, 0)
        self.B.setRange(self.vm["s"].idx(self.N_n - 1), 0, 0)


ORIGINAL = plan_mod.Plan._add_surplus_deposit_linking
_NET = plan_mod.Plan._netSurplusRoundTrip


def _net_recorded(self):
    """Keep the LP's own deposits and taxable withdrawals before the worksheet nets them (#234)."""
    self._raw_d = self.d_in.copy()
    self._raw_w0 = self.w_ijn[:, 0, :].copy()
    _NET(self)


plan_mod.Plan._netSurplusRoundTrip = _net_recorded
FREE = plan_mod._fixedAcrossIterations(free_linking)


def build(horizon_a, objective):
    d = load_toml(TEMPLATE)[0]
    d["savings_assets"].update(STAND_IN)
    d["basic_info"]["life_expectancy"] = [horizon_a, 92]
    d["fixed_income"]["social_security_pia_amounts"] = [3200, 2000]
    d["fixed_income"]["social_security_ages"] = [67.0, 67.0]
    d["aca_settings"]["slcsp_annual"] = 24.0
    d["household_financial_profile"]["HFP_file_name"] = "HFP_us_wages.xlsx"  # 2026 wages, then retired
    if objective == "maxBequest":
        d["optimization_parameters"]["objective"] = "maxBequest"
        d["solver_options"]["netSpending"] = NET_SPENDING
    d["solver_options"]["withSSAges"] = "fixed"
    return d


def run(job):
    horizon_a, split, decider, objective = job
    d = build(horizon_a, objective)
    # Set on every job: pool workers are reused, so a patch left by a "free" job would leak.
    if split != "free":
        d["savings_assets"]["spousal_surplus_deposit_fraction"] = float(split)
        plan_mod.Plan._add_surplus_deposit_linking = ORIGINAL
    else:
        plan_mod.Plan._add_surplus_deposit_linking = FREE
    buf = io.StringIO()
    p = config_to_plan(d, HERE, verbose=True, logstreams=[buf])
    opts = dict(p.solverOptions or {})
    if decider == "ls":
        opts.update(breakpointMethod="local-search")
    else:
        opts.update(withMedicare="none", withSSTaxability=0.85)
    t0 = time.time()
    p.solve(p.objective, opts)
    out = {"horizon_a": horizon_a, "split": split, "decider": decider, "objective": objective,
           "status": p.caseStatus,
           "seconds": round(time.time() - t0, 1), "n_d": int(p.n_d), "N_n": int(p.N_n)}
    if p.caseStatus != "solved":
        return out
    g = p.gamma_n[: p.N_n]
    out.update({
        "value": float(p._objectiveValue(p.objective)),
        "basis_today": float(p.basis),
        "bequest_today": float(_compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]),
        "deposits_today": [float(np.sum(p.d_in[i] / g)) for i in range(p.N_i)],
        "raw_deposits_today": [float(np.sum(p._raw_d[i] / g)) for i in range(p.N_i)],
        "netted_today": float(np.sum((p._raw_w0 - p.w_ijn[:, 0, :]) / g)),
        "surplus_today": float(np.sum(p.s_n / g)),
        "taxable_w_today": [float(np.sum(p.w_ijn[i, 0] / g)) for i in range(p.N_i)],
        "linking": plan_mod.Plan._add_surplus_deposit_linking is FREE,
        "deposit_years": [[2026 + n, round(float(p.d_in[0, n])), round(float(p.d_in[1, n])), round(float(p.s_n[n]))]
                          for n in range(p.N_n) if p.s_n[n] > 1 or p.d_in[:, n].sum() > 1],
        "both_years_d_and_w": int(np.sum([(p.d_in[i, n] > 1) and (p.w_ijn[1 - i, 0, n] > 1 or p.w_ijn[i, 0, n] > 1)
                                         for i in range(p.N_i) for n in range(p.n_d)])),
        "solverGap": getattr(p, "solverGap", None),
        "residuals": json.loads(json.dumps(getattr(p, "fixedPointResidual", None) or {}, default=float)),
    })
    return out


if __name__ == "__main__":
    jobs = [(h, s, dec, obj) for dec in ("exact", "ls") for obj in ("maxSpending", "maxBequest")
            for h in (92, 85) for s in (0.0, 0.5, 1.0, "free")]
    with ProcessPoolExecutor(4) as pool:
        for r in pool.map(run, jobs):
            print(json.dumps(r), flush=True)
