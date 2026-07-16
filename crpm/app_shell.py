"""Streamlit shell for the CRPM screening process-mining workbench."""

from __future__ import annotations

import base64
import html as _html
import logging
from datetime import date
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from crpm import __version__
from crpm.app_runtime import (
    AVAILABLE_ALGORITHMS,
    compute_analysis_signature,
    get_log_profile,
    list_safe_local_xes_files,
    preview_csv_dataframe,
    resolve_csv_log,
    resolve_xes_log,
    run_discovery_comparison_pipeline,
)
from crpm.app_state import (
    PREVIEW_PAGES,
    WORKFLOW_COHORT_FIRST_EVENT_DIRECT,
    AnalysisSnapshot,
    CRPMState,
    build_analysis_snapshot,
    get_crpm_state,
    initialize_shell_state,
)
from crpm.pages.common import render_quiet_note
from crpm.pages import PAGE_REGISTRY
from crpm.styles import apply_custom_styling

logger = logging.getLogger(__name__)

FMUP_LOGO_URL = "https://sigarra.up.pt/fmup/pt/imagens/LogotipoSI"
FMUP_HOME_URL = "https://sigarra.up.pt/fmup/pt/web_page.inicial"
UP_SYMBOL_URL = "https://sigarra.up.pt/up/pt/imagens/LogotipoSI"
UP_HOME_URL = "https://sigarra.up.pt/up/pt/web_page.inicial"
AUTHOR_WEBSITE = "https://hfmonteiro.com"
LEGAL_NOTICE = (
    "For research and operational monitoring support only. Not a substitute for clinical judgment or institutional decision-making."
)
CONFORMANCE_PAGE_FRAGMENT = st.fragment(PAGE_REGISTRY["Conformance Analytics"])
WORKSPACE_PAGES = {
    "Explore": ("Overview", "Discovery", "DFG Visualizations", "Variant Analysis"),
    "Conformance": ("Conformance Analytics",),
    "Performance": ("Operational Flow", "Process Performance"),
    "Models": ("Model Comparison",),
}


def _default_xes_index(options: list[str], selected_path: str | None) -> int:
    """Prefer the full screening demo for a fresh session without overriding a choice."""
    if selected_path in options:
        return options.index(selected_path)
    preferred_name = "screening_conformance_demo.xes"
    for index, option in enumerate(options):
        if Path(option).name == preferred_name:
            return index
    return 0


def _svg_data_uri(svg_markup: str) -> str:
    """Encode inline SVG markup as a data URI for stable logo rendering."""
    encoded = base64.b64encode(svg_markup.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


UP_BADGE_SRC = _svg_data_uri(
    """
    <svg xmlns="http://www.w3.org/2000/svg" width="196" height="64" viewBox="0 0 196 64" role="img" aria-label="Universidade do Porto">
      <rect width="196" height="64" rx="14" fill="#ffffff"/>
      <rect x="6" y="6" width="52" height="52" rx="10" fill="#111111"/>
      <text x="32" y="40" text-anchor="middle" fill="#ffffff" font-family="Georgia, 'Times New Roman', serif" font-size="28" font-weight="700">U.</text>
      <text x="71" y="27" fill="#141414" font-family="Arial, Helvetica, sans-serif" font-size="15" font-weight="800" letter-spacing="1.6">PORTO</text>
      <text x="71" y="46" fill="#55606d" font-family="Arial, Helvetica, sans-serif" font-size="8.5" font-weight="700" letter-spacing="1.1">UNIVERSIDADE DO PORTO</text>
    </svg>
    """.strip()
)

FMUP_BADGE_SRC = _svg_data_uri(
    """
    <svg xmlns="http://www.w3.org/2000/svg" width="232" height="64" viewBox="0 0 232 64" role="img" aria-label="Faculdade de Medicina da Universidade do Porto">
      <rect width="232" height="64" rx="14" fill="#ffffff"/>
      <rect x="6" y="6" width="52" height="52" rx="10" fill="#111111"/>
      <text x="32" y="40" text-anchor="middle" fill="#ffffff" font-family="Georgia, 'Times New Roman', serif" font-size="28" font-weight="700">U.</text>
      <text x="71" y="24" fill="#141414" font-family="Arial, Helvetica, sans-serif" font-size="21" font-weight="800" letter-spacing="1.2">FMUP</text>
      <rect x="71" y="32" width="88" height="10" rx="5" fill="#ffd54a"/>
      <text x="71" y="53" fill="#55606d" font-family="Arial, Helvetica, sans-serif" font-size="8.5" font-weight="700" letter-spacing="0.8">FACULDADE DE MEDICINA</text>
    </svg>
    """.strip()
)


def render_app() -> None:
    """Render the CRPM screening workbench."""
    _safe_set_page_config()
    initialize_shell_state(st.session_state)
    state = get_crpm_state(st.session_state)

    apply_custom_styling()
    _render_header_brand()
    page = _render_workspace_navigation()
    _reset_page_scroll_on_change(page)
    _render_analysis_controls(state)
    snapshot = build_analysis_snapshot(st.session_state)
    _render_sidebar_session_info(snapshot)
    _render_footer()

    _render_header(snapshot, page=page)
    page_renderer = CONFORMANCE_PAGE_FRAGMENT if page == "Conformance Analytics" else PAGE_REGISTRY[page]
    page_renderer(snapshot)


def _render_workspace_navigation() -> str:
    """Render a compact workspace selector with contextual sub-navigation."""
    current_page = str(st.session_state.get("crpm_preview_page", PREVIEW_PAGES[0]))
    current_workspace = next(
        (workspace for workspace, pages in WORKSPACE_PAGES.items() if current_page in pages),
        next(iter(WORKSPACE_PAGES)),
    )
    if st.session_state.get("crpm_workspace") not in WORKSPACE_PAGES:
        st.session_state["crpm_workspace"] = current_workspace

    st.sidebar.markdown(
        "<div class='crpm-sidebar-section-label'>Workspace</div>",
        unsafe_allow_html=True,
    )
    workspace = st.sidebar.radio(
        "Workspace",
        tuple(WORKSPACE_PAGES),
        key="crpm_workspace",
        label_visibility="collapsed",
    )
    pages = WORKSPACE_PAGES[workspace]
    page_key = f"crpm_workspace_view_{workspace.lower()}"
    if st.session_state.get(page_key) not in pages:
        st.session_state[page_key] = current_page if current_page in pages else pages[0]

    st.markdown(
        ("<div class='crpm-workspace-nav-marker' " f"data-workspace='{_html.escape(workspace)}'></div>"),
        unsafe_allow_html=True,
    )
    if len(pages) == 1:
        page = pages[0]
    else:
        page = st.radio(
            "View",
            pages,
            key=page_key,
            horizontal=True,
            label_visibility="collapsed",
        )
    st.session_state["crpm_preview_page"] = page
    return str(page)


def _reset_page_scroll_on_change(page: str) -> None:
    """Reset the main browser viewport when the selected analytical page changes."""
    previous_page = st.session_state.get("_crpm_last_rendered_page")
    st.session_state["_crpm_last_rendered_page"] = page
    if previous_page in {None, page}:
        return

    components.html(
        """
        <script>
        (() => {
          const scrollTop = (target) => {
            try {
              if (target && typeof target.scrollTo === "function") {
                target.scrollTo({ top: 0, left: 0, behavior: "auto" });
              } else if (target) {
                target.scrollTop = 0;
              }
            } catch (_) {}
          };
          const reset = () => {
            scrollTop(window.parent);
            try {
              const doc = window.parent.document;
              [
                doc.querySelector("[data-testid='stAppViewContainer']"),
                doc.querySelector(".main"),
                doc.querySelector("section.main"),
                doc.scrollingElement,
                doc.documentElement,
                doc.body,
              ].forEach(scrollTop);
            } catch (_) {}
          };
          reset();
          try {
            window.parent.requestAnimationFrame(() => window.parent.requestAnimationFrame(reset));
          } catch (_) {}
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def _safe_set_page_config() -> None:
    try:
        icon_path = Path(__file__).parent / "assets" / "crpm_logo.png"
        page_icon = str(icon_path) if icon_path.exists() else "🔬"
        st.set_page_config(
            page_title="CRPM - Screening Process Mining Workbench",
            page_icon=page_icon,
            layout="wide",
            initial_sidebar_state="expanded",
        )
    except Exception:
        pass


def _render_sidebar_session_info(snapshot: AnalysisSnapshot) -> None:
    """Show compact session info beneath the analysis controls."""
    preflight_warnings = st.session_state.get("crpm_preflight_warnings", [])
    source_meta = dict(snapshot.source_metadata or {})
    if snapshot.analysis_complete:
        if snapshot.input_name or snapshot.active_followup_label or snapshot.workflow_cohort_policy:
            context_bits = []
            if snapshot.input_name:
                context_bits.append(f"Input: {snapshot.input_name}")
            if snapshot.workflow_cohort_policy == WORKFLOW_COHORT_FIRST_EVENT_DIRECT:
                context_bits.append("Mode: Direct workflow")
            if snapshot.active_followup_label:
                context_bits.append(f"Follow-up: {snapshot.active_followup_label}")
            st.sidebar.caption(" · ".join(context_bits))
        if source_meta:
            validation = str(source_meta.get("validation_status", "validated"))
            validation_label = {
                "validated:xes": "Validated XES",
                "validated:csv": "Validated CSV",
                "validated": "Validated",
            }.get(validation.lower(), validation.replace("_", " ").replace(":", " ").strip().title())
            st.sidebar.caption(f"Source: {validation_label}")
        st.sidebar.caption(
            f"✓ {snapshot.model_count} model(s) discovered · {snapshot.case_count:,} cases · {snapshot.event_count:,} events"
        )
    else:
        st.sidebar.caption("Load a log and click **Run analysis** to start.")
    for warning in preflight_warnings:
        st.sidebar.warning(warning)


def _render_header(snapshot: AnalysisSnapshot, *, page: str) -> None:
    """Render the main content header with compact run context."""
    if page == "Conformance Analytics":
        if getattr(snapshot, "config_change_message", None):
            render_quiet_note(
                "Settings changed since the last successful run. "
                "Click Run analysis to rebuild the filtered log, conformance workspace, and charts."
            )
            if hasattr(st, "toast"):
                st.toast("Settings changed. Run analysis to refresh results.", icon="ℹ️")
        if getattr(snapshot, "filter_error_message", None):
            st.error(snapshot.filter_error_message)
        return

    _render_run_context_bar(snapshot, page=page)
    if getattr(snapshot, "config_change_message", None):
        render_quiet_note(
            "Settings changed since the last successful run. "
            "Click Run analysis to rebuild the filtered log, conformance workspace, and charts."
        )
        if hasattr(st, "toast"):
            st.toast("Settings changed. Run analysis to refresh results.", icon="ℹ️")
    if getattr(snapshot, "filter_error_message", None):
        st.error(snapshot.filter_error_message)


def _render_run_context_bar(snapshot: AnalysisSnapshot, *, page: str) -> None:
    """Render a low-height run context strip so page cockpits stay above the fold."""
    intro_copy = _shell_intro_copy(page)
    chips = []
    if getattr(snapshot, "input_name", None):
        chips.append(("Input", snapshot.input_name))
    if getattr(snapshot, "active_followup_label", None):
        chips.append(("Follow-up", snapshot.active_followup_label))
    if getattr(snapshot, "analysis_complete", False):
        chips.extend(
            [
                ("Cases", f"{int(getattr(snapshot, 'case_count', 0) or 0):,}"),
                ("Events", f"{int(getattr(snapshot, 'event_count', 0) or 0):,}"),
                ("Models", f"{int(getattr(snapshot, 'model_count', 0) or 0):,}"),
            ]
        )
    if not chips:
        chips.append(("Status", "Run analysis to populate the workbench"))

    chip_markup = "".join(
        "<span class='crpm-run-context__chip'>"
        f"<span>{_html.escape(str(label))}</span>"
        f"<strong>{_html.escape(str(value))}</strong>"
        "</span>"
        for label, value in chips
    )
    st.markdown(
        f"""
        <div class="crpm-run-context" data-qa="run-context-bar">
            <div class="crpm-run-context__copy">
                <span class="crpm-run-context__label">Current run</span>
                <span class="crpm-run-context__body">{_html.escape(intro_copy)}</span>
            </div>
            <div class="crpm-run-context__chips">{chip_markup}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _shell_intro_copy(page: str) -> str:
    return {
        "Overview": "Start with the current cohort and the next analytical surface worth opening.",
        "Discovery": "Use this page to inspect discovered model candidates before moving into formal comparison.",
        "Model Comparison": "Compare discovery candidates on fitness, precision, and balance without duplicating page-level explanation.",
        "Operational Flow": "Review throughput movement, queue pressure, and stage aging over the current filtered pathway.",
        "DFG Visualizations": "Read the directly-follows map first, then drop into ranked transitions only when exact values matter.",
        "Variant Analysis": "Inspect dominant trace concentration and only then widen into rare-path behavior.",
        "Process Performance": "Use the timing charts for pattern recognition and the ranked tables for exact durations.",
    }.get(page, "Continue with the selected analytical surface for the current filtered run.")


# ---------------------------------------------------------------------------
# Branding / footer / legal
# ---------------------------------------------------------------------------


def _render_header_brand() -> None:
    """Render persistent author and institutional links in the app header."""
    st.markdown(
        f"""
        <div class="crpm-header-badges" data-qa="global-brand-strip" aria-label="CRPM institutional links">
            <a class="crpm-author-badge" href="{AUTHOR_WEBSITE}" target="_blank" rel="noopener noreferrer" aria-label="hfmonteiro.com">
                <span>www.hfmonteiro.com</span>
            </a>
            <span class="crpm-build-badge" aria-label="CRPM build version">Build {__version__}</span>
            <a class="crpm-fmup-badge" href="{FMUP_HOME_URL}" target="_blank" rel="noopener noreferrer" aria-label="Faculdade de Medicina da Universidade do Porto">
                <img src="{FMUP_BADGE_SRC}" alt="FMUP symbol" />
            </a>
            <a class="crpm-up-badge" href="{UP_HOME_URL}" target="_blank" rel="noopener noreferrer" aria-label="Universidade do Porto">
                <img src="{UP_BADGE_SRC}" alt="U.Porto symbol" />
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="crpm-legal-bar">
            <strong>Legal notice:</strong>
            <span>{_html.escape(LEGAL_NOTICE)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_footer() -> None:
    """Render compact provenance in the sidebar to avoid interrupting analysis pages."""
    st.sidebar.markdown(
        f"""
        <div class="crpm-sidebar-provenance" data-crpm-footer="sidebar" aria-label="CRPM provenance">
            <span>PhD work · Hugo Monteiro</span>
            <a href="{AUTHOR_WEBSITE}" target="_blank" rel="noopener noreferrer">hfmonteiro.com</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_input_validation_error(source_type: str, exc: Exception) -> None:
    logger.warning("%s input rejected during validation: %s", source_type, exc.__class__.__name__)
    if source_type == "CSV":
        message = (
            "The CSV log could not be validated. Check required columns, blank IDs, "
            "timestamp parsing, and timezone consistency before retrying."
        )
    else:
        message = "The XES log could not be validated or loaded. Check the file structure and retry."
    st.sidebar.error(message)


def _render_analysis_controls(state: CRPMState) -> None:
    st.sidebar.markdown("### Analysis setup")
    config = state.config
    results = state.results
    st.sidebar.caption("Direct workflow mode · First-event gate")
    run_button_slot = st.sidebar.empty()
    controls_panel = st.sidebar.expander("Data & run", expanded=not results.analysis_complete)
    controls_panel.caption("Choose the event log and first-event gate. Advanced settings stay available on demand.")

    source_type = controls_panel.radio(
        "Input source",
        ["XES", "CSV"],
        index=0 if config.source_type == "XES" else 1,
        key="crpm_input_source",
    )
    config.source_type = source_type

    loaded_log = None

    if source_type == "XES":
        config.xes_logs_directory = controls_panel.text_input(
            "Local XES folder",
            value=config.xes_logs_directory,
            key="crpm_xes_logs_directory",
            help="Local paths are used only for loading; run metadata shown in the UI is redacted.",
        )
        xes_options = list_safe_local_xes_files(config.xes_logs_directory)
        uploaded_xes = controls_panel.file_uploader("Upload XES log", type=["xes"], key="crpm_xes_upload")

        if xes_options:
            default_index = _default_xes_index(xes_options, config.selected_log_path)
            config.selected_log_path = controls_panel.selectbox(
                "Choose XES log",
                xes_options,
                index=default_index,
                key="crpm_xes_file_choice",
                format_func=lambda value: Path(value).name,
            )
        elif uploaded_xes is None:
            controls_panel.caption("Place XES logs in the selected folder or upload one directly.")
            config.selected_log_path = None

        try:
            loaded_log = resolve_xes_log(
                state,
                selected_path=config.selected_log_path,
                uploaded_bytes=uploaded_xes.getvalue() if uploaded_xes is not None else None,
                uploaded_name=uploaded_xes.name if uploaded_xes is not None else None,
            )
        except Exception as exc:
            if config.selected_log_path or uploaded_xes is not None:
                _render_input_validation_error("XES", exc)
    else:
        uploaded_csv = controls_panel.file_uploader("Upload CSV log", type=["csv"], key="crpm_csv_upload")
        if uploaded_csv is None:
            controls_panel.caption("Upload a CSV file to continue.")
        else:
            try:
                preview_df = preview_csv_dataframe(state, uploaded_csv.getvalue())
                columns = list(preview_df.columns)
                if columns:
                    config.csv_case_col = controls_panel.selectbox(
                        "Case ID column",
                        columns,
                        index=columns.index(config.csv_case_col) if config.csv_case_col in columns else 0,
                        key="crpm_csv_case_col",
                    )
                    config.csv_activity_col = controls_panel.selectbox(
                        "Activity column",
                        columns,
                        index=columns.index(config.csv_activity_col) if config.csv_activity_col in columns else min(1, len(columns) - 1),
                        key="crpm_csv_activity_col",
                    )
                    config.csv_timestamp_col = controls_panel.selectbox(
                        "Timestamp column",
                        columns,
                        index=columns.index(config.csv_timestamp_col) if config.csv_timestamp_col in columns else min(2, len(columns) - 1),
                        key="crpm_csv_timestamp_col",
                    )
                    loaded_log, _ = resolve_csv_log(
                        state,
                        uploaded_bytes=uploaded_csv.getvalue(),
                        uploaded_name=uploaded_csv.name,
                        case_col=config.csv_case_col,
                        activity_col=config.csv_activity_col,
                        timestamp_col=config.csv_timestamp_col,
                    )
            except Exception as exc:
                _render_input_validation_error("CSV", exc)

    if loaded_log is None:
        run_button_slot.button(
            "Run analysis",
            type="primary",
            use_container_width=True,
            key="crpm_run_analysis_unavailable",
            disabled=True,
        )
        return

    if not results.analysis_complete:
        results.input_name = loaded_log.input_name
        results.log_signature = loaded_log.log_signature
        results.source_metadata = loaded_log.metadata()
        results.workflow_cohort_policy = config.workflow_cohort_policy

    log_profile = get_log_profile(state, loaded_log)
    log_stats = log_profile["stats"]
    start_options = ["All"] + list(log_profile["first_events"])
    if config.workflow_cohort_policy == WORKFLOW_COHORT_FIRST_EVENT_DIRECT and config.start_filter == "All" and len(start_options) > 1:
        config.start_filter = start_options[1]
    config.start_filter = controls_panel.selectbox(
        "First-event workflow gate",
        start_options,
        index=start_options.index(config.start_filter) if config.start_filter in start_options else 0,
        key="crpm_start_filter",
        help="Production discovery/conformance/DFG mode keeps cases whose first event matches this gate. Use All only outside the paper-aligned production workflow.",
    )
    show_advanced_setup = controls_panel.checkbox(
        "Advanced setup",
        value=False,
        key="crpm_show_advanced_setup",
        help="Show date, discovery, follow-up, and validation settings in this sidebar panel.",
    )
    if show_advanced_setup:
        controls_panel.markdown("---")
        config.apply_date_filter = controls_panel.checkbox(
            "Apply date filter",
            value=config.apply_date_filter,
            key="crpm_apply_date_filter",
            help="Filter the loaded log to a date-bounded cohort or event slice before discovery and conformance.",
        )

        if config.apply_date_filter:
            config.date_filter_mode = controls_panel.selectbox(
                "Date filter mode",
                options=["case", "event"],
                index=0 if config.date_filter_mode != "event" else 1,
                format_func=lambda value: "Case cohort (recommended)" if value == "case" else "Event clipping (advanced)",
                key="crpm_date_filter_mode",
                help="Case cohort keeps whole traces whose earliest timestamp falls inside the range. Event clipping removes events outside the range and is intended for advanced use only.",
            )
            default_start = log_stats["start"].date() if log_stats.get("start") else date.today()
            default_end = log_stats["end"].date() if log_stats.get("end") else default_start
            config.start_date = controls_panel.date_input(
                "Start date",
                value=config.start_date or default_start,
                key="crpm_filter_start_date",
            )
            config.end_date = controls_panel.date_input(
                "End date",
                value=config.end_date or default_end,
                key="crpm_filter_end_date",
            )
        else:
            config.date_filter_mode = "case"
            config.start_date = None
            config.end_date = None

        controls_panel.caption("Discovery algorithms")
        algorithm_labels = {
            "Heuristics (Classic)": "Heuristics classic",
            "Heuristics (PLUS)": "Heuristics plus",
            "Inductive (IM)": "Inductive IM",
            "Inductive (IMf)": "Inductive IMf",
            "Inductive (IMd)": "Inductive IMd",
            "Alpha (Classic)": "Alpha classic",
            "Alpha+": "Alpha+",
        }
        active_algorithms = set(config.selected_algorithms) or {"Heuristics (Classic)"}
        selected_algorithms = []
        for index, algorithm_name in enumerate(AVAILABLE_ALGORITHMS):
            is_last_active = len(active_algorithms) == 1 and algorithm_name in active_algorithms
            if controls_panel.checkbox(
                algorithm_labels.get(algorithm_name, algorithm_name),
                value=algorithm_name in active_algorithms,
                key=f"crpm_discovery_algorithm_{index}",
                disabled=is_last_active,
                help="At least one discovery algorithm must remain selected." if is_last_active else None,
            ):
                selected_algorithms.append(algorithm_name)
        config.selected_algorithms = selected_algorithms

        config.apply_followup_window = controls_panel.checkbox(
            "Apply follow-up horizon",
            value=config.apply_followup_window,
            key="crpm_apply_followup_window",
            help="Secondary sensitivity mode. Censors each case to a fixed horizon from the selected first-event gate.",
        )
        if config.apply_followup_window:
            config.followup_days = int(
                controls_panel.number_input(
                    "Follow-up horizon (days)",
                    min_value=30,
                    max_value=730,
                    value=config.followup_days,
                    step=5,
                    key="crpm_followup_days",
                )
            )

        config.enable_train_test = controls_panel.checkbox(
            "Enable train/test split (80/20)",
            value=config.enable_train_test,
            key="crpm_enable_train_test",
            help="Recommended when you want less optimistic conformance estimates. Small logs may produce unstable test results.",
        )
        if config.enable_train_test:
            config.random_seed = int(
                controls_panel.number_input(
                    "Random seed",
                    min_value=1,
                    max_value=9999,
                    value=config.random_seed,
                    key="crpm_random_seed",
                )
            )

    controls_panel.markdown("#### Log summary")
    controls_panel.caption(f"{log_stats['traces']:,} traces / {log_stats['events']:,} events")
    if log_stats["start"] and log_stats["end"]:
        controls_panel.caption(f"{log_stats['start']:%Y-%m-%d} to {log_stats['end']:%Y-%m-%d}")

    followup_days = config.followup_days if config.apply_followup_window else None

    current_signature = compute_analysis_signature(
        log_signature=loaded_log.log_signature,
        workflow_cohort_policy=config.workflow_cohort_policy,
        start_filter=config.start_filter,
        date_filter_mode=config.date_filter_mode,
        start_date=config.start_date,
        end_date=config.end_date,
        selected_algorithms=config.selected_algorithms,
        enable_train_test=config.enable_train_test,
        random_seed=config.random_seed,
        followup_days=followup_days,
    )
    if results.last_analysis_signature is not None and current_signature != results.last_analysis_signature and results.analysis_complete:
        results.reset(
            input_name=loaded_log.input_name,
            log_signature=loaded_log.log_signature,
            active_followup_label="Pending rerun",
            source_metadata=loaded_log.metadata(),
            workflow_cohort_policy=config.workflow_cohort_policy,
            config_change_message="Analysis settings changed. Click Run analysis to refresh the stabilized shell results.",
        )

    if run_button_slot.button("Run analysis", type="primary", use_container_width=True, key="crpm_run_analysis"):
        try:
            run_discovery_comparison_pipeline(
                state,
                loaded_log=loaded_log,
                start_filter=config.start_filter,
                date_filter_mode=config.date_filter_mode,
                start_date=config.start_date,
                end_date=config.end_date,
                selected_algorithms=config.selected_algorithms,
                enable_train_test=config.enable_train_test,
                random_seed=config.random_seed,
                followup_days=followup_days,
            )
        except Exception as exc:
            logger.warning("Analysis run failed: %s", exc.__class__.__name__)
            results.reset(
                input_name=loaded_log.input_name,
                log_signature=loaded_log.log_signature,
                active_followup_label="Run failed",
                source_metadata=loaded_log.metadata(),
                workflow_cohort_policy=config.workflow_cohort_policy,
                filter_error_message="The analysis could not be completed. Review the current settings and try again.",
            )
    if results.config_change_message:
        st.sidebar.warning(results.config_change_message)
    if results.filter_error_message:
        st.sidebar.error(results.filter_error_message)
