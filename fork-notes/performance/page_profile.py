"""Profile one library page's rerun on its script thread (yappi, wall clock; AppTest).

    uv pip install --python .venv/bin/python yappi
    .venv/bin/python fork-notes/performance/page_profile.py /tmp/bench/library Library 26

Times under yappi are several times the unprofiled ones: read the shares, not the seconds.
"""
import os
import sys
import time
from pathlib import Path

UI = str(Path(__file__).resolve().parents[2] / "ui")
root = sys.argv[1]; page = sys.argv[2]
os.environ["OWL_LIBRARY_DIR"] = root
os.chdir(UI)
sys.path.insert(0, UI)
import yappi
from streamlit.testing.v1 import AppTest
from owlplanner.library import Library
runs = Library.open(root).runs()
at = AppTest.from_file(f"{UI}/{page}.py", default_timeout=300)
at.session_state["run_page_last"] = runs[-1].id
at.run(); at.run()
yappi.set_clock_type("wall"); yappi.start()
t = time.perf_counter(); at.run(); dt = time.perf_counter() - t
yappi.stop()
print(page, "rerun under yappi", round(dt, 2), "s")
st = yappi.get_func_stats()
rows = [(s.ttot, s.tsub, s.ncall, s.module.replace(UI[:-2], "").split("site-packages/")[-1], s.lineno, s.name) for s in st]
rows.sort(reverse=True)
keep = [r for r in rows if ("ui/" in r[3][:4] or "owlplanner" in r[3] or r[5] in ("loads", "read_text", "dumps", "button", "columns", "container", "markdown", "popover", "_enqueue_message", "to_json", "selectbox", "text_input", "expander", "download_button", "dataframe", "plotly_chart", "stat", "flock"))]
for r in keep[:int(sys.argv[3]) if len(sys.argv) > 3 else 28]:
    print("%7.3f %7.3f %7d  %s:%d %s" % r)
