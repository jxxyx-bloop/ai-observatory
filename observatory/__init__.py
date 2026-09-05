"""AI Observatory — read the logs your coding agent already writes.

The modules in here import each other by bare name (`import analyze`) rather
than as submodules, because they were written to be run out of a checkout with
`python3 observe.py`. `observe.py` puts its own directory on `sys.path` before
its first import, so both entry points — the script and the installed
`ai-observatory` command — resolve identically.
"""

__version__ = "0.1.0"
