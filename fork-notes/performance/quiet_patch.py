"""Experiment only (performance review 2026-11-10): a prototype, applied by rewriting the source of
`LocalSearch.solve` in memory. Nothing in `src/` changes.

Local search skips its steps (b), (b') and (a') in a loop iteration that follows one whose search
made no move from its LP start (the binaries the loop handed back are the ones it got). The cheap
(a) steps and (c) still run. No final confirming search is run: see the review for what that leaves open.
"""
import inspect, textwrap
from owlplanner import localsearch as L

src = textwrap.dedent(inspect.getsource(L.LocalSearch.solve))
def _d(t):
    return "\n".join(line[4:] if line.startswith("    ") else line for line in t.split("\n"))
def rep(a, b):
    global src
    a, b = _d(a), _d(b)
    assert src.count(a) == 1, (a, src.count(a))
    src = src.replace(a, b)
rep("        fams = self._families()\n",
    "        fams = self._families()\n        quiet = getattr(self, '_quiet', False)\n        start_obj = best[0]\n        lp_start = steps[0]['step'].startswith('start: previous binaries')\n")
rep('            if "zs" in fams:\n                A = copy.deepcopy(self.A)', '            if "zs" in fams and not quiet:\n                A = copy.deepcopy(self.A)')
rep('if "zs" in fams and "zl" in fams and not joint_done:', 'if "zs" in fams and "zl" in fams and not joint_done and not quiet:')
rep("            if len(others) > 1:\n", "            if len(others) > 1 and not quiet:\n")
rep("        best = (best[0], self._restore_links(best[1]), *best[2:])\n",
    "        self._quiet = lp_start and not (best[0] < start_obj - _IMPROVE * abs(start_obj))\n        best = (best[0], self._restore_links(best[1]), *best[2:])\n")
ns = {}
exec(compile(src, "<quiet solve>", "exec"), L.__dict__, ns)
L.LocalSearch.solve = ns["solve"]
