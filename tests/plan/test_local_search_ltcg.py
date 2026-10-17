"""
Fork: local search leaves the LTCG regime binaries free when it moves SS taxability (step (b)).

The `zl` binaries hold ordinary taxable income on one side of each LTCG threshold. Pinned while
SS moved, they blocked every move that needs both: on Case_john+sally the local-search preset
stopped at about 63% of branch-and-bound's bequest. Draft upstream issue: fork-notes/issue-ls-ltcg.md.
"""

import io
import pathlib

import pytest

import owlplanner as owl
from owlplanner import localsearch

_EXAMPLES = pathlib.Path(__file__).resolve().parents[2] / "examples"


def _load(case="Case_john+sally.toml"):
    return owl.readConfig(str(_EXAMPLES / case), verbose=False, logstreams=[io.StringIO()])


def test_ss_step_leaves_ltcg_free(monkeypatch):
    """Every restricted solve with the local-branching row (step (b)) leaves the `zl` columns free."""
    calls = []
    orig = localsearch.LocalSearch._mip

    def spy(self, options, overrides=None, A=None, warm=None, lp=False):
        if A is not None:
            zl = set(int(c) for c in self._cols("zl"))
            calls.append((len(zl), sorted(zl & set(overrides or {}))))
        return orig(self, options, overrides=overrides, A=A, warm=warm, lp=lp)

    monkeypatch.setattr(localsearch.LocalSearch, "_mip", spy)
    p = _load()
    p.solve(p.objective, options={**p.solverOptions, "breakpointMethod": "local-search", "localSearchTime": 1})
    assert p.caseStatus == "solved"
    assert calls, "no SS step ran"
    assert all(n_zl > 0 for n_zl, _ in calls), "the case has no LTCG binaries"
    assert all(not pinned for _, pinned in calls), calls


@pytest.mark.toml
def test_john_sally_reaches_branch_and_bound():
    """The preset stopped at 20,004 against branch-and-bound's 31,778; it now reaches branch-and-bound."""
    bb = _load()
    bb.solve(bb.objective, options={**bb.solverOptions, "breakpointMethod": "branch-and-bound"})
    ls = _load()
    ls.solve(ls.objective, options={**ls.solverOptions, "breakpointMethod": "local-search"})
    assert bb.caseStatus == "solved" and ls.caseStatus == "solved"
    assert ls.bequest >= bb.bequest * (1 - 0.005), (ls.bequest, bb.bequest)
