# CRPM Governance Notes

CRPM is a local, Python-first research and operational-monitoring workbench. It is not a clinical decision-support system and does not replace local programme governance, data-protection review, or clinical judgement.

## Privacy Modes

CRPM records privacy posture as metadata so exports and manifests remain auditable:

- `public_demo` - synthetic or fully aliased data for screenshots, teaching, and public examples.
- `internal_operational` - local operational monitoring with privacy-safe summaries by default.
- `restricted_health_adjacent` - sensitive healthcare-adjacent logs where raw identifiers must not appear in UI, logs, manifests, or exports by default.

All modes keep `allows_raw_records=false` in the governance metadata. Raw case identifiers and patient-level health records should not be written to public reports or logs.

## Domain Templates

The first supported domain template is `ccr_screening`. It documents colorectal cancer screening assumptions such as the default production first-event gate `Invitation` and the non-clinical scope of outputs. The `generic` template is available for non-domain-specific process-mining experiments.

Domain templates are governance and interpretation metadata. They do not change metric definitions without explicit analytics code and tests.

## Release Responsibility

Before public release, run the release checks, inspect generated artifacts, and confirm that screenshots, manifests, logs, and bundled examples do not expose local paths, real case identifiers, credentials, or health records.

Recommended local checks before publishing a branch:

```bash
pytest -q
ruff check crpm tests
black --check crpm tests
crpm-release-check --quick
```

Generated artifacts should stay local and ignored: `outputs/`, `output/`, `build/`, `dist/`, `*.egg-info`, `.pytest_cache/`, `.ruff_cache/`, Streamlit logs, and browser/test caches. Keep `AGENTS.md` local-only because it may contain branch-specific working notes.

Branch promotion policy:

- Develop experimental dashboard and process-intelligence work on `_CRPM_v3`.
- Treat `main` as the stable public baseline; it now contains the v3 process-intelligence workbench capabilities.
- Use `_CRPM_v3` for future dashboard, BPMN-style workflow, reproducibility, governance, batch, manifest, data-quality, and UI refinements.
- Do not merge or push to `main` as part of routine v3 cleanup.
