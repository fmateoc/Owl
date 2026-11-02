#!/bin/bash
#
# Library-mode launcher (run-library-design.md, sections 3 and 10).
#
# The Run Library is switched on by OWL_LIBRARY_DIR (default: otherFiles/library, which git
# ignores) and holds household data, so the server binds to localhost only (R11). Other
# arguments pass through to streamlit; the plain launcher (owlplanner.sh) has no library.
#
# Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

echo Hit Ctrl-C to terminate the server.
export OWL_LIBRARY_DIR="${OWL_LIBRARY_DIR:-otherFiles/library}"
options="--browser.gatherUsageStats=false --browser.serverAddress=localhost --server.address=localhost --server.fileWatcherType=auto $*"
uv run streamlit run ./ui/main.py $options
