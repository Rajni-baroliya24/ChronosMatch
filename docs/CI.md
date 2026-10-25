# Continuous Integration Guide

ChronosMatch uses GitHub Actions to check the project automatically.

## Workflow location

.github/workflows/chronosmatch-tests.yml

## When tests run

- Pushes to main, develop, and feature/** branches.
- Pull requests targeting main or develop.

## Test environments

The workflow runs two jobs:

| Operating system | Python | Node.js |
| --- | --- | --- |
| Ubuntu | 3.13 | 24 |
| Windows | 3.13 | 24 |

Each job installs the Python development dependencies, runs pytest,
and runs the browser-engine checks.

Node.js also enables the browser/Python parity test.

## Run checks locally

Run these commands from the project root:

    python -m pip install -r requirements-dev.txt
    python -m pytest -q
    node tests/browser_engine.test.cjs

The final command requires Node.js.

## Find results

Open the repository's Actions tab and select a ChronosMatch tests run.
Select a Windows or Ubuntu job, then expand the test step to read its output.

## If a check fails

1. Find the first failed step and read its error message.
2. Reproduce the failure locally using the corresponding command above.
3. Fix the cause and run the checks again.
4. Commit and push the fix to the same feature branch.
5. Confirm the new workflow run succeeds.

Do not remove failing tests merely to make the workflow pass.

## Scope

Passing checks validate the scenarios covered by the tests.
They do not establish production trading readiness or guarantee performance.