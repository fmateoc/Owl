"""
The run library's job manager for the interface: one per server process (design section 8.2).

`get_manager()` is the `st.cache_resource` singleton every page shares (R5: two tabs see one
queue), and it starts the manager's ticker thread (review H5): the queue dispatches waiting
jobs and adopts or interrupts running ones whether or not a Queue page is open. `main.py`
calls it on every page load when the library is on (`OWL_LIBRARY_DIR`), so the ticker runs
from the first page a browser opens after a server restart.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import streamlit as st

from owlplanner.library import JobManager, Library
from owlplanner.library.store import default_library_root


def library_address_ok() -> bool:
    """Section 10, R11: library mode is localhost only.

    A running app cannot rebind its own server, so the check is on the configured bind
    address: the library pages are refused unless the server listens on localhost. The
    library-mode launcher (`owlplanner-library.cmd` / `.sh`) passes `--server.address=localhost`.
    """
    return str(st.get_option("server.address")).strip().lower() in ("localhost", "127.0.0.1")


@st.cache_resource
def _manager(root: str):
    manager = JobManager(Library.open(root))
    manager.start_ticker()
    return manager


def get_manager():
    """The server's job manager over the library folder (`OWL_LIBRARY_DIR`), ticking."""
    return _manager(str(default_library_root()))
