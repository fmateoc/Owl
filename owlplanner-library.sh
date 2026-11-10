#!/bin/bash
#
# Library-mode launcher (run-library-design.md, sections 3 and 10).
#
#     owlplanner-library.sh [household folder] [streamlit options]
#
# With a folder (any first argument that is not an option), everything the app makes or
# keeps for the household lives there: the run library in <folder>/library, the workbook the
# first-time setup writes, and a starter file to double-click next time. The folder is made
# if it is not there. The script can be called from anywhere.
#
# Without a folder the Run Library is in OWL_LIBRARY_DIR (default: otherFiles/library in this
# checkout, which git ignores). It holds household data, so the server binds to localhost
# only (R11). Other arguments pass through to streamlit; the plain launcher (owlplanner.sh)
# has no library.
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

here="$(cd "$(dirname "$0")" && pwd)"
if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then
    mkdir -p "$1" || exit 1
    OWL_HOME_DIR="$(cd "$1" && pwd)"
    export OWL_HOME_DIR
    export OWL_LIBRARY_DIR="$OWL_HOME_DIR/library"
    shift
    echo "Household folder: $OWL_HOME_DIR"
fi
cd "$here" || exit 1
echo Hit Ctrl-C to terminate the server.
export OWL_LIBRARY_DIR="${OWL_LIBRARY_DIR:-otherFiles/library}"
# toolbarMode "viewer": no Deploy, Rerun or Clear cache in the menu (UX review Q14); Print stays.
options="--browser.gatherUsageStats=false --browser.serverAddress=localhost --server.address=localhost --server.fileWatcherType=auto --client.toolbarMode=viewer $*"
uv run streamlit run ./ui/main.py $options
