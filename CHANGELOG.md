# Changelog

All notable changes to CRPM are documented in this file.  
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased] — `_CRPM_v3`

### Added
- Process-intelligence dashboard posture for the v3 branch, with denser Overview, DFG, and Conformance Analytics surfaces.
- Run manifest generation with CRPM/PM4Py/Python versions, source metadata, filters, workflow policy, denominators, algorithm parameters, timings, and cache telemetry.
- Event-log quality reporting for required fields, duplicate events, timestamp ordering, timezone posture, semantic profiles, and preprocessing impact.
- Denominator registry so cases, events, activities, transitions, variants, paths, visible cases, and excluded cases are auditable.
- Headless batch CLI (`crpm-analyze`) and config schema for repeatable local runs.
- Release-check CLI (`crpm-release-check`) for version, preflight, test, format, build, and artifact checks.
- Synthetic screening data generator CLI (`crpm-generate-screening-demo`) for privacy-safe demos and tests.
- Governance metadata for privacy modes and domain templates, plus `docs/governance.md`.
- Reader-oriented project structure guide in `docs/project_structure.md`.
- Shared process-map payload structure for DFG and workflow renderers.
- Model-quality and PM4Py parameter profile reporting.
- Process-intelligence summaries for cohort lenses, time-series monitoring, resource posture, loop/rework metrics, and conformance root-cause counts.

### Changed
- Preserved `first_event_direct` as the production workflow default and documented it as the research contract.
- Improved Conformance Analytics with parent/child filters, visible reset actions, pinned metrics, and a graph-first cockpit layout.
- Improved DFG layout so the process map reads earlier and avoids the previous low/wide first viewport.
- Aligned README and governance branch notes with the current `main` and `_CRPM_v3` roles.
- Tightened input validation, safe error display, path redaction, and privacy-safe metadata handling.
- Bounded PM4Py compatibility to `pm4py>=2.7.22,<2.8` until newer compatibility windows are tested.

### Fixed
- Page navigation now resets the main viewport on page changes so users do not land mid-page after switching analytical surfaces.
- Time-series monitoring normalizes timezone-aware timestamps before period grouping to avoid noisy runtime warnings.
- Date filtering now uses the same earliest-event, timezone-safe semantics across the public conformance and pipeline APIs and rejects invalid ranges explicitly.
- PDF report generation now handles models with missing fitness or precision metrics without crashing during recommendation selection.
- Page caches remain bounded when backed by a standard dictionary, and the Streamlit entrypoint is covered by formatting and lint gates.

## [0.3.0] — 2026-03-16

### Added
- Native execution for all eight analytical pages (Overview, Discovery, Model Comparison, Operational Flow, DFG Visualizations, Variant Analysis, Conformance Analytics, Process Performance).
- 365-day follow-up horizon filter wired through state, runtime, and shell.
- Typed session state with Python dataclasses (`CRPMState`, `ShellConfig`, `AnalysisResults`, `AnalysisSnapshot`).
- Institutional branding (FMUP/UP logos, legal notice, professional header).
- `examples/` folder with idealized reference artefacts, `running-example.xes`, and synthetic CRC screening demo samples for XES and CSV onboarding.
- Public API exports in `crpm/__init__.py` with `__version__`.
- GitHub Actions CI workflow.
- CHANGELOG.md.

### Changed
- Bumped version to 0.3.0.
- Dependencies relaxed to minimum compatible versions (no longer pinned).
- Default log directory changed from `xes_logs/` to `examples/`.
- `pyproject.toml` updated with classifiers, keywords, URLs, and `crpm.pages` package.

### Removed
- Legacy workbench (`app_v2.py`) and all associated code paths.
- Dead files: `helpers.py`, `setup.cfg`, `nul`.
- Stale documentation: `IMPLEMENTATION_SUMMARY.md`, `USER_GUIDE_v2.md`.
- `xes_logs/` directory (contents moved to `examples/`).

## [0.1.0] — 2025-10-01

### Added
- Initial process mining workbench with Streamlit UI.
- Discovery, conformance, and screening pipeline modules.
- XES log import and basic DFG visualisation.
