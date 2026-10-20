# Integrating this edition with your ChronosMatch project

## Preserve your working project

Extract and run this edition in a new folder first. This package was prepared from the earlier `ChronosMatch_complete_reference.zip` and `ChronosMatch_web_dashboard.zip` archives, not from your current Windows checkout. Your current project may include newer work that must be preserved.

Do not delete your original folder, `.git` directory, teammate branches or commits. Do not copy `.venv`, `data`, caches or SQLite databases into Git.

## What to do with architecture.md

Keep the filename. The text you pasted is a useful initial proposal; you do not need a second file with the same headings. After reviewing the new implementation with your team, either replace its contents with this edition's `architecture.md`, or merge only sections that describe the code you actually adopt. Remove the old "initial proposal / pending confirmation" status only after the team agrees it is outdated.

## Review the changes

The existing models and price-time-priority order book are retained. `src/engine.py` additionally rejects duplicate IDs across an entire binary batch before applying it. `src/market_data.py` corrects the wire-size description to 37 bytes. New `src/service.py` and `app.py` add persistence, limits, order lifecycle, API, metrics and simulation behavior. `web/` replaces the earlier small dashboard. `web_app.py` preserves the earlier launch command.

Compare these files against your **current** checkout before copying. Preserve newer teammate changes and resolve differences deliberately. The new `app.py` should be used as a whole app with its matching `web/` assets and `src/service.py`; copying just the HTML into the old Flask template folder will not connect the new controls.

## Suggested integration sequence

1. Run this edition separately and complete its tests.
2. In your current Git checkout, run `git status` and check the branch. Preserve any existing uncommitted work.
3. Create a feature branch using your team's agreed branch naming, for example `feature/chronosmatch-studio`.
4. Bring in the reviewed service, app, web assets, requirements, tests and documentation. Compare core engine changes first.
5. Ensure `.gitignore` excludes `.venv/`, `data/`, `__pycache__/`, `.pytest_cache/`, and `*.sqlite3*`.
6. Install the updated development requirements and run `python -m pytest -q`.
7. Run the app, confirm the header says PYTHON ENGINE, and exercise demo, manual orders, cancellation and risk controls.
8. Review `git diff` and `git status`, stage only the intended source files, and commit. Push the feature branch and open a pull request into `develop`.
9. Merge into `main` only after integration review and tests pass.

If the folder you are using is not yet a Git repository, first resolve how it should be linked to the team's existing remote. Do not initialize or force-push over the remote as part of copying this package.
