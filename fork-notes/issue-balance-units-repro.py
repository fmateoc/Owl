"""Balances typed in dollars into the $k fields (stock dev): what the solve says."""
import io
import sys

import owlplanner
from owlplanner.config import load_toml, config_to_plan

case = sys.argv[1]
print("owlplanner from:", owlplanner.__file__.rsplit("/src/", 1)[0].rsplit("/", 1)[-1])
for factor, what in ((1, "as entered ($k)"), (1000, "typed in dollars (x1000)")):
    diconf, dirname, _ = load_toml(case)
    sa = diconf["savings_assets"]
    for key in ("taxable_savings_balances", "tax_deferred_savings_balances", "tax_free_savings_balances"):
        sa[key] = [v * factor for v in sa[key]]
    if "taxable_cost_basis" in sa and sa["taxable_cost_basis"]:
        sa["taxable_cost_basis"] = [v * factor for v in sa["taxable_cost_basis"]]
    plan = config_to_plan(diconf, dirname, verbose=False, logstreams=[io.StringIO()])
    plan.solve(diconf["optimization_parameters"]["objective"], dict(diconf["solver_options"]))
    print(f"{what}: taxable {sa['taxable_savings_balances']} -> caseStatus {plan.caseStatus!r}")
