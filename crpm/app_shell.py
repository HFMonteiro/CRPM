"""Streamlit shell for the CRPM screening process-mining workbench."""

from __future__ import annotations

import html as _html
import logging
from datetime import date
from pathlib import Path

import streamlit as st

from crpm.app_runtime import (
    AVAILABLE_ALGORITHMS,
    compute_analysis_signature,
    compute_log_stats,
    first_event_names,
    preview_csv_dataframe,
    resolve_csv_log,
    resolve_xes_log,
    run_discovery_comparison_pipeline,
)
from crpm.app_state import PREVIEW_PAGES, AnalysisSnapshot, CRPMState, build_analysis_snapshot, get_crpm_state, initialize_shell_state
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
    "For research and operational monitoring support only. "
    "Not a substitute for clinical judgment or institutional decision-making."
)


def render_app() -> None:
    """Render the CRPM screening workbench."""
    _safe_set_page_config()
    initialize_shell_state(st.session_state)
    state = get_crpm_state(st.session_state)

    apply_custom_styling()
    _render_header_brand()
    _render_analysis_controls(state)
    snapshot = build_analysis_snapshot(st.session_state)
    _render_sidebar_session_info(snapshot)

    page = st.sidebar.radio(
        "Page",
        PREVIEW_PAGES,
        key="crpm_preview_page",
    )

    _render_header(snapshot)
    PAGE_REGISTRY[page](snapshot)
    _render_footer()


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
    if snapshot.analysis_complete:
        st.sidebar.caption(
            f"✓ {snapshot.model_count} model(s) discovered · {snapshot.case_count:,} cases · {snapshot.event_count:,} events"
        )
        if snapshot.stage_timings:
            with st.sidebar.expander("Latest stage timings", expanded=False):
                for stage_name, seconds in snapshot.stage_timings.items():
                    st.caption(f"{stage_name}: {seconds:.3f}s")
    else:
        st.sidebar.caption("Load a log and click **Run analysis** to start.")
    for warning in preflight_warnings:
        st.sidebar.warning(warning)


def _render_header(snapshot: AnalysisSnapshot) -> None:
    """Render the main content header with hero and summary metrics."""
    st.markdown(
        """
        <div class="crpm-shell-hero">
            <div class="crpm-shell-hero__eyebrow">CRPM &mdash; Colorectal Cancer Screening</div>
            <div class="crpm-shell-hero__title">Screening Program Process Mining Workbench</div>
            <div class="crpm-shell-hero__body">Load an event log, discover empirical process models, compare fitness and precision across algorithms, assess conformance against normative pathways, inspect bottlenecks and delays, review dominant variants, and visualise directly-follows graphs.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    meta_cols = st.columns(4)
    meta_cols[0].metric("Cases", f"{snapshot.case_count:,}")
    meta_cols[1].metric("Events", f"{snapshot.event_count:,}")
    meta_cols[2].metric("Discovered models", snapshot.model_count)
    meta_cols[3].metric("Comparison rows", len(snapshot.comparison_df))

    if snapshot.input_name:
        st.caption(f"Current input: {snapshot.input_name}")
    if snapshot.active_followup_label:
        st.caption(f"Follow-up window: {snapshot.active_followup_label}")
    if snapshot.config_change_message:
        render_quiet_note(
            "Settings changed since the last successful run. "
            "Click Run analysis to rebuild the filtered log, conformance workspace, and charts."
        )
        if hasattr(st, "toast"):
            st.toast("Settings changed. Run analysis to refresh results.", icon="ℹ️")
    if snapshot.filter_error_message:
        st.error(snapshot.filter_error_message)


# ---------------------------------------------------------------------------
# Branding / footer / legal
# ---------------------------------------------------------------------------

def _render_header_brand() -> None:
    """Render a persistent UP badge in the sticky header area."""
    st.markdown(
        f"""
        <div class="crpm-header-badges">
            <a class="crpm-author-badge" href="{AUTHOR_WEBSITE}" target="_blank" aria-label="hfmonteiro.com">
                <span>www.hfmonteiro.com</span>
            </a>
            <a class="crpm-fmup-badge" href="{FMUP_HOME_URL}" target="_blank" aria-label="Faculdade de Medicina da Universidade do Porto">
                <img src="{FMUP_LOGO_URL}" alt="FMUP logo" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';" />
                <span style="display:none;">FMUP</span>
            </a>
            <a class="crpm-up-badge" href="{UP_HOME_URL}" target="_blank" aria-label="Universidade do Porto">
                <img src="{UP_SYMBOL_URL}" alt="UP logo" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';" />
                <span style="display:none;">UP</span>
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
    """Render the institutional footer at the bottom of the page."""
    st.markdown(
        f"""
        <div class="crpm-footer">
            <div class="crpm-footer__row">
                <img class="crpm-footer__logo" src="{FMUP_LOGO_URL}" alt="FMUP logo" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-flex';" />
                <span class="crpm-footer__logo-fallback" style="display:none;">FMUP</span>
                <div class="crpm-footer__text">
                    Developed in the context of PhD work by Hugo Monteiro &middot;
                    <a href="{AUTHOR_WEBSITE}" target="_blank">hfmonteiro.com</a>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_analysis_controls(state: CRPMState) -> None:
    st.sidebar.markdown("### Analysis Setup")
    config = state.config
    results = state.results
    with st.sidebar.expander("How to use this sidebar", expanded=False):
        st.caption(
            "1. Load a log. 2. Choose filters and algorithms. 3. Run analysis. "
            "If you change settings after a successful run, the current results are invalidated until you rerun."
        )
        st.caption(
            "Use case-cohort date filtering for most screening analyses. Event clipping is an advanced mode that can change trace structure."
        )

    source_type = st.sidebar.radio(
        "Input source",
        ["XES", "CSV"],
        index=0 if config.source_type == "XES" else 1,
        key="crpm_input_source",
    )
    config.source_type = source_type

    loaded_log = None

    if source_type == "XES":
        config.xes_logs_directory = st.sidebar.text_input(
            "Folder containing .xes files",
            value=config.xes_logs_directory,
            key="crpm_xes_logs_directory",
        )
        logs_dir = Path(config.xes_logs_directory)
        xes_options = [str(path) for path in sorted(logs_dir.glob("*.xes"))] if logs_dir.exists() else []
        uploaded_xes = st.sidebar.file_uploader("Upload XES log", type=["xes"], key="crpm_xes_upload")

        if xes_options:
            default_index = xes_options.index(config.selected_log_path) if config.selected_log_path in xes_options else 0
            config.selected_log_path = st.sidebar.selectbox(
                "Choose XES log",
                xes_options,
                index=default_index,
                key="crpm_xes_file_choice",
            )
        elif uploaded_xes is None:
            st.sidebar.caption("Place XES logs in the selected folder or upload one directly.")
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
                st.sidebar.error(str(exc))
    else:
        uploaded_csv = st.sidebar.file_uploader("Upload CSV log", type=["csv"], key="crpm_csv_upload")
        if uploaded_csv is None:
            st.sidebar.caption("Upload a CSV file to continue.")
        else:
            try:
                preview_df = preview_csv_dataframe(state, uploaded_csv.getvalue())
                columns = list(preview_df.columns)
                if columns:
                    config.csv_case_col = st.sidebar.selectbox(
                        "Case ID column",
                        columns,
                        index=columns.index(config.csv_case_col) if config.csv_case_col in columns else 0,
                        key="crpm_csv_case_col",
                    )
                    config.csv_activity_col = st.sidebar.selectbox(
                        "Activity column",
                        columns,
                        index=columns.index(config.csv_activity_col) if config.csv_activity_col in columns else min(1, len(columns) - 1),
                        key="crpm_csv_activity_col",
                    )
                    config.csv_timestamp_col = st.sidebar.selectbox(
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
                st.sidebar.error(str(exc))

    if loaded_log is None:
        return

    if not results.analysis_complete:
        results.input_name = loaded_log.input_name
        results.log_signature = loaded_log.log_signature

    log_stats = compute_log_stats(loaded_log.log)
    start_options = ["All"] + first_event_names(loaded_log.log)
    config.start_filter = st.sidebar.selectbox(
        "Filter by first event",
        start_options,
        index=start_options.index(config.start_filter) if config.start_filter in start_options else 0,
        key="crpm_start_filter",
    )
    config.apply_date_filter = st.sidebar.checkbox(
        "Apply date filter",
        value=config.apply_date_filter,
        key="crpm_apply_date_filter",
        help="Filter the loaded log to a date-bounded cohort or event slice before discovery and conformance.",
    )

    if config.apply_date_filter:
        config.date_filter_mode = st.sidebar.selectbox(
            "Date filter mode",
            options=["case", "event"],
            index=0 if config.date_filter_mode != "event" else 1,
            format_func=lambda value: "Case cohort (recommended)" if value == "case" else "Event clipping (advanced)",
            key="crpm_date_filter_mode",
            help="Case cohort keeps whole traces whose earliest timestamp falls inside the range. Event clipping removes events outside the range and is intended for advanced use only.",
        )
        default_start = log_stats["start"].date() if log_stats.get("start") else date.today()
        default_end = log_stats["end"].date() if log_stats.get("end") else default_start
        config.start_date = st.sidebar.date_input(
            "Start date",
            value=config.start_date or default_start,
            key="crpm_filter_start_date",
        )
        config.end_date = st.sidebar.date_input(
            "End date",
            value=config.end_date or default_end,
            key="crpm_filter_end_date",
        )
    else:
        config.date_filter_mode = "case"
        config.start_date = None
        config.end_date = None

    selected_algorithms = st.sidebar.multiselect(
        "Discovery algorithms",
        options=list(AVAILABLE_ALGORITHMS.keys()),
        default=config.selected_algorithms,
        key="crpm_selected_algorithms",
        help="Select the process discovery algorithms to compare. Fewer algorithms reduce runtime on large logs.",
    )
    config.selected_algorithms = selected_algorithms or ["Heuristics (Classic)"]

    config.apply_followup_window = st.sidebar.checkbox(
        "Apply follow-up horizon",
        value=config.apply_followup_window,
        key="crpm_apply_followup_window",
        help="Censor each case to a fixed observation window from its anchor event. Useful for comparability studies.",
    )
    if config.apply_followup_window:
        config.followup_days = int(
            st.sidebar.number_input(
                "Follow-up horizon (days)",
                min_value=30,
                max_value=730,
                value=config.followup_days,
                step=5,
                key="crpm_followup_days",
            )
        )

    config.enable_train_test = st.sidebar.checkbox(
        "Enable train/test split (80/20)",
        value=config.enable_train_test,
        key="crpm_enable_train_test",
        help="Recommended when you want less optimistic conformance estimates. Small logs may produce unstable test results.",
    )
    if config.enable_train_test:
        config.random_seed = int(
            st.sidebar.number_input(
                "Random seed",
                min_value=1,
                max_value=9999,
                value=config.random_seed,
                key="crpm_random_seed",
            )
        )

    st.sidebar.markdown("### Log Statistics")
    st.sidebar.caption(f"Traces: {log_stats['traces']:,}")
    st.sidebar.caption(f"Events: {log_stats['events']:,}")
    if log_stats["start"] and log_stats["end"]:
        st.sidebar.caption(f"Period: {log_stats['start']:%Y-%m-%d} -> {log_stats['end']:%Y-%m-%d}")

    followup_days = config.followup_days if config.apply_followup_window else None

    current_signature = compute_analysis_signature(
        log_signature=loaded_log.log_signature,
        start_filter=config.start_filter,
        date_filter_mode=config.date_filter_mode,
        start_date=config.start_date,
        end_date=config.end_date,
        selected_algorithms=config.selected_algorithms,
        enable_train_test=config.enable_train_test,
        random_seed=config.random_seed,
        followup_days=followup_days,
    )
    if (
        results.last_analysis_signature is not None
        and current_signature != results.last_analysis_signature
        and results.analysis_complete
    ):
        results.reset(
            input_name=loaded_log.input_name,
            log_signature=loaded_log.log_signature,
            active_followup_label="Pending rerun",
            config_change_message="Analysis settings changed. Click Run analysis to refresh the stabilized shell results.",
        )

    if st.sidebar.button("Run analysis", type="primary", use_container_width=True, key="crpm_run_analysis"):
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
        except Exception:
            logger.exception("Analysis run failed")
            results.reset(
                input_name=loaded_log.input_name,
                log_signature=loaded_log.log_signature,
                active_followup_label="Run failed",
                filter_error_message="The analysis could not be completed. Review the current settings and try again.",
            )
    if results.config_change_message:
        st.sidebar.warning(results.config_change_message)
    if results.filter_error_message:
        st.sidebar.error(results.filter_error_message)
