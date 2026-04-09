# Changelog

All notable changes to CRPM are documented in this file.  
Format follows [Keep a Changelog](https://keepachangelog.com/).

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
