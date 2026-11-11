@ECHO OFF

:: Library-mode launcher (run-library-design.md, sections 3 and 10).
::
::     owlplanner-library.cmd [household folder] [streamlit options]
::
:: With a folder (any first argument that does not start with "-"), everything the app makes
:: or keeps for the household lives there: the run library in <folder>\library, the workbook
:: the first-time setup writes, and a starter file to double-click next time. The folder is
:: made if it is not there. The script can be called from anywhere.
::
:: Without a folder the Run Library is in OWL_LIBRARY_DIR (default: otherFiles\library in this
:: checkout, which git ignores). It holds household data, so the server binds to localhost
:: only (R11). Other arguments pass through to streamlit; the plain launcher (owlplanner.cmd)
:: has no library.
::
:: Solves run side by side on half of this computer's cores. To choose the number, set
:: OWL_LIBRARY_CORES before starting (set OWL_LIBRARY_CORES=1 for one solve at a time).

setlocal
set "OWL_FIRST=%~1"
set "OWL_REST=%*"
if "%OWL_FIRST%"=="" goto :start
if "%OWL_FIRST:~0,1%"=="-" goto :start
if not exist "%~f1\" mkdir "%~f1"
set "OWL_HOME_DIR=%~f1"
set "OWL_LIBRARY_DIR=%~f1\library"
set "OWL_REST=%2 %3 %4 %5 %6 %7 %8 %9"
echo Household folder: %OWL_HOME_DIR%

:start
cd /d "%~dp0"
echo Hit Ctrl-C to terminate the server.
if "%OWL_LIBRARY_DIR%"=="" set OWL_LIBRARY_DIR=otherFiles\library
:: toolbarMode "viewer": no Deploy, Rerun or Clear cache in the menu (UX review Q14); Print stays.
set options=--browser.gatherUsageStats=false --browser.serverAddress=localhost --server.address=localhost --server.fileWatcherType=auto --client.toolbarMode=viewer %OWL_REST%
uv run streamlit run .\ui\main.py %options%
