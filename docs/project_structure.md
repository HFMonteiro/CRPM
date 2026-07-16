# CRPM Project Structure

This note explains how the repository is organised for readers who need to navigate, review, or extend CRPM. It is intentionally selective: the goal is to show the working architecture, not to duplicate every filename.

## Mental Model

CRPM has four practical layers:

1. **Shell and runtime** - Streamlit page routing, sidebar controls, session state, input validation, and orchestration.
2. **Analytics core** - PM4Py discovery, conformance, DFG, variants, denominators, log quality, and screening-domain helpers.
3. **Reader surfaces** - Streamlit pages, visualisations, dashboards, workflow boards, and BPMN-style views.
4. **Governance and reproducibility** - batch CLI, run manifests, privacy posture, release checks, tests, and public documentation.

## Repository Map

```text
CRPM/
|-- app.py
|   Streamlit entrypoint. Keeps launch behaviour thin and delegates to crpm.app_shell.
|
|-- crpm/
|   |-- app_shell.py
|   |   Global UI shell: branding, legal notice, sidebar controls, page routing,
|   |   page-scroll reset, and provenance placement.
|   |
|   |-- app_runtime.py
|   |   Runtime orchestration: resolves local/uploaded logs, applies the first-event
|   |   workflow gate, runs discovery/comparison/conformance, and builds outputs.
|   |
|   |-- app_state.py
|   |   Typed Streamlit session state, config/result containers, and page snapshots.
|   |
|   |-- pages/
|   |   Streamlit page modules. Each page should read from AnalysisSnapshot and avoid
|   |   changing core analytics semantics silently.
|   |
|   |-- discovery.py / conformance.py / dfg_utils.py / variants.py
|   |   PM4Py-facing process-mining functions and render helpers.
|   |
|   |-- process_map.py
|   |   Shared process-map payload contract used by DFG and conformance renderers.
|   |
|   |-- visualization.py / dashboard.py / pages/common.py
|   |   Reusable visual components, Plotly figures, SVG/HTML builders, cards, rails,
|   |   ranked tables, and privacy-safe labels.
|   |
|   |-- screening.py / synthetic_screening.py
|   |   Colorectal-screening domain helpers and synthetic demo generation.
|   |
|   |-- batch_cli.py / config_schema.py
|   |   Headless JSON/YAML analysis entrypoint and safe config parsing.
|   |
|   |-- governance.py / run_manifest.py / release_check.py / preflight.py
|   |   Privacy posture, audit metadata, release checks, and runtime dependency checks.
|   |
|   `-- styles.py
|       Central Streamlit CSS. Use sparingly and prefer scoped selectors for page
|       polish so visual fixes do not destabilise unrelated analytical pages.
|
|-- examples/
|   Synthetic/public logs and idealised model artefacts for demos, tests, and local
|   onboarding. These files should remain safe for public documentation.
|
|-- docs/
|   Public governance notes, the first-event research contract, screenshots, and
|   this structure guide.
|
|-- tests/
|   Behavioural and contract coverage for analytics, state, shell, pages, CLI,
|   governance, formatting, examples, release checks, and visual helpers.
|
`-- pyproject.toml
    Package metadata, dependencies, optional dev tooling, and CLI script entrypoints.
```

## Page Responsibilities

```text
Overview              first read, cohort posture, process canvas, evidence rails
Discovery             candidate discovery models and method profile
Model Comparison      small-candidate heatmap/table; scatter only when useful
Operational Flow      pathway movement, queue pressure, PRE/POST summaries
DFG Visualizations    directly-follows map and ranked transition evidence
Variant Analysis      dominant/rare trace structures and variant metrics
Conformance Analytics workflow explorer, board mode, BPMN-style view, inspector
Process Performance   bottlenecks, activity duration, and case duration detail
```

## Invariants To Preserve

- The production workflow remains `first_event_direct`; visual filters may hide or highlight structure but must not silently redefine the cohort.
- Raw case identifiers, local paths, uploaded filenames, and sensitive records should not appear in UI, logs, manifests, or public screenshots.
- DFG and Conformance workflow renderers should use the shared process-map payload contract where possible.
- Public examples and screenshots should be safe synthetic/demo material.
- `main` is protected as the stable public branch; `_CRPM_v3` is the current local experimentation branch for dashboard and visual polish.

## Documentation Pointers

- `README.md` - public overview, setup, feature list, sample data, and development commands.
- `docs/research_contract.md` - first-event direct workflow rule and dashboard contract.
- `docs/governance.md` - privacy modes, domain templates, release responsibility, and branch promotion policy.
- `CHANGELOG.md` - release-oriented summary of added/changed/fixed work.
