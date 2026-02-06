# Top 10 Improvement Suggestions for CRPM

The following improvements are ranked by impact and feasibility. Each includes
the rationale, affected files, and a concrete action plan.

---

## 1. Add a Test Suite

**Priority:** High

The repository has no automated tests despite having `pytest` in
`requirements.lock`. Adding tests for the `crpm` package would catch
regressions early and make future refactoring safer.

**Affected files:** new `tests/` directory.

**Action plan:**
- Create `tests/conftest.py` with a small fixture event log (the bundled
  `xes_logs/running-example.xes` can be reused).
- Add unit tests for every public function in `crpm/conformance.py`,
  `crpm/pipeline.py`, `crpm/analytics.py`, `crpm/variants.py`, and
  `crpm/discovery.py`.
- Add a CI workflow (`.github/workflows/test.yml`) that runs `pytest` on push.

---

## 2. Remove Duplicated Code Between Modules

**Priority:** High

Several functions are duplicated across files:

| Function / Logic | Locations |
|---|---|
| `filter_date_range` | `crpm/conformance.py` **and** `crpm/pipeline.py` (identical) |
| `load_log` / `load_csv` | `crpm/conformance.py` **and** `helpers.py` |
| `first_event_names` | `app.py` **and** `helpers.py` |
| `filter_start_event` / `filter_by_first_event` | `crpm/conformance.py` **and** `helpers.py` |
| `run_heuristics_miner` / `discover_heuristics_net` | `crpm/conformance.py` **and** `crpm/pipeline.py` (near-identical) |

**Action plan:**
- Keep one canonical version of each function in the appropriate `crpm`
  module.
- Update all callers (`app.py`, `app_v2.py`, `pipeline_app.py`, `helpers.py`)
  to import from the single source.
- Consider deprecating `helpers.py` entirely since its functions already exist
  in `crpm/conformance.py`.

---

## 3. Add Proper Error Handling and Logging

**Priority:** High

The codebase relies on bare `except Exception` blocks that silently swallow
errors (e.g., `crpm/analytics.py:344`, `crpm/variants.py:62`,
`crpm/discovery.py:102`). This makes debugging difficult.

**Action plan:**
- Replace bare `except Exception` with specific exception types where
  possible.
- Use Python's `logging` module instead of `print()` (see
  `crpm/discovery.py:377`) or silent passes.
- At minimum, log the exception message so failures are traceable.
- In the Streamlit apps, surface errors via `st.warning()` rather than
  hiding them.

---

## 4. Use SHA-256 Instead of SHA-1 for File Hashing

**Priority:** High (security)

`app.py:82` uses `hashlib.sha1(raw).hexdigest()` to hash uploaded file
content. SHA-1 is considered cryptographically weak. While this is not used
for security purposes here, switching to SHA-256 is a zero-cost improvement
that follows current best practices.

**Action plan:**
- In `app.py` function `make_uploaded_signature`, replace
  `hashlib.sha1(raw).hexdigest()` with `hashlib.sha256(raw).hexdigest()`.
- Apply the same change in `app_v2.py` if it contains the same pattern.

---

## 5. Pin and Audit Dependencies

**Priority:** Medium

`requirements.txt` pins exact versions which is good, but:
- `fpdf` is imported in `crpm/report_generator.py` but is not listed in
  `requirements.txt`.
- There is no dependabot or automated vulnerability scanning configured.
- The lock file and the requirements file can drift apart silently.

**Action plan:**
- Add `fpdf2` (the maintained fork) to `requirements.txt`.
- Add a `.github/dependabot.yml` to get automated dependency update PRs.
- Document the update workflow in the README (already partially done).

---

## 6. Improve the `__init__.py` Exports

**Priority:** Medium

`crpm/__init__.py` only exports `conformance` and `pipeline`, but the
package now contains seven modules (`analytics`, `discovery`, `dfg_utils`,
`interpretations`, `report_generator`, `styles`, `variants`,
`visualization`). Users who `import crpm` do not get access to the newer
modules.

**Action plan:**
- Update `crpm/__init__.py` to import and re-export all public sub-modules.
- Optionally expose the most-used functions at the package level for
  convenience (e.g., `from crpm import load_log, discover_heuristics_net`).

---

## 7. Add Type Checking and Linting to CI

**Priority:** Medium

The lock file includes `mypy`, `pyright`, and `ruff`, but there is no CI
step that runs them. `setup.cfg` configures only `flake8` with a single
setting.

**Action plan:**
- Add a `pyproject.toml` (or extend `setup.cfg`) with `ruff` and `mypy`
  configuration.
- Add a CI job that runs `ruff check .` and `mypy crpm/` on every PR.
- Fix the handful of type errors that surface (mostly `Any` returns from
  PM4Py).

---

## 8. Clean Up Stale / Backup Files

**Priority:** Medium

The repository root contains files that add noise and may confuse
contributors:

| File | Issue |
|---|---|
| `app_v1_backup.py` | Backup that duplicates `app.py`; belongs in git history |
| `key scripts/` | Stand-alone scripts without documentation or tests |
| `IDEALIZED DATASET/` | Spaces in directory name; no documentation |
| `CONFORMANCE_fullcode_may_2025.ipynb` | Large notebook that was refactored into `crpm/pipeline.py` |

**Action plan:**
- Remove `app_v1_backup.py` (retrievable from git history).
- Rename `key scripts` → `scripts` and `IDEALIZED DATASET` →
  `idealized_dataset` (avoid spaces in paths).
- Add a short `README.md` inside each directory explaining its purpose.
- Consider moving the notebook to a `notebooks/` directory.

---

## 9. Make the Streamlit Apps Configurable via Environment Variables

**Priority:** Low

Hard-coded values such as `MAX_UPLOAD_BYTES = 200 * 1024 * 1024` (app.py:178),
the default log folder `"./xes_logs"`, and output directory settings are
scattered across the code. Making these configurable via environment
variables (or a `.env` file) improves deployment flexibility.

**Action plan:**
- Read `CRPM_MAX_UPLOAD_MB`, `CRPM_LOG_DIR`, and `CRPM_OUTPUT_DIR` from the
  environment, falling back to sensible defaults.
- Use `python-dotenv` or Streamlit's built-in `secrets.toml` for local
  development overrides.
- Document available variables in the README.

---

## 10. Add a `py.typed` Marker and Improve Docstrings

**Priority:** Low

Several functions lack docstrings (e.g., `filter_date_range` in both
`crpm/conformance.py` and `crpm/pipeline.py`) and some docstrings mix
Portuguese comments with English documentation. Adding a `py.typed` marker
file lets type checkers treat the package as typed.

**Action plan:**
- Create `crpm/py.typed` (empty file).
- Audit every public function and ensure it has an English docstring following
  the existing Google-style convention used elsewhere in the codebase.
- Translate remaining Portuguese comments (`# Se não há limite…`,
  `# Constrói os datetimes limite`, etc.) to English for consistency.
