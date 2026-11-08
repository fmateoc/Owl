"""
Optimization Parameters page for Owl retirement planner Streamlit UI.

This module provides the interface for setting optimization parameters
including spending profiles, Medicare options, and other optimization settings.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import streamlit as st
from datetime import date
from owlplanner.utils import last_year_entered

import sskeys as kz
import owlbridge as owb
import case_progress as cp
from moseklicense import hasMOSEK


def _ssAgesMode(names, selected):
    """The ssAgesMode value for the individuals selected for claiming-age optimization."""
    if len(names) == 2 and len(selected) == 2:
        return "both"
    return selected[0] if selected else "none"


def _onSSAgesChange(names):
    selected = [n for i, n in enumerate(names) if st.session_state.get(kz.genCaseKey(f"ssAgesOpt{i}"))]
    kz.setCaseKey("ssAgesMode", _ssAgesMode(names, selected))


def _moved_text(label, old, new, low, high, low_name="the plan's first year"):
    """A clamped year in words (review AN2): "Year to stop considering Roth conversions: 2500
    is past the last year accepted, 2146; shown as 2146"."""
    where = (f"past the last year accepted, {high}" if old > high
             else f"before {low_name}, {low}")
    return f"{label}: {old} is {where}; shown as {new}"


def _onAcaFromStart():
    """The marketplace toggle (QW-8.3, decision 5): on stores 0, the code's "from the plan
    start"; off stores next year (the plan's last at most) for the year box to show."""
    on = st.session_state.get(kz.genCaseKey("acaFromPlanStart"))
    plan = kz.getCaseKey("plan")
    years = getattr(plan, "year_n", None) if plan is not None else None
    end = int(years[-1]) if years is not None and len(years) else date.today().year + 40
    year = 0 if on else min(date.today().year + 1, end)
    kz.setCaseKey("acaStartYear", year)
    st.session_state[kz.genCaseKey("acaStartYear")] = year


def _bound_year(key, low, high, neutral_low=True):
    """Clamp a stored year field into [low, high] (UX remediation QW-8's input bounds).

    Streamlit silently shows the bound instead of a stored value outside it, so the case keeps
    what the field shows. Moving a value is never silent (review AM3): the page names every
    move. A move **up** to the plan's first year is the neutral one -- a year before the
    plan's first year means "from its first year" (what `sanitize_config` does at load) -- so
    the case keeps its status. A move **down** to the upper bound (or up to a later start year)
    changes what the input means, so the case is flagged modified: its results are stale.
    Returns the old value when one moved, else None.
    """
    value = kz.getCaseKey(key)
    if value is None:
        return None
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    if low <= year <= high:
        return None
    moved = min(max(year, low), high)
    if year > high or not neutral_low:
        kz.setCaseKey(key, moved)  # flags "modified": the meaning changed
    else:
        kz.storeCaseKey(key, moved)  # neutral (before the plan's first year = from it)
    st.session_state[kz.genCaseKey(key)] = moved
    return year


kz.initCaseKey("computeMedicare", True)
kz.initCaseKey("optimizeMedicare", False)
kz.initCaseKey("slcspAnnual", 0)
kz.initCaseKey("acaStartYear", 0)
kz.initCaseKey("optimizeACA", False)
kz.initCaseKey("otherMedical", 0)
kz.initCaseKey("medicalExcess", 0)
kz.initCaseKey("optimizeLTCG", False)
kz.initCaseKey("optimizeNIIT", False)
kz.initCaseKey("localSearch", False)
kz.initCaseKey("mipStrategy", "branch-and-bound")
kz.initCaseKey("ssTaxabilityMode", "loop")
kz.initCaseKey("ssTaxabilityValue", 0.85)
# Fork: withItemized and withSTAR (config.ui_bridge.SOLVER_UI_PASSTHROUGH_KEYS) are not
# initialized here (review Y3): a stored default would be written by ui_to_config and make an
# unchanged case save as a changed run. Their radios show "loop" (Plan's default) until a choice.


ret = kz.titleBar(":material/tune: Run Options")

if ret is None or kz.caseHasNoPlan():
    kz.no_case_info()
else:
    thisyear = date.today().year
    # Upstream #250: a year field accepts any year up to last_year_entered (past any plan, so a
    # year beyond the plan still says "never" when longevity changes); an extra digit is refused.
    last_year = last_year_entered(thisyear)
    # Fork, QW-8 (review AM3): a stored year outside its field's range is set to the nearest
    # allowed one here, once, and the page says which values moved, by the field's own label
    # (review AN2). The low bound is this year, or the start year for the stop year (fork); the
    # ACA start year's 0 means "from the plan start" (its toggle below) and is never moved.
    _moved = []
    for _key, _label in (("startRothConversions", "Year to start considering Roth conversions"),
                         ("stopRothConversions", "Year to stop considering Roth conversions"),
                         ("swapRothConvertersYear", "Year to switch converters"),
                         ("acaStartYear", "ACA start year")):
        if _key == "acaStartYear" and kz.getCaseKey(_key) in (0, None):
            continue
        _by_start = _key == "stopRothConversions" and kz.getCaseKey("stopRothConversionsEnabled")
        _low = int(kz.getCaseKey("startRothConversions") or thisyear) if _by_start else thisyear
        _old = _bound_year(_key, _low, last_year, neutral_low=_low <= thisyear)
        if _old is not None:
            _low_name = "the start year" if _low > thisyear else "the plan's first year"
            _moved.append(_moved_text(_label, _old, kz.getCaseKey(_key), _low, last_year, _low_name))
    if _moved:
        st.caption("; ".join(_moved) + ".")
    st.markdown("#### :orange[Roth Conversions]")
    col1, col2, col3 = st.columns(3, gap="large", vertical_alignment="top")
    with col1:
        iname0 = kz.getCaseKey("iname0")
        helpmsg = (
            "Value is in nominal \\$k. A year held fixed with the *Roth conv fixed* column "
            "of the *Wages and Contributions* table is not subject to this maximum."
        )
        kz.initCaseKey("maxRothConversion", 50)
        ret = kz.getNum("Maximum annual Roth conversion (\\$k)", "maxRothConversion", help=helpmsg)
        # kz.initCaseKey("oppCostX", 0.)
        # helpmsg = "Estimated opportunity cost for paying estimated tax on Roth conversions."
        # ret = kz.getNum("Opportunity cost for conversion (%)", "oppCostX", step=0.01, format="%.2f",
        #                min_value=0., max_value=5., help=helpmsg)

    with col2:
        helpmsg = "Do not perform Roth conversions before that year."
        kz.initCaseKey("startRothConversions", thisyear)
        ret = kz.getIntNum(
            "Year to start considering Roth conversions",
            "startRothConversions",
            min_value=thisyear,
            max_value=last_year_entered(thisyear),
            help=helpmsg,
        )
        # An explicit toggle, not a year derived from the plan horizon: a derived default
        # is stored once and never revisited, so extending life expectancy later would
        # leave a stale year quietly blocking conversions the user never meant to block.
        kz.initCaseKey("stopRothConversionsEnabled", False)
        helpmsg = (
            "Stop Roth conversions partway through the plan. Off means they are considered "
            "to the end. Together with the year above, this bounds conversions to a window."
        )
        ret = kz.getToggle("Stop Roth conversions mid-plan", "stopRothConversionsEnabled", help=helpmsg)
        if kz.getCaseKey("stopRothConversionsEnabled"):
            _start = int(kz.getCaseKey("startRothConversions") or thisyear)
            kz.initCaseKey("stopRothConversions", max(thisyear + 10, _start))
            helpmsg = "No Roth conversions are performed in this year or later."
            ret = kz.getIntNum(
                "Year to stop considering Roth conversions",
                "stopRothConversions",
                min_value=_start,
                max_value=last_year_entered(thisyear),
                help=helpmsg,
            )
    with col3:
        if kz.getCaseKey("status") == "married":
            iname1 = kz.getCaseKey("iname1")
            choices = ["none", iname0, iname1]
            kz.initCaseKey("noRothConversions", choices[0])
            kz.initCaseKey("swapRothConvertersEnabled", False)
            swapon = kz.getCaseKey("swapRothConvertersEnabled")
            excludeset = kz.getCaseKey("noRothConversions") != "none"

            helpmsg = "`none` means no exclusion. To exclude both spouses, set `Maximum annual Roth conversion` to 0."
            # Only lock a control once it is at its default, so a pre-existing conflicting
            # state (both set) always leaves at least one control free to resolve it.
            excludeoff = swapon and not excludeset
            if excludeoff:
                helpmsg += " Disabled while *Swap Roth converters mid-plan* is enabled."
            ret = kz.getRadio(
                "Exclude Roth conversions for...", choices, "noRothConversions", help=helpmsg, disabled=excludeoff
            )

            # st.divider()
            swapoff = excludeset and not swapon
            helpmsg = (
                "Switch which spouse performs Roth conversions partway through the plan. "
                "This overrides the exclusion above."
            )
            if swapoff:
                helpmsg += " Disabled while an exclusion is set above."
            ret = kz.getToggle(
                "Swap Roth converters mid-plan", "swapRothConvertersEnabled", help=helpmsg, disabled=swapoff
            )
            if kz.getCaseKey("swapRothConvertersEnabled"):
                kz.initCaseKey("swapRothConvertersFirst", iname0)
                ret = kz.getSelectbox("Converts first", [iname0, iname1], "swapRothConvertersFirst")
                kz.initCaseKey("swapRothConvertersYear", thisyear)
                helpmsg = "Year in which the other spouse takes over Roth conversions."
                ret = kz.getIntNum(
                    "Year to switch converters",
                    "swapRothConvertersYear",
                    min_value=thisyear,
                    max_value=last_year_entered(thisyear),
                    help=helpmsg,
                )

    st.divider()
    st.markdown("#### :orange[Health Insurance]")
    st.markdown("##### Qualified Medical Expenses")
    cols = st.columns(3, gap="large", vertical_alignment="top")
    with cols[0]:
        helpmsg_med = (
            "Annual non-Medicare non-ACA qualified medical expenses (dental, vision, co-pays, deductibles, etc.) "
            "in today's dollars. HSA withdrawals are capped at this amount plus any Medicare costs. "
            "These expenses are treated as part of general living costs, not as separate healthcare costs. "
            "Ignore if plan has no HSA."
        )
        kz.getNum(
            "Other medical expenses (\\$k/year)",
            "otherMedical",
            step=1.0,
            min_value=0.0,
            format="%.2f",
            help=helpmsg_med,
        )
    with cols[1]:
        helpmsg_excess = (
            "How much faster than inflation medical prices grow each year, in percent. "
            "Applies to Medicare premiums, the ACA benchmark premium, and other medical expenses. "
            "Tax brackets, IRMAA thresholds, and the poverty line still follow inflation. "
            "Set to 0 to keep medical prices in step with inflation."
        )
        kz.getNum(
            "Medical prices above inflation (%/year)",
            "medicalExcess",
            step=0.5,
            min_value=0.0,
            max_value=10.0,
            format="%.2f",
            help=helpmsg_excess,
        )

    st.markdown("##### ACA Marketplace (Pre-65)")
    helpmsg = (
        "Annual premium for the second-lowest-cost Silver plan in your area. "
        "Used to compute Premium Tax Credit. Set to 0 to exclude ACA costs. "
        "Applies only in years before Medicare (age 65). "
        "See [Healthcare.gov](https://healthcare.gov) for your SLCSP."
    )
    cols = st.columns(3, gap="large", vertical_alignment="top")
    with cols[0]:
        kz.getNum(
            "Benchmark Silver plan premium (SLCSP) (\\$k/year)",
            "slcspAnnual",
            step=1.0,
            min_value=0.0,
            format="%.2f",
            help=helpmsg,
        )
    with cols[1]:
        acaoff = (kz.getCaseKey("slcspAnnual") or 0) <= 0
        # QW-8.3's second pass (decision 5, review AN2): a toggle for "from the plan start",
        # which stores 0, the code's own sentinel (no message, no change to a saved file); off,
        # a year box from this year on (upstream #250's bound, past any plan). The build's year
        # field stored this year in every case without the key and announced "acaStartYear 0 -> 2026".
        _from_start = kz.getCaseKey("acaStartYear") in (0, None)
        kz.initGlobalKey(kz.genCaseKey("acaFromPlanStart"), _from_start)
        st.toggle("Marketplace coverage from the plan start", key=kz.genCaseKey("acaFromPlanStart"),
                  on_change=_onAcaFromStart, disabled=acaoff,
                  help="On: marketplace (ACA) coverage from the plan's first year. Off: from the "
                       "year below; the years before it are assumed employer-covered (no ACA "
                       "cost).")
        if not _from_start:
            kz.getIntNum(
                "ACA start year",
                "acaStartYear",
                min_value=thisyear,
                max_value=last_year_entered(thisyear),
                step=1,
                help="The calendar year marketplace coverage begins (e.g. 2029 for the year of "
                     "retirement).",
                disabled=acaoff,
            )

    st.markdown("##### Medicare")
    cols = st.columns(3, gap="large", vertical_alignment="top")
    with cols[0]:
        kz.initCaseKey("computeMedicare", True)
        helpmsg = "Compute Medicare and IRMAA premiums."
        medion = kz.getToggle("Medicare and IRMAA calculations", "computeMedicare", help=helpmsg)

    if kz.getCaseKey("computeMedicare"):
        helpmsg = "MAGI in nominal \\$k for current and previous years."
        years = owb.backYearsMAGI()
        for ii in range(2):
            kz.initCaseKey("MAGI" + str(ii), 0)
            if years[ii] > 0:
                with cols[1 + ii]:
                    ret = kz.getNum(f"MAGI for {years[ii]} (\\$k)", "MAGI" + str(ii), help=helpmsg)

        cols = st.columns(3, gap="large", vertical_alignment="top")
        with cols[0]:
            kz.initCaseKey("includeMedicarePartD", True)
            helpmsg_partd = (
                "Include Medicare Part D premiums (IRMAA surcharges use same MAGI brackets as Part B). "
                "Turn off if you have other drug coverage (e.g. employer, VA)."
            )
            kz.getToggle("Include Part D premiums", "includeMedicarePartD", help=helpmsg_partd)
        with cols[1]:
            kz.initCaseKey("medicarePartDBasePremium", None)
            helpmsg_partd_base = (
                "Optional monthly Part D base premium per person (today's \\$). "
                "Set to 0 to omit. National average ~\\$39–47 per month."
            )
            kz.getNum(
                "Part D base premium (\\$/month per person)",
                "medicarePartDBasePremium",
                step=1.0,
                min_value=0.0,
                format="%.2f",
                help=helpmsg_partd_base,
            )

    st.divider()
    st.markdown("#### :orange[Social Security Claiming Ages]")
    helpmsg = (
        "Select which individuals should have their SS claiming month optimized "
        "(any month between age 62 and 70). "
        "Optimal ages are written back to the Fixed Income page and in the Synopsis after solving."
    )
    col1, col2 = st.columns(2, gap="large", vertical_alignment="top")
    with col1:
        names = [kz.getCaseKey("iname0")]
        if kz.getCaseKey("status") == "married":
            names.append(kz.getCaseKey("iname1"))

        # Someone whose entered claiming age is already past cannot be optimized (the solver
        # refuses it): that name stays listed, disabled, and is dropped from the selection.
        past = kz.ssPastAgeNames()
        kz.initCaseKey("ssAgesMode", "none")
        mode = kz.getCaseKey("ssAgesMode") or "none"
        selected = [n for n in names if (mode == "both" or mode == n) and n not in past]
        if _ssAgesMode(names, selected) != mode:
            kz.setCaseKey("ssAgesMode", _ssAgesMode(names, selected))
        st.markdown("Optimize SS claiming age for...", help=helpmsg)
        for i, (box, name) in enumerate(zip(st.columns(len(names)), names)):
            key = kz.genCaseKey(f"ssAgesOpt{i}")
            st.session_state[key] = name in selected
            with box:
                st.checkbox(name, key=key, disabled=name in past, on_change=_onSSAgesChange, args=[names])
        for name in past:
            st.caption(
                f"{name}'s claiming age entered on the *Fixed Income* page is already past, so it cannot be "
                f"optimized. If {name} is not yet collecting, enter a claiming age from this month on to "
                "make it available here."
            )

    st.divider()
    with st.expander("*Advanced options*"):
        # Above "Calculations" on purpose: the local-search caption there says it overrides
        # "every breakpoint below", which is true of the MILP settings and not of these two.
        st.markdown("#### :orange[Deductions and Credits]")
        col1, col2 = st.columns(2, gap="large", vertical_alignment="top")
        with col1:
            helpmsg = (
                "Fork: whether a year deducts its itemized total (state and local taxes up to the SALT "
                "cap, property tax, mortgage interest, charity and medical above their floors; New York "
                "has its own itemized deduction) or the standard deduction. The larger of the two is "
                "deducted, year by year. ’loop’ decides from the previous step of the self-consistent "
                "iteration; ’none’ turns itemizing off everywhere (the standard deduction)."
            )
            ret = kz.getRadio("Itemized deductions", ["loop", "none"], "withItemized", help=helpmsg)
        with col2:
            helpmsg = (
                "Fork: the NY STAR credit for an owner in a school district chosen on the Create Case "
                "page (Basic, and Enhanced from 65 under the income limit). ’loop’ reads the credit "
                "from the previous step of the iteration; ’optimize’ lets the plan hold its income "
                "under the Enhanced limit where that pays (binary variables); ’none’ turns the credit "
                "off. Local search solves it with binary variables too (’loop’ and ’optimize’ mean the "
                "same there), and keeps ’none’."
            )
            ret = kz.getRadio("NY STAR credit", ["loop", "optimize", "none"], "withSTAR", help=helpmsg)

        st.divider()
        st.markdown("#### :orange[Calculations]")
        helpmsg_ls = (
            "Carry the tax breakpoints (Social Security taxability, Medicare, ACA, capital gains and "
            "NIIT) as binary variables and solve them by local search (fix-and-optimize): small "
            "restricted problems around the iteration's plan instead of a full branch-and-bound. "
            "Usually a somewhat better plan than the iteration, in seconds to a few minutes; "
            "not a proven optimum. The plan is never worse than the iteration's. "
            "Overrides a fixed Social Security taxable fraction: the IRS formula applies instead."
        )
        ls_on = kz.getToggle("Solve tax breakpoints by local search (expert)", "localSearch", help=helpmsg_ls)
        if ls_on:
            st.caption(
                "Local search sets every breakpoint below to MILP, Social Security taxability included; "
                "the individual settings do not apply."
            )
        col1, col2 = st.columns([40, 60], gap="large", vertical_alignment="top")
        with col1:
            helpmsg = (
                "Option to optimize Medicare using binary variables."
                "  Use with caution as some cases might not converge"
                " without adjusting additional solver parameters."
            )
            medioff = not medion
            ret = kz.getToggle(
                "Solve Medicare brackets with MILP (expert)", "optimizeMedicare", help=helpmsg,
                disabled=medioff or ls_on,
            )
            acaoff = (kz.getCaseKey("slcspAnnual") or 0) <= 0
            helpmsg_aca = (
                "Choose the ACA bracket inside the optimization instead of by iteration. "
                "Exact at a bracket edge, and slower. Only applies when SLCSP > 0."
            )
            ret = kz.getToggle(
                "Solve ACA brackets with MILP (expert)", "optimizeACA", help=helpmsg_aca, disabled=acaoff or ls_on
            )
        with col2:
            kz.initCaseKey("noLateSurplus", False)
            helpmsg = (
                "Disallow cash-flow surpluses in the last two years of the plan."
                " This avoids sheltering transfers when market goes down in last years."
            )
            ret = kz.getToggle("Disallow cash-flow surpluses in the last 2 years", "noLateSurplus", help=helpmsg)
            helpmsg_ltcg = (
                "Choose the capital-gains bracket inside the optimization instead of by "
                "iteration, for the stacking of ordinary income under long-term gains. "
                "Exact at a bracket edge, and slower."
            )
            ret = kz.getToggle(
                "Solve LTCG brackets with MILP (expert)", "optimizeLTCG", help=helpmsg_ltcg, disabled=ls_on
            )
            helpmsg_niit = (
                "Decide inside the optimization whether income crosses the Net Investment "
                "Income Tax threshold, instead of by iteration. Only has an effect when the "
                "capital-gains brackets are solved the same way."
            )
            ret = kz.getToggle(
                "Solve NIIT threshold with MILP (expert)", "optimizeNIIT", help=helpmsg_niit, disabled=ls_on
            )
        any_milp = any(
            kz.getCaseKey(k) for k in ("optimizeMedicare", "optimizeACA", "optimizeLTCG", "optimizeNIIT")
        ) or kz.getCaseKey("ssTaxabilityMode") == "optimize"
        helpmsg_strategy = (
            "How the breakpoints set to MILP are solved. 'branch-and-bound': the complete search, "
            "which stops at the solver gap or time limit. 'local-search': fix-and-optimize around the "
            "iteration's plan, faster, not a proven optimum."
        )
        ret = kz.getRadio(
            "MILP strategy (expert)", ["branch-and-bound", "local-search"], "mipStrategy",
            help=helpmsg_strategy, disabled=ls_on or not any_milp,
        )

        st.divider()
        st.markdown("#### :orange[Social Security Taxability]")
        col1, col2, col3 = st.columns(3, gap="large", vertical_alignment="top")
        with col1:
            choices = ["loop", "value", "optimize"]
            kz.initCaseKey("ssTaxabilityMode", "loop")
            helpmsg = (
                "’loop’: compute SS taxable fraction dynamically via the self-consistent loop. "
                "’value’: pin SS taxable fraction to a fixed value (enter in box). "
                "’optimize’: solve taxable SS within the optimization using binary variables (expert)."
            )
            ret = kz.getRadio("SS taxability method", choices, "ssTaxabilityMode", help=helpmsg, disabled=ls_on)
        with col2:
            if kz.getCaseKey("ssTaxabilityMode") == "value":
                kz.initCaseKey("ssTaxabilityValue", 0.85)
                helpmsg = (
                    "SS taxable fraction \u2208 [0, 0.85]. "
                    "Use 0.0 (Provisional income (PI) below lower threshold), "
                    "0.5 (mid-range), or 0.85 (high PI)."
                )
                ret = kz.getNum(
                    "Fixed SS taxable fraction",
                    "ssTaxabilityValue",
                    min_value=0.0,
                    max_value=0.85,
                    step=0.05,
                    format="%.2f",
                    help=helpmsg,
                )

        st.divider()
        st.markdown("#### :orange[Solver]")
        choices = ["default", "HiGHS"]
        kz.initCaseKey("solver", choices[0])
        kz.initCaseKey("xtraOptions", "")

        if hasMOSEK():
            choices += ["MOSEK"]
        elif kz.getCaseKey("solver") == "MOSEK":
            kz.setCaseKey("solver", choices[0])

        col1, col2 = st.columns([45, 55], gap="large", vertical_alignment="top")
        with col1:
            helpmsg = (
                "Select different solvers for comparison purposes."
                " For best performance, use MOSEK if available. Otherwise use HiGHS."
                " 'default' automatically picks MOSEK when available, otherwise HiGHS."
            )
            ret = kz.getRadio("Linear programming solver", choices, "solver", help=helpmsg)
            if kz.getCaseKey("solver") == "default":
                resolved = "MOSEK" if hasMOSEK() else "HiGHS"
                st.caption(f"Will use: **{resolved}**")
        with col2:
            helpmsg = (
                'Additional solver options as a dictionary (e.g., \'{"key1": "value1", "key2": 123}\'). '
                "These options will be merged into the solver options dictionary. "
                "Leave empty unless experimenting with solver."
            )
            ret = kz.getText(
                "Extra solver options (expert)", "xtra_options", placeholder='{"key": "value"}', help=helpmsg
            )

    st.divider()
    # Show progress bar at bottom (only when case is defined)
    cp.show_progress_bar(divider=False)
