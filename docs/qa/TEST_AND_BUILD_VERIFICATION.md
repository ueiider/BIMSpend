# Test and build verification

6 November 2026. Local Linux, Python 3.12, isolated temporary QA dependencies and synthetic fixtures. Python source compilation succeeded on main, R1-08 and FCC. No watcher, production service, add-in or real data was used.

| Snapshot | Current execution | Scope |
|---|---|---|
| main 65e344b | 28 passed, 6 GUI deselected | Run `PYTHONPATH=src python -m pytest -q -m 'not gui'`. Attribution, event idempotency, synthetic AW/Revit import and overlap/AFK, review retention, time states, permissions, team, reports, estimating, finance and packaging paths. |
| R1-08 02257ab full non-GUI selection | Collection stopped with four errors | `capture/session_lock.py:131` calls Windows-only `ctypes.WINFUNCTYPE` at import time. Capture, correlation, suggestion domain and suggestion engine test modules error on Linux. |
| R1-08 reduced non-GUI selection | 110 passed, 7 GUI deselected | Same pytest command ignoring `tests/capture/test_capture_module.py`, `test_correlation.py`, `test_suggestion_domain.py`, `test_suggestion_engine.py` under that directory. Includes P0 migration/concurrency/auth and financial tests. |
| FCC 31a7713 | 7 pytest tests passed and schema script reported 60/60 | Run from recovered root with `python -m pytest -q aw_adapter` and `python tests/test_schemas.py`. Uses fixtures and local temporary queues. No FCC end-to-end HTTP, named pipe, Revit host or deployed service test. |

The local pytest runs emitted an installed AnyIO plugin deprecation warning. No display server, Windows host, dotnet or Autodesk reference assemblies were available for current GUI/build execution. C# compilation and real read-only Revit callback/IPC validation are pending. R1-08 full Windows domain and GUI at its own HEAD remain unverified in this audit.

| Prior GitHub Actions evidence | What it establishes |
|---|---|
| [main tests, 42095663150](https://github.com/ueiider/BIMSpend/actions/runs/42095663150) | Successful Windows workflow at 65e344b. Test script selects domain tests and six isolated Tkinter test cases. |
| [main package, 42167781841](https://github.com/ueiider/BIMSpend/actions/runs/42167781841) | Successful dispatch at 65e344b. Preview folder artifact 13479896244 listed as unexpired. |
| [R1-08 package, 42166458043](https://github.com/ueiider/BIMSpend/actions/runs/42166458043) | Successful package/synthetic startup smoke at 02257ab. Preview artifact 13479053018 listed as unexpired. Screenshot step allows errors. No screenshot artifact in the retrieved listing. This workflow does not run the full pytest suite. |
| [R1-06 tests, 42158614347](https://github.com/ueiider/BIMSpend/actions/runs/42158614347) | Successful Windows test workflow at eada297 after earlier failures 42157789150 and 42157987786. |
| [Capture tests, 42148155003](https://github.com/ueiider/BIMSpend/actions/runs/42148155003) | Successful Windows workflow at 59d5dd2, before R1-04 and later changes. |
| [Work integration, 42011629716](https://github.com/ueiider/BIMSpend/actions/runs/42011629716) | Successful Windows workflow at 47c8d35. |

Release gate: run full Windows QA on the exact selected candidate, prove legacy DB migration with preexisting reviewed entries, test worker/IPC through injected synthetic sources, then smoke the exact packaged artifact on a clean Windows VM. No new packaging workflow was triggered.
