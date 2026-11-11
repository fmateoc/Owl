"""Plain (unprofiled) rerun times of library pages, AppTest, median of several reruns.

    .venv/bin/python fork-notes/performance/page_timing.py <library folder> [reruns] [Page ...]

The library is `library_bench.py`'s (120 runs, a 36-member collection). Performance review P6.
"""
import os
import statistics
import sys
import time
from pathlib import Path

UI = str(Path(__file__).resolve().parents[2] / "ui")
root = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
pages = sys.argv[3:] or ["Library", "Collections", "Run", "Queue"]
os.environ["OWL_LIBRARY_DIR"] = root
os.chdir(UI)
sys.path.insert(0, UI)
from streamlit.testing.v1 import AppTest  # noqa: E402
from owlplanner.library import Library  # noqa: E402

runs = Library.open(root).runs()
for page in pages:
    at = AppTest.from_file(f"{UI}/{page}.py", default_timeout=300)
    at.session_state["run_page_last"] = runs[-1].id
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    times = []
    for _ in range(n):
        t = time.perf_counter()
        at.run()
        times.append(time.perf_counter() - t)
    print(f"{page:<12s} median {statistics.median(times):.3f} s  "
          f"(min {min(times):.3f}, max {max(times):.3f}, {n} reruns)")
