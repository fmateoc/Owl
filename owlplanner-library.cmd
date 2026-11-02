@ECHO OFF

:: Library-mode launcher (run-library-design.md, sections 3 and 10).
:: The Run Library is switched on by OWL_LIBRARY_DIR (default: otherFiles\library, which git
:: ignores) and holds household data, so the server binds to localhost only (R11). Other
:: arguments pass through to streamlit; the plain launcher (owlplanner.cmd) has no library.

echo Hit Ctrl-C to terminate the server.
if "%OWL_LIBRARY_DIR%"=="" set OWL_LIBRARY_DIR=otherFiles\library
set options=--browser.gatherUsageStats=false --browser.serverAddress=localhost --server.address=localhost --server.fileWatcherType=auto %*
uv run streamlit run .\ui\main.py %options%
