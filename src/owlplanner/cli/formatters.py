"""
JSON output formatter for solved Plan objects.

Converts a solved Plan to a structured dict suitable for JSON serialization.
All monetary values are in nominal dollars unless the key ends with ``_today``
or ``_today_dollars``.

Fork (ergonomics review S-4): each ``by_year`` row also carries its ``deflator`` (the plan's
cumulative inflation factor ``gamma_n``, 1 in the first year): an amount in today's dollars is
the nominal amount divided by it. The row's ``state_tax`` is ``st_T_n``, the state and local tax
net of the NY STAR credit, and three of its parts are given beside it:

    state_tax = state base + state_recapture + local_tax - star_credit

``local_tax`` is ``lt_T_n`` (NYC / Yonkers), ``state_recapture`` is ``st_recap_n`` (NY's
benefit recapture), ``star_credit`` is ``st_star_n`` (the STAR credit received, positive), and
the state base (the bracket tax less personal credits) is what is left. ``wages_by_person`` is
each person's wages (``omega_in``), for the run page's "last work year" markers.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors
"""

import json
import numpy as np

from owlplanner.export import plan_metrics, balance_sheet_arrays, cash_flow_split, fixedIncomeStreams
from owlplanner.brackets import bracket_view
from owlplanner.thresholds import threshold_proximity
from owlplanner.version import engine_provenance


class _NumpyEncoder(json.JSONEncoder):
    """Serialize numpy scalar types that the default encoder rejects."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def _round(val, decimals=0):
    """Round a numpy scalar to a Python int or float."""
    if decimals == 0:
        return int(round(float(val)))
    return round(float(val), decimals)


def _round_opt(val, decimals=2):
    """Round to *decimals*, passing None through."""
    return None if val is None else round(float(val), decimals)


def _metrics_to_summary(m: dict) -> dict:
    """
    Translate plan_metrics() snake_case float dict to the JSON summary block.

    Renames keys for JSON clarity (e.g. ``_today`` → ``_today_dollars``,
    explicit ``_nominal`` suffix) and rounds all monetary values to integers.
    """

    def r(key):
        return int(round(m[key]))

    return {
        "spending_basis_today_dollars": r("spending_basis"),
        "effective_tax_rate": round(m["effective_tax_rate"], 4),
        "total_spending_nominal": r("total_spending_nominal"),
        "total_spending_today_dollars": r("total_spending_today"),
        "total_fixed_income_nominal": r("total_fixed_income_nominal"),
        "total_fixed_income_today_dollars": r("total_fixed_income_today"),
        "ss_income_nominal": r("ss_income_nominal"),
        "ss_income_today_dollars": r("ss_income_today"),
        "pension_income_nominal": r("pension_income_nominal"),
        "pension_income_today_dollars": r("pension_income_today"),
        "spia_income_nominal": r("spia_income_nominal"),
        "wages_nominal": r("wages_nominal"),
        "roth_conversions_nominal": r("roth_conversions_nominal"),
        "roth_conversions_today_dollars": r("roth_conversions_today"),
        "federal_income_tax_nominal": r("federal_income_tax_nominal"),
        "federal_income_tax_today_dollars": r("federal_income_tax_today"),
        "ltcg_tax_nominal": r("ltcg_tax_nominal"),
        "niit_nominal": r("niit_nominal"),
        "payroll_tax_nominal": r("payroll_tax_nominal"),
        "payroll_tax_today_dollars": r("payroll_tax_today"),
        # SSA earnings test: 0 when it withholds nothing.
        "ss_withheld_nominal": r("ss_withheld_nominal"),
        "ss_withheld_today_dollars": r("ss_withheld_today"),
        "state_tax_nominal": r("state_tax_nominal"),
        "medicare_nominal": r("medicare_nominal"),
        "aca_nominal": r("aca_nominal"),
        "debt_payments_nominal": r("debt_payments_nominal"),
        "housing_costs_nominal": r("housing_costs_nominal"),
        "final_bequest_nominal": r("final_bequest_nominal"),
        "final_bequest_today_dollars": r("final_bequest_today"),
        "heirs_tax_liability_nominal": r("heirs_tax_liability_nominal"),
        "remaining_debt_balance": r("remaining_debt_balance"),
        "fixed_assets_start_nominal": r("fixed_assets_start_nominal"),
        "debt_start_nominal": r("debt_start_nominal"),
        "net_worth_start_nominal": r("net_worth_start_nominal"),
        "net_worth_start_today_dollars": r("net_worth_start_today"),
        "liquid_net_worth_start_nominal": r("liquid_net_worth_start_nominal"),
        "liquid_net_worth_start_today_dollars": r("liquid_net_worth_start_today"),
        "deferred_income_tax_start_nominal": r("deferred_income_tax_start_nominal"),
        "liquidation_tax_rate": round(m["liquidation_tax_rate"], 4),
        "liquidation_capgains_rate": round(m["liquidation_capgains_rate"], 4),
        "time_horizon_years": int(m["time_horizon_years"]),
        "cumulative_inflation_factor": round(m["inflation_factor"], 4),
    }


def plan_convergence(plan) -> dict:
    """How the self-consistent loop ended, and how far the plan is from the model its own income implies.

    "solved" says the loop stopped, not that the answer is self-consistent. Reporting the
    residual lets a caller tell a converged plan from one that merely ran out of patience,
    without re-deriving the tax quantities itself.
    """
    fpr = getattr(plan, "fixedPointResidual", None) or {}
    residual = {family: _round(v["abs_sum"]) for family, v in fpr.items()}
    # The families the log warns about (Plan._warnSSResidual, _warnLTCGResidual): the loop left
    # them above its own tolerance, and the exact model would settle them.
    tol = plan.N_n * getattr(plan, "_residual_tol", 0.0)
    vm = getattr(plan, "vm", None) or {}
    remedies = {}
    if "tss" not in vm and not isinstance(plan.solverOptions.get("withSSTaxability"), (int, float)):
        remedies["SS"] = 'withSSTaxability="optimize"'
    if not getattr(plan, "_ltcg_lp", False):
        remedies["LTCG"] = 'withLTCG="optimize"'
    unsettled = {
        family: remedy for family, remedy in remedies.items() if fpr.get(family, {}).get("abs_sum", 0.0) > tol
    }
    return {
        "convergence": plan.convergenceType,
        # How the tax breakpoints were solved: "loop", "branch-and-bound (...)", "local search (...)",
        # or "local search -> loop" when the search kept the loop's plan.
        "breakpoint_method": getattr(plan, "breakpointMethodUsed", "loop"),
        "fixed_point_residual_today_dollars": residual,
        # Families left above the loop's tolerance (residualTol per year), each with the option
        # whose exact model settles it; empty when the plan settled.
        "unsettled": unsettled,
        # Half the objective's oscillation band on an unsettled loop (as the Summary's
        # "Objective error bar" row; 0 when the loop settled): differences smaller than it
        # are not meaningful (run_library's comparison reads it).
        "objective_error_bar_today_dollars": _round_opt(
            float(getattr(plan, "oscillationAbs", 0.0) or 0.0) / 2.0, 2
        ),
        # Last solve's wall-clock and CPU seconds (machine- and load-dependent), as in the Summary.
        "solve_time_seconds": {
            "wall": _round_opt(getattr(plan, "lastSolveWallTime", None)),
            "cpu": _round_opt(getattr(plan, "lastSolveCPUTime", None)),
        },
    }


def plan_to_dict(plan) -> dict:
    """
    Serialize a solved Plan to a plain Python dict.

    Raises ValueError if the plan is not solved.
    """
    if plan.caseStatus != "solved":
        raise ValueError(f"Plan is not solved (status: {plan.caseStatus})")

    N = plan.N_n

    # ---- summary (via shared plan_metrics) ------------------------------
    m = plan_metrics(plan)
    summary = _metrics_to_summary(m)

    # ---- per-year arrays ------------------------------------------------
    spending = plan.g_n[:N]
    fed_tax = plan.T_n[:N]
    ltcg_tax = plan.U_n[:N]
    niit = plan.J_n[:N]
    payroll = plan.payroll_n[:N]
    state_tax = plan.st_T_n[:N]
    medicare = plan.medicare_n[:N]
    aca = plan.aca_costs_n[:N]
    roth_conv = np.sum(plan.x_in[:, :N], axis=0)
    ss_income = plan.zetaBar_in[:, :N]
    portfolio_total = np.sum(plan.b_ijn[:, :, :N], axis=(0, 1))
    gamma = plan.gamma_n[:N]
    # The parts of st_T_n (fork; see the module docstring). Plans built before these existed
    # lack the attributes: zeros keep plan.json well-formed.
    zeros = np.zeros(N)
    local_tax = np.asarray(getattr(plan, "lt_T_n", zeros), dtype=float)[:N]
    state_recapture = np.asarray(getattr(plan, "st_recap_n", zeros), dtype=float)[:N]
    star_credit = np.asarray(getattr(plan, "st_star_n", zeros), dtype=float)[:N]
    wages_in = np.asarray(plan.omega_in, dtype=float)[:, :N]  # each person's wages (the markers)
    # Income sources and the cash drawn from the savings accounts (the mix is in today's
    # dollars; back to nominal, like every other by_year amount).
    streams = fixedIncomeStreams(plan, N)
    withdrawals = np.asarray(plan.annual_cashflow_mix()["income"]["portfolio"], dtype=float)[:N] * gamma

    # Balance-sheet series (savings + fixed assets - debts, plus liquid net worth)
    bs = balance_sheet_arrays(plan, N)

    by_year = []
    for n in range(N):
        year = int(plan.year_n[n])
        by_year.append(
            {
                "year": year,
                "ages": [int(year - int(plan.yobs[i])) for i in range(plan.N_i)],
                "spending": _round(spending[n]),
                "federal_income_tax": _round(fed_tax[n]),
                "ltcg_tax": _round(ltcg_tax[n]),
                "niit": _round(niit[n]),
                "payroll_tax": _round(payroll[n]),
                "state_tax": _round(state_tax[n]),
                "local_tax": _round(local_tax[n]),
                "state_recapture": _round(state_recapture[n]),
                "star_credit": _round(star_credit[n]),
                "deflator": round(float(gamma[n]), 6),
                "wages_by_person": [_round(wages_in[i, n]) for i in range(plan.N_i)],
                "medicare_premiums": _round(medicare[n]),
                "aca_premiums": _round(aca[n]),
                "roth_conversions": _round(roth_conv[n]),
                "ss_income": [_round(ss_income[i, n]) for i in range(plan.N_i)],
                "wages": _round(streams["wages"][n]),
                "pension_income": _round(streams["pension"][n]),
                "spia_income": _round(streams["spia"][n]),
                "portfolio_withdrawals": _round(withdrawals[n]),
                "portfolio_total": _round(portfolio_total[n]),  # savings accounts only
                "fixed_assets": _round(bs["fixed_assets"][n]),
                "debt": _round(bs["debt"][n]),
                "net_worth": _round(bs["net_worth"][n]),
                "deferred_income_tax": _round(bs["deferred_income_tax"][n]),
                "disposition_costs": _round(bs["disposition_costs"][n]),
                "liquid_net_worth": _round(bs["liquid_net_worth"][n]),
            }
        )

    # ---- per-year cash-flow split (the run page's one-year Sankey, I6) ------
    cf = cash_flow_split(plan, N)
    cash_flow = {
        side: {name: [_round(v) for v in values] for name, values in rows.items()}
        for side, rows in cf.items()
    }

    # ---- Roth conversion schedule (non-zero years only) -----------------
    roth_schedule = []
    for n in range(N):
        total = float(roth_conv[n])
        if total > 1.0:
            entry = {
                "year": int(plan.year_n[n]),
                "ages": [int(plan.year_n[n]) - int(plan.yobs[i]) for i in range(plan.N_i)],
                "amount_nominal": _round(total),
                "amount_today_dollars": _round(total / float(gamma[n])),
            }
            if plan.N_i > 1:
                entry["by_person"] = {
                    plan.inames[i]: _round(float(plan.x_in[i, n]))
                    for i in range(plan.N_i)
                    if float(plan.x_in[i, n]) > 1.0
                }
            roth_schedule.append(entry)

    # ---- top-level document ---------------------------------------------
    state = plan.state if plan.state else "none"
    state_moves = [{"year": m.year, "state": m.state or "none", "locality": m.locality} for m in plan.state_moves]
    # What passes to non-spouse heirs at the first death (beneficiary fractions below 1), after
    # the heirs' tax, in today's dollars; year_n[n_d - 1] is the decedent's last year.
    partial = float(getattr(plan, "partialBequest", 0.0) or 0.0)
    partial_year = int(plan.year_n[max(0, plan.n_d - 1)]) if partial > 0 and plan.n_d < N else None
    return {
        "engine": engine_provenance(),
        "status": plan.caseStatus,
        **plan_convergence(plan),
        "case_name": plan._name,
        "objective": plan.objective,
        "individuals": list(plan.inames),
        # SS claiming ages in years (66y2m = 66.1667), aligned with `individuals`; what the
        # solve used, so two results can be compared without the cached plan (run library 9.1).
        "claiming_ages": [round(float(a), 4) for a in plan.ssecAges],
        "state": state,
        **({"locality": plan.locality} if plan.locality else {}),
        "state_moves": state_moves,
        "start_year": int(plan.year_n[0]),
        "end_year": int(plan.year_n[-1]),
        "time_horizon_years": N,
        "spending_year1_today_dollars": _round(spending[0]),
        "total_bequest_nominal": summary["final_bequest_nominal"],
        "total_bequest_today_dollars": summary["final_bequest_today_dollars"],
        "partial_bequest_today_dollars": _round(partial),
        "partial_bequest_year": partial_year,
        "summary": summary,
        "roth_conversions": {
            "total_nominal": summary["roth_conversions_nominal"],
            "total_today_dollars": summary["roth_conversions_today_dollars"],
            "schedule": roth_schedule,
        },
        # One year's sources and uses, per year (the run page's Sankey, I6): the cash flow
        # identity split along the design's lines, nominal $, sources equal to uses.
        "cash_flow": cash_flow,
        # "Things to look at" (I3): the years whose income sits just below or just over a
        # threshold the model knows, with the distance and the price of the crossing.
        "thresholds": threshold_proximity(plan),
        # The conversion and bracket view (I8): per year, taxable income, the conversion
        # layer, and the bracket, IRMAA and ACA lines it is measured against.
        "brackets": bracket_view(plan),
        "by_year": by_year,
    }


def plan_to_json(plan, indent: int = 2) -> str:
    """Return plan_to_dict serialized as a JSON string."""
    return json.dumps(plan_to_dict(plan), indent=indent, cls=_NumpyEncoder)


# ---------------------------------------------------------------------------
# Shared comparison helpers (used by cmd_compare.py and cmd_serve.py)
# ---------------------------------------------------------------------------

KEY_METRICS = [
    "spending_basis",
    "total_spending_today",
    "total_spending_nominal",
    "ss_income_today",
    "roth_conversions_today",
    "federal_income_tax_today",
    "state_tax_today",
    "medicare_today",
    "aca_today",
    "final_bequest_today",
    "final_bequest_nominal",
    "effective_tax_rate",
]


def _diff(base: dict, variant: dict) -> dict:
    """Compute numeric delta (variant minus base) for every key present in both dicts."""
    delta = {}
    for k in base:
        if k not in variant:
            continue
        bv, vv = base[k], variant[k]
        if isinstance(bv, (int, float)) and isinstance(vv, (int, float)):
            delta[k] = round(vv - bv, 6)
        else:
            delta[k] = None
    return delta


def _pct(delta_val, base_val):
    """Percent change, or None if base is zero."""
    if base_val and base_val != 0:
        return round((delta_val / abs(base_val)) * 100, 2)
    return None


def build_pct_change(delta: dict, base: dict) -> dict:
    """Return percent-change dict for KEY_METRICS, skipping None deltas."""
    return {k: _pct(delta[k], base[k]) for k in KEY_METRICS if k in delta and delta[k] is not None}
