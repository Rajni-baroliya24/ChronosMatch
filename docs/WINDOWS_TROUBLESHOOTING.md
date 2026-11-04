\# Windows Troubleshooting



\## Website server occupies the terminal



When serve.py is running, the terminal remains occupied by the server.

This is normal. Keep it open and open the configured server address

in a browser. Use a second terminal for additional commands.

Press Ctrl+C to stop the server.



Start the website from the project root:



```bat

lowlatency\_output\\venv\\Scripts\\python.exe serve.py

```



\## Native extension cannot build



Install Microsoft C++ Build Tools with the Desktop development with C++

workload and a Windows SDK. Reopen the terminal after installation,

then build using the project's virtual environment:



```bat

lowlatency\_output\\venv\\Scripts\\python.exe setup\_lowlatency.py build\_ext --inplace

```



\## Require native processing during tests



Enable native-extension enforcement before running the test suite:



```bat

set CHRONOS\_REQUIRE\_NATIVE=1

lowlatency\_output\\venv\\Scripts\\python.exe -m pytest -q

```



The combined integration suite previously passed 125 tests on Windows

on 3 November 2026. Run the commands again to verify a different revision.



\## Terminal dashboard shows only a final JSON report



Observe the screen while the pipeline is running. A curses display may

restore the previous terminal contents when it exits. If no live display

appears, capture the running screen and investigate terminal initialization

and rendering. A completed JSON report alone does not verify dashboard rendering.



\## Website and native pipeline show different activity



The website uses the Python trading service. The native pipeline is a

separate demonstration and does not automatically update the website.

