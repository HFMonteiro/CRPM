"""CRPM - Comprehensive Process Mining Application with Multi-Algorithm Analysis.

This Streamlit app provides:
- Multi-algorithm process discovery (Heuristics, Inductive, Alpha)
- Model comparison and sensitivity analysis
- Performance analytics and bottleneck detection
- Variant analysis with per-variant conformance
- DFG visualizations
"""

import base64
import hashlib
import io
import os
import tempfile
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Ensure PM4Py dependencies are available
try:
    from pm4py.visualization.heuristics_net import visualizer as hn_vis
    from pm4py.visualization.petri_net import visualizer as pn_vis
    from pm4py.visualization.dfg import visualizer as dfg_vis
    from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
except Exception as exc:
    st.error(
        f"Failed to import PM4Py modules: {exc}\n"
        "Make sure you've run: pip install pm4py[all] lxml graphviz"
    )
    st.stop()

from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.importer.importer import apply as pnml_importer

# Import CRPM modules
from crpm.conformance import (
    load_log,
    filter_start_event,
    filter_date_range,
    compute_alignments,
    compute_token_replay,
    summarize_metrics,
    load_petri_net_from_pnml,
)
from crpm.pipeline import csv_to_event_log, split_log_random
from crpm.report_generator import generate_pdf_report
from crpm.discovery import (
    discover_all_algorithms,
    AVAILABLE_ALGORITHMS,
    compute_model_complexity,
    DiscoveryResult
)
from crpm.styles import apply_custom_styling
from crpm.interpretations import (
    assess_fitness,
    assess_precision,
    assess_balanced_quality,
    get_model_quadrant,
    assess_process_variance,
    assess_bottleneck_severity,
    assess_case_duration_outliers,
    assess_variant_coverage,
    assess_variant_count,
    get_quality_badge_html,
)
from crpm.analytics import (
    compute_activity_statistics,
    compute_transition_statistics,
    detect_bottlenecks,
    compute_case_durations,
    compute_case_statistics,
    extract_model_transitions,
)
from crpm.variants import (
    get_variant_statistics,
    compute_variant_conformance,
    compute_variant_coverage,
)
from crpm.visualization import (
    create_bottleneck_chart,
    create_activity_duration_chart,
    create_case_duration_histogram,
    create_variant_frequency_chart,
    create_variant_coverage_chart,
    create_model_comparison_radar,
    create_model_comparison_heatmap,
    create_fitness_precision_scatter,
)
from crpm.dfg_utils import (
    discover_dfg_frequency,
    discover_dfg_performance,
    filter_dfg_by_frequency,
    render_dfg_to_png,
    get_dfg_statistics,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
ENV_OUTPUT_DIR = Path(os.environ.get("CRPM_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

# UI Configuration
DATAFRAME_HEIGHT = 400  # Standard height for dataframes in pixels

st.set_page_config(
    page_title="CRPM - Process Mining Workbench",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom CSS styling
apply_custom_styling()

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------

def init_session_caches() -> None:
    """Initialize all session state caches."""
    for key in (
        "log_cache",
        "dataframe_cache",
        "filtered_cache",
        "model_cache",
        "discovery_results_cache",
        "conformance_cache",
        "performance_cache",
        "variant_cache",
        "dfg_cache",
    ):
        st.session_state.setdefault(key, {})

    # Train/test split state
    if "train_log" not in st.session_state:
        st.session_state["train_log"] = None
    if "test_log" not in st.session_state:
        st.session_state["test_log"] = None
    if "split_info" not in st.session_state:
        st.session_state["split_info"] = {}
    if "reference_model" not in st.session_state:
        st.session_state["reference_model"] = None
    if "analysis_complete" not in st.session_state:
        st.session_state["analysis_complete"] = False


# ---------------------------------------------------------------------------
# Cache Helper Functions
# ---------------------------------------------------------------------------

def make_file_signature(path: Path) -> str:
    """Build a stable signature for an on-disk file."""
    try:
        stat = path.stat()
    except OSError:
        return str(path.resolve())
    return f"{path.resolve()}::{stat.st_size}::{stat.st_mtime_ns}"


def make_uploaded_signature(raw: bytes, label: str) -> str:
    """Hash uploaded file content for caching."""
    digest = hashlib.sha1(raw).hexdigest()
    return f"{label}::{digest}"


def compute_filter_key(
    log_signature: str,
    first_event: Optional[str],
    start_dt: Optional[date],
    end_dt: Optional[date],
) -> str:
    """Key representing the filtered subset of a log."""
    def _fmt(value: Optional[date]) -> str:
        if value is None:
            return "-"
        if isinstance(value, datetime):
            return value.isoformat()
        return datetime.combine(value, datetime.min.time()).isoformat()

    return "::".join([
        log_signature,
        first_event or "*",
        _fmt(start_dt),
        _fmt(end_dt),
    ])


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def render_petri_png(net, im, fm, rankdir: str = "LR") -> bytes:
    """Render Petri net to PNG bytes.

    Args:
        net: Petri net
        im: Initial marking
        fm: Final marking
        rankdir: Graph direction - "LR" (left-right, default) or "TB" (top-bottom)

    Returns:
        PNG bytes
    """
    parameters = {
        "format": "png",
        "rankdir": rankdir
    }
    gviz = pn_vis.apply(net, im, fm, parameters=parameters)
    try:
        return gviz.pipe(format="png")
    except Exception:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp_path = Path(tmp.name)
        try:
            pn_vis.save(gviz, str(tmp_path))
            return tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)


def render_heuristics_png(heu_net) -> bytes:
    """Render heuristics net to PNG bytes."""
    gviz = hn_vis.apply(heu_net)
    try:
        return gviz.pipe(format="png")
    except Exception:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp_path = Path(tmp.name)
        try:
            hn_vis.save(gviz, str(tmp_path))
            return tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)


def first_event_names(log: EventLog) -> List[str]:
    """Return sorted set of first event names in the log."""
    return sorted({trace[0]["concept:name"] for trace in log if trace})


def compute_log_stats(log: EventLog) -> Dict[str, Optional[object]]:
    """Compute basic statistics for an event log."""
    traces = len(log)
    events = 0
    timestamps = []
    for trace in log:
        events += len(trace)
        for event in trace:
            ts = event.get("time:timestamp")
            if isinstance(ts, datetime):
                timestamps.append(ts)
    start_ts = min(timestamps) if timestamps else None
    end_ts = max(timestamps) if timestamps else None
    return {
        "traces": traces,
        "events": events,
        "start": start_ts,
        "end": end_ts,
    }


# ---------------------------------------------------------------------------
# Conformance Computation
# ---------------------------------------------------------------------------

def compute_full_conformance(log: EventLog, net, im, fm, model_name: str) -> Dict[str, Any]:
    """Compute all conformance metrics for a model."""
    try:
        # Alignments
        align_res = compute_alignments(log, net, im, fm)

        # Token replay
        token_res = compute_token_replay(log, net, im, fm)

        # Precision
        try:
            from pm4py.algo.evaluation.precision import algorithm as precision_evaluator
            precision = float(precision_evaluator.apply(log, net, im, fm))
        except Exception:
            precision = None

        # Summarize
        summary = summarize_metrics(align_res, token_res)

        # Add precision
        if precision is not None:
            summary["precision"] = {"value": precision}

        return {
            "model_name": model_name,
            "alignments": align_res,
            "token": token_res,
            "precision": precision,
            "summary": summary
        }
    except Exception as e:
        st.error(f"Error computing conformance for {model_name}: {e}")
        return {}


# ===========================================================================
# SIDEBAR: Data Loading and Filtering
# ===========================================================================

init_session_caches()

st.sidebar.title("CRPM - Process Mining Workbench")
st.sidebar.markdown("---")

try:
    source_type = st.sidebar.radio("Input source", ["XES", "CSV"], horizontal=True)

    output_dir_str = st.sidebar.text_input("Output directory", str(ENV_OUTPUT_DIR))
    OUTPUT_DIR = Path(output_dir_str)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB

    log: EventLog
    log_signature: str
    input_name: str

    # =======================================================================
    # XES or CSV Input
    # =======================================================================

    if source_type == "XES":
        default_logs_path = "./xes_logs"
        logs_path_str = st.sidebar.text_input(
            "Folder containing .xes files",
            default_logs_path,
        )
        logs_dir = Path(logs_path_str)
        if not logs_dir.exists():
            st.sidebar.error(f"Directory not found: {logs_dir.resolve()}")
            st.stop()

        xes_files = sorted(logs_dir.glob("*.xes"))
        uploaded_file = st.sidebar.file_uploader("Upload XES log", type="xes")
        uploaded_path = None
        uploaded_signature = None

        if uploaded_file is not None:
            uploaded_bytes = uploaded_file.getvalue()
            if len(uploaded_bytes) > MAX_UPLOAD_BYTES:
                st.sidebar.error(
                    f"Upload too large ({len(uploaded_bytes)/(1024*1024):.1f} MB). "
                    f"Max allowed: {MAX_UPLOAD_BYTES/(1024*1024):.0f} MB."
                )
                st.stop()
            uploaded_signature = make_uploaded_signature(uploaded_bytes, "xes_upload")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xes") as tmp:
                tmp.write(uploaded_bytes)
                uploaded_path = Path(tmp.name)
            xes_files = [uploaded_path] + xes_files

        if not xes_files:
            st.sidebar.info("Please upload a XES log to continue.")
            st.stop()

        def _fmt(path_obj: Path) -> str:
            if uploaded_path is not None and path_obj == uploaded_path and uploaded_file is not None:
                return f"{uploaded_file.name} (uploaded)"
            return path_obj.name

        file_choice = st.sidebar.selectbox("Choose XES log", xes_files, format_func=_fmt)
        file_signature = make_file_signature(file_choice)
        if uploaded_path is not None and file_choice == uploaded_path and uploaded_signature:
            file_signature = uploaded_signature

        log_cache: Dict[str, EventLog] = st.session_state["log_cache"]
        if file_signature in log_cache:
            log = log_cache[file_signature]
        else:
            with st.spinner("Loading XES log..."):
                log = load_log(file_choice)
            log_cache[file_signature] = log

        log_signature = f"xes::{file_signature}"
        input_name = file_choice.name

    else:  # CSV
        csv_file = st.sidebar.file_uploader("Upload CSV log", type=["csv"])
        if csv_file is None:
            st.sidebar.info("Upload a CSV file to continue.")
            st.stop()

        csv_bytes = csv_file.getvalue()
        if len(csv_bytes) > MAX_UPLOAD_BYTES:
            st.sidebar.error(
                f"CSV upload too large ({len(csv_bytes)/(1024*1024):.1f} MB). "
                f"Max allowed: {MAX_UPLOAD_BYTES/(1024*1024):.0f} MB."
            )
            st.stop()

        csv_signature = make_uploaded_signature(csv_bytes, "csv")
        dataframe_cache: Dict[str, pd.DataFrame] = st.session_state["dataframe_cache"]
        if csv_signature in dataframe_cache:
            df = dataframe_cache[csv_signature].copy()
        else:
            df = pd.read_csv(io.BytesIO(csv_bytes))
            dataframe_cache[csv_signature] = df.copy()

        st.sidebar.markdown("**CSV Column Mapping:**")
        cols = list(df.columns)
        case_col = st.sidebar.selectbox("Case ID column", cols, index=0 if cols else None)
        activity_col = st.sidebar.selectbox("Activity column", cols, index=1 if len(cols) > 1 else 0)
        timestamp_col = st.sidebar.selectbox("Timestamp column", cols, index=2 if len(cols) > 2 else 0)

        csv_log_signature = f"{csv_signature}::{case_col}:{activity_col}:{timestamp_col}"
        log_cache = st.session_state["log_cache"]
        if csv_log_signature in log_cache:
            log = log_cache[csv_log_signature]
        else:
            with st.spinner("Converting CSV to event log..."):
                log = csv_to_event_log(df, case_col, activity_col, timestamp_col)
            log_cache[csv_log_signature] = log

        log_signature = f"csv::{csv_log_signature}"
        input_name = getattr(csv_file, "name", "uploaded.csv")

    # =======================================================================
    # Filters
    # =======================================================================

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Filters:**")

    start_events = first_event_names(log)
    start_filter = st.sidebar.selectbox(
        "Filter by first event",
        ["All"] + start_events,
    )

    apply_date_filter = st.sidebar.checkbox("Apply date filter")
    if apply_date_filter:
        start_date = st.sidebar.date_input("Start date")
        end_date = st.sidebar.date_input("End date")
    else:
        start_date = end_date = None

    # =======================================================================
    # Train/Test Split Configuration
    # =======================================================================

    st.sidebar.markdown("---")
    enable_train_test = st.sidebar.checkbox(
        "✅ Enable Train/Test Split (80/20)",
        value=False,
        help="Split the log randomly into training (80%) and test (20%) sets. Models will be discovered on training data and evaluated on test data for realistic conformance metrics."
    )

    random_seed = 42
    if enable_train_test:
        random_seed = st.sidebar.number_input(
            "Random Seed",
            min_value=1,
            max_value=9999,
            value=42,
            help="Set random seed for reproducible splits"
        )

    # Optional: Load reference model
    st.sidebar.markdown("**Load Reference Model (Optional):**")
    reference_pnml = st.sidebar.file_uploader(
        "Upload PNML file",
        type=["pnml"],
        help="Upload an idealized Petri net model to compare against discovered models"
    )

    # Handle reference model upload
    if reference_pnml is not None:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pnml") as tmp:
                tmp.write(reference_pnml.getvalue())
                ref_pnml_path = Path(tmp.name)

            ref_net, ref_im, ref_fm = load_petri_net_from_pnml(ref_pnml_path)
            st.session_state["reference_model"] = {
                "name": reference_pnml.name,
                "net": ref_net,
                "im": ref_im,
                "fm": ref_fm
            }
            st.sidebar.success(f"✅ Loaded: {reference_pnml.name}")

            # Clean up temp file
            try:
                ref_pnml_path.unlink()
            except:
                pass
        except Exception as e:
            st.sidebar.error(f"Failed to load PNML: {e}")
            st.session_state["reference_model"] = None
    elif st.session_state.get("reference_model") is not None and reference_pnml is None:
        # Clear reference model if file uploader is cleared
        st.session_state["reference_model"] = None

    # =======================================================================
    # Log Statistics
    # =======================================================================

    log_stats = compute_log_stats(log)
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Log Statistics:**")
    st.sidebar.caption(f"Traces: {log_stats['traces']:,}")
    st.sidebar.caption(f"Events: {log_stats['events']:,}")
    if log_stats["start"] and log_stats["end"]:
        st.sidebar.caption(f"Period: {log_stats['start']:%Y-%m-%d} → {log_stats['end']:%Y-%m-%d}")

    # =======================================================================
    # Algorithm Selection
    # =======================================================================

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Discovery Algorithms:**")

    # Group algorithms by type
    heuristics_algos = [k for k in AVAILABLE_ALGORITHMS.keys() if "Heuristics" in k]
    inductive_algos = [k for k in AVAILABLE_ALGORITHMS.keys() if "Inductive" in k]

    with st.sidebar.expander("Select Algorithms", expanded=True):
        select_all = st.checkbox("Select All", value=False)

        selected_algorithms = []

        if select_all:
            selected_algorithms = list(AVAILABLE_ALGORITHMS.keys())
        else:
            st.caption("**Heuristics Miner:**")
            for algo in heuristics_algos:
                if st.checkbox(algo, value=(algo == "Heuristics (Classic)"), key=f"algo_{algo}"):
                    selected_algorithms.append(algo)

            st.caption("**Inductive Miner:**")
            for algo in inductive_algos:
                if st.checkbox(algo, value=(algo == "Inductive (IMf)"), key=f"algo_{algo}"):
                    selected_algorithms.append(algo)

    if not selected_algorithms:
        st.sidebar.warning("Please select at least one algorithm.")
        selected_algorithms = ["Heuristics (Classic)"]  # Default

    # =======================================================================
    # Run Analysis Button
    # =======================================================================

    st.sidebar.markdown("---")
    run_analysis = st.sidebar.button("🚀 Run Analysis", type="primary", use_container_width=True)

    # =======================================================================
    # Export Report Section
    # =======================================================================

    st.sidebar.markdown("---")
    st.sidebar.markdown("**📄 Export Report:**")

    export_format = st.sidebar.radio(
        "Format:",
        ["CSV (Tables Only)", "JSON (All Data)", "PDF (Full Report)"],
        horizontal=False,
        label_visibility="collapsed"
    )

    # Check if analysis is complete
    analysis_complete = st.session_state.get("analysis_complete", False)

    if st.sidebar.button(
        "📥 Generate Report",
        type="secondary",
        use_container_width=True,
        disabled=not analysis_complete,
        help="Run analysis first to enable report generation"
    ):
        if export_format == "CSV (Tables Only)":
            st.sidebar.info("CSV export: Use download buttons in each tab for specific data.")
        elif export_format == "JSON (All Data)":
            st.sidebar.info("JSON export: Feature coming soon!")
        else:  # PDF Full Report
            with st.spinner("Generating PDF report..."):
                try:
                    # Collect all analysis data from session state
                    discovery_results = st.session_state.get("discovery_results", [])
                    comparison_df = st.session_state.get("comparison_df", pd.DataFrame())
                    case_stats = st.session_state.get("case_stats", {})
                    activity_stats = st.session_state.get("activity_stats", pd.DataFrame())
                    bottleneck_df = st.session_state.get("bottleneck_df", pd.DataFrame())
                    variant_stats = st.session_state.get("variant_stats", pd.DataFrame())

                    # Prepare log summary
                    filtered_log = st.session_state.get("current_filtered_log", [])
                    log_summary = {
                        "num_cases": len(filtered_log),
                        "num_events": sum(len(trace) for trace in filtered_log),
                        "num_activities": len(set(
                            event.get("concept:name", "Unknown")
                            for trace in filtered_log
                            for event in trace
                        )),
                        "num_variants": len(variant_stats) if not variant_stats.empty else 0,
                    }

                    # Prepare filters applied
                    filters_applied = {
                        "start_activity": st.session_state.get("start_filter", "All"),
                        "date_range": f"{st.session_state.get('start_date', 'N/A')} to {st.session_state.get('end_date', 'N/A')}"
                    }

                    # Generate PDF
                    pdf_bytes = generate_pdf_report(
                        discovery_results=discovery_results,
                        comparison_df=comparison_df,
                        case_stats=case_stats,
                        activity_stats=activity_stats,
                        bottleneck_df=bottleneck_df,
                        variant_stats=variant_stats,
                        log_summary=log_summary,
                        filters_applied=filters_applied
                    )

                    # Offer download
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.sidebar.download_button(
                        label="📄 Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"process_mining_report_{timestamp}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.sidebar.success("✅ PDF report generated successfully!")

                except Exception as e:
                    st.sidebar.error(f"❌ Failed to generate PDF: {str(e)}")
                    with st.sidebar.expander("Error Details"):
                        st.code(traceback.format_exc())

    if not analysis_complete:
        st.sidebar.caption("⚠️ Run analysis first to enable report export")

    if run_analysis:
        # Apply filters
        selected_first = None if start_filter == "All" else start_filter
        filter_key = compute_filter_key(log_signature, selected_first, start_date, end_date)

        filtered_cache: Dict[str, EventLog] = st.session_state["filtered_cache"]
        if filter_key in filtered_cache:
            filtered_log = filtered_cache[filter_key]
        else:
            with st.spinner("Applying filters..."):
                filtered_log = filter_start_event(log, selected_first)
                filtered_log = filter_date_range(filtered_log, start_date, end_date)
            filtered_cache[filter_key] = filtered_log

        if len(filtered_log) == 0:
            st.warning("No traces remain after applying the selected filters.")
            st.stop()

        st.session_state["current_filtered_log"] = filtered_log
        st.session_state["current_filter_key"] = filter_key
        st.session_state["current_input_name"] = input_name

        # Apply train/test split if enabled
        if enable_train_test:
            with st.spinner("Splitting log into train (80%) and test (20%) sets..."):
                train_log, test_log, split_info = split_log_random(filtered_log, train_ratio=0.8, random_seed=random_seed)

                # Store in session state
                st.session_state["train_log"] = train_log
                st.session_state["test_log"] = test_log
                st.session_state["split_info"] = split_info
                st.session_state["enable_train_test"] = True

                # Show split statistics
                st.info(f"📊 **Train/Test Split Complete:**\n"
                        f"- Training: {split_info['train_cases']} cases ({split_info['train_ratio']*100:.1f}%), {split_info['train_events']} events\n"
                        f"- Test: {split_info['test_cases']} cases ({split_info['test_ratio']*100:.1f}%), {split_info['test_events']} events\n"
                        f"- Random seed: {split_info['random_seed']}")

                # Warn if test set is too small
                if split_info['test_cases'] < 20:
                    st.warning(f"⚠️ Test set has only {split_info['test_cases']} cases - results may not be reliable. Consider using more data.")

                discovery_log = train_log  # Use training log for discovery
        else:
            st.session_state["train_log"] = None
            st.session_state["test_log"] = None
            st.session_state["split_info"] = {}
            st.session_state["enable_train_test"] = False
            discovery_log = filtered_log  # Use full filtered log

            # Show warning about inflated metrics
            st.warning("⚠️ **Train/Test Split Disabled**: Models will be evaluated on the same data used for discovery. "
                      "This may result in artificially inflated conformance metrics (overfitting bias). "
                      "Enable train/test split for realistic evaluation.")

        # Run discovery for all selected algorithms
        with st.spinner("Running process discovery algorithms..."):
            discovery_cache = st.session_state["discovery_results_cache"]
            # Include train/test mode in cache key
            split_mode = "train_test" if enable_train_test else "full"
            cache_key = f"{filter_key}::{','.join(sorted(selected_algorithms))}::{split_mode}::{random_seed}"

            if cache_key in discovery_cache:
                discovery_results = discovery_cache[cache_key]
            else:
                discovery_results = discover_all_algorithms(discovery_log, selected_algorithms)
                discovery_cache[cache_key] = discovery_results

        st.session_state["discovery_results"] = discovery_results
        st.session_state["analysis_complete"] = True
        st.success(f"✅ Discovery complete! {len(discovery_results)} models discovered.")

except Exception:
    st.error("An unexpected error occurred:")
    st.text(traceback.format_exc())
    st.stop()

# ===========================================================================
# MAIN CONTENT: TABS
# ===========================================================================

if not st.session_state.get("analysis_complete", False):
    st.title("CRPM - Process Mining Workbench")
    st.info("👈 Configure your analysis in the sidebar and click **Run Analysis** to begin.")
    st.stop()

# Retrieve analysis results
filtered_log = st.session_state.get("current_filtered_log")
filter_key = st.session_state.get("current_filter_key")
input_name = st.session_state.get("current_input_name")
discovery_results: Dict[str, DiscoveryResult] = st.session_state.get("discovery_results", {})

if not discovery_results:
    st.warning("No models discovered. Please run the analysis.")
    st.stop()

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Discovery",
    "📊 Model Comparison",
    "⚡ Performance Analytics",
    "🔀 Variant Analysis",
    "🗺️ DFG Visualizations"
])

# ===========================================================================
# TAB 1: DISCOVERY
# ===========================================================================

with tab1:
    st.header("Process Discovery Results")

    st.caption(f"Analyzed log: **{input_name}** | Traces: {len(filtered_log):,} | Events: {sum(len(t) for t in filtered_log):,}")

    # Display all discovered models
    num_models = len(discovery_results)

    if num_models == 0:
        st.info("No models discovered.")
    elif num_models <= 2:
        cols = st.columns(num_models)
    else:
        cols = st.columns(3)

    col_idx = 0
    for model_name, result in discovery_results.items():
        with cols[col_idx % len(cols)]:
            st.subheader(model_name)
            st.caption(f"{result.algorithm} - {result.variant}")

            # Model statistics
            st.metric("Transitions", result.num_transitions)
            st.metric("Places", result.num_places)
            st.metric("Arcs", result.num_arcs)
            st.metric("Discovery Time", f"{result.discovery_time_s:.2f}s")

            # Render visualization
            try:
                if result.heuristics_net:
                    img_bytes = render_heuristics_png(result.heuristics_net)
                else:
                    # Use top-down layout for Inductive Miner variants, left-right for others
                    rankdir = "TB" if result.algorithm == "Inductive Miner" else "LR"
                    img_bytes = render_petri_png(result.net, result.initial_marking, result.final_marking, rankdir=rankdir)

                st.image(img_bytes, caption=f"{model_name} Visualization")

                # Download button
                st.download_button(
                    f"Download {model_name} Image",
                    data=img_bytes,
                    file_name=f"{model_name.replace(' ', '_').lower()}.png",
                    mime="image/png",
                    key=f"download_{model_name}"
                )
            except Exception as e:
                st.error(f"❌ Could not render visualization for {model_name}")
                with st.expander("Error Details"):
                    st.code(str(e))
                    st.caption(
                        "**Common fixes:**\n"
                        "- Ensure Graphviz is installed: `conda install -c conda-forge graphviz` or download from https://graphviz.org/\n"
                        "- Check that model was discovered successfully\n"
                        "- Try a different discovery algorithm"
                    )
                import traceback
                st.text(traceback.format_exc())

        col_idx += 1

        # Start new row after 3 models
        if col_idx % 3 == 0 and col_idx < num_models:
            cols = st.columns(3)


# ===========================================================================
# TAB 2: MODEL COMPARISON
# ===========================================================================

with tab2:
    st.header("Model Comparison & Sensitivity Analysis")

    # Executive summary card
    with st.expander("📊 What Am I Looking At?", expanded=False):
        st.markdown("""
        **This tab compares all discovered models across multiple quality dimensions:**

        - **Fitness**: How well the model can replay the actual event log (higher is better, ≥0.95 is excellent)
        - **Precision**: How strictly the model constrains behavior (higher is better, ≥0.90 is excellent)
        - **Balanced Quality**: Models in the "Ideal Zone" have both high fitness AND high precision

        **Quality Quadrants:**
        - 🟢 **Ideal Zone**: High fitness (≥0.85) & high precision (≥0.75) → Best models
        - 🟡 **Overfitting**: High fitness but low precision → Model allows too much behavior
        - 🟡 **Underfitting**: Low fitness but high precision → Model doesn't capture actual process
        - 🔴 **Poor Quality**: Both metrics low → Try different algorithm

        **What to do:**
        1. Look for models in the Ideal Zone (green)
        2. Consider model complexity (simpler is often better)
        3. Balance fitness and precision based on your use case
        """)

    if len(discovery_results) < 2:
        st.info("At least 2 models required for comparison. Please select more algorithms.")
    else:
        # Determine which log to use for conformance checking
        enable_train_test = st.session_state.get("enable_train_test", False)
        test_log = st.session_state.get("test_log")
        train_log = st.session_state.get("train_log")
        split_info = st.session_state.get("split_info", {})

        # Display info about evaluation mode
        if enable_train_test and test_log is not None:
            st.info(f"📊 **Evaluation Mode:** Train/Test Split Enabled\n"
                   f"- Models discovered on: **Training set** ({split_info.get('train_cases', 0)} cases)\n"
                   f"- Models evaluated on: **Test set** ({split_info.get('test_cases', 0)} cases, unseen data)\n"
                   f"- This provides realistic conformance metrics without overfitting bias.")
            evaluation_log = test_log
            eval_mode = "test"
        else:
            st.warning("⚠️ **Evaluation Mode:** No Train/Test Split\n"
                      "Models are evaluated on the same data used for discovery. "
                      "Metrics may be artificially inflated (overfitting bias).")
            evaluation_log = filtered_log
            eval_mode = "full"

        st.markdown("Computing conformance metrics for all models...")

        # Compute conformance for all models
        conformance_results = {}

        progress_bar = st.progress(0)
        for idx, (model_name, result) in enumerate(discovery_results.items()):
            progress_bar.progress((idx + 1) / len(discovery_results))

            # Check cache - include eval mode in cache key
            conf_cache_key = f"{filter_key}::{model_name}::{eval_mode}"
            if conf_cache_key in st.session_state["conformance_cache"]:
                conformance_results[model_name] = st.session_state["conformance_cache"][conf_cache_key]
            else:
                with st.spinner(f"Computing conformance for {model_name}..."):
                    conf_result = compute_full_conformance(
                        evaluation_log,
                        result.net,
                        result.initial_marking,
                        result.final_marking,
                        model_name
                    )
                    conformance_results[model_name] = conf_result
                    st.session_state["conformance_cache"][conf_cache_key] = conf_result

        progress_bar.empty()

        # Build comparison table
        comparison_data = []
        for model_name, result in discovery_results.items():
            conf = conformance_results.get(model_name, {})
            summary = conf.get("summary", {})

            align_fitness = summary.get("alignment_fitness", {}).get("log_fitness", None)
            token_fitness = summary.get("token_fitness", {}).get("log_fitness", None)
            precision = conf.get("precision", None)

            # Model complexity
            complexity = compute_model_complexity(result)

            comparison_data.append({
                "model_name": model_name,
                "algorithm": result.algorithm,
                "variant": result.variant,
                "alignment_fitness": align_fitness,
                "token_fitness": token_fitness,
                "precision": precision,
                "num_transitions": result.num_transitions,
                "num_places": result.num_places,
                "arc_degree": complexity.get("arc_degree", 0),
                "complexity_score": complexity.get("complexity_score", 0),
                "discovery_time_s": result.discovery_time_s
            })

        comparison_df = pd.DataFrame(comparison_data)

        # Add quality assessments
        comparison_df["fitness_quality"] = comparison_df["alignment_fitness"].apply(
            lambda x: assess_fitness(x)[0] if pd.notna(x) else "N/A"
        )
        comparison_df["precision_quality"] = comparison_df["precision"].apply(
            lambda x: assess_precision(x)[0] if pd.notna(x) else "N/A"
        )
        comparison_df["quadrant"] = comparison_df.apply(
            lambda row: get_model_quadrant(row["alignment_fitness"], row["precision"]),
            axis=1
        )

        # Display comparison table
        st.subheader("Conformance Metrics Comparison")

        # Format for display
        display_df = comparison_df.copy()
        numeric_cols = ["alignment_fitness", "token_fitness", "precision", "arc_degree", "complexity_score", "discovery_time_s"]
        for col in numeric_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "N/A")

        # Reorder columns to show quality indicators
        col_order = ["model_name", "algorithm", "variant", "alignment_fitness", "fitness_quality",
                     "precision", "precision_quality", "quadrant", "num_transitions", "num_places",
                     "discovery_time_s"]
        display_df = display_df[[c for c in col_order if c in display_df.columns]]

        st.dataframe(display_df, use_container_width=True, height=DATAFRAME_HEIGHT)

        # Download button
        st.download_button(
            "Download Comparison CSV",
            comparison_df.to_csv(index=False).encode(),
            file_name="model_comparison.csv",
            mime="text/csv"
        )

        # Visualizations
        st.markdown("---")
        st.subheader("Visual Comparison")

        viz_col1, viz_col2 = st.columns(2)

        with viz_col1:
            st.markdown("**Fitness vs Precision (Pareto Frontier)**")
            try:
                fig = create_fitness_precision_scatter(comparison_df)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Could not create scatter plot: {e}")

        with viz_col2:
            st.markdown("**Metrics Heatmap**")
            try:
                metrics = ["alignment_fitness", "token_fitness", "precision"]
                fig = create_model_comparison_heatmap(comparison_df, metrics)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Could not create heatmap: {e}")

        # Recommendation
        st.markdown("---")
        st.subheader("🎯 Model Recommendation")

        # Find best model by different criteria
        best_fitness = comparison_df.loc[comparison_df["alignment_fitness"].idxmax()] if "alignment_fitness" in comparison_df.columns else None
        best_precision = comparison_df.loc[comparison_df["precision"].idxmax()] if "precision" in comparison_df.columns else None
        best_balanced = comparison_df.loc[(comparison_df["alignment_fitness"].fillna(0) + comparison_df["precision"].fillna(0)).idxmax()] if "alignment_fitness" in comparison_df.columns and "precision" in comparison_df.columns else None

        rec_col1, rec_col2, rec_col3 = st.columns(3)

        with rec_col1:
            if best_fitness is not None:
                fitness_assessment = assess_fitness(best_fitness["alignment_fitness"])
                st.metric("Best Fitness", best_fitness["model_name"], f"{best_fitness['alignment_fitness']:.4f}")
                st.caption(f"{get_quality_badge_html(fitness_assessment[0], fitness_assessment[1])} {fitness_assessment[2]}", unsafe_allow_html=True)

        with rec_col2:
            if best_precision is not None:
                precision_assessment = assess_precision(best_precision["precision"])
                st.metric("Best Precision", best_precision["model_name"], f"{best_precision['precision']:.4f}")
                st.caption(f"{get_quality_badge_html(precision_assessment[0], precision_assessment[1])} {precision_assessment[2]}", unsafe_allow_html=True)

        with rec_col3:
            if best_balanced is not None:
                balanced_score = (best_balanced.get("alignment_fitness", 0) + best_balanced.get("precision", 0)) / 2
                balanced_assessment = assess_balanced_quality(
                    best_balanced.get("alignment_fitness", 0),
                    best_balanced.get("precision", 0)
                )
                st.metric("Best Balanced", best_balanced["model_name"], f"{balanced_score:.4f}")
                st.caption(f"{get_quality_badge_html(balanced_assessment[0], balanced_assessment[1])} {balanced_assessment[2]}", unsafe_allow_html=True)

        # Overall recommendation
        st.markdown("---")
        if best_balanced is not None:
            quadrant = get_model_quadrant(best_balanced.get("alignment_fitness", 0), best_balanced.get("precision", 0))
            if "Ideal" in quadrant:
                st.success(f"✅ **Recommended**: Use **{best_balanced['model_name']}** for production. It has the best balance of fitness and precision.")
            elif "Overfitting" in quadrant:
                st.warning(f"⚠️ **{best_balanced['model_name']}** has high fitness but low precision. Consider using a more restrictive algorithm like Heuristics Miner.")
            elif "Underfitting" in quadrant:
                st.warning(f"⚠️ **{best_balanced['model_name']}** has high precision but low fitness. Consider using Inductive Miner for better fitness guarantees.")
            else:
                st.error(f"⚠️ All models show poor quality. Try different algorithm parameters or check data quality.")


# ===========================================================================
# TAB 3: PERFORMANCE ANALYTICS
# ===========================================================================

with tab3:
    st.header("Performance Analytics & Bottleneck Detection")

    # Executive summary card
    with st.expander("📊 What Am I Looking At?", expanded=False):
        st.markdown("""
        **This tab analyzes process performance and identifies bottlenecks:**

        - **Case Duration**: How long cases take from start to finish
        - **Process Variance**: Consistency of process execution times
          - 🟢 **Low variance** (<20% of median) = Consistent, predictable process
          - 🟡 **Medium variance** (20-50%) = Some variability to investigate
          - 🔴 **High variance** (>50%) = Significant outliers, investigate delays

        - **Bottlenecks**: Transitions that take the longest time
          - 🔴 **Critical**: >3x median duration, high frequency → Immediate attention
          - 🟠 **High**: >2x median duration → Should be optimized
          - 🟡 **Moderate**: >1.5x median → Monitor closely

        **What to do:**
        1. Check variance - high variance means inconsistent process
        2. Focus on red/orange bottlenecks for optimization
        3. Investigate P90 outliers for process improvements
        """)

    # Select model for performance analysis
    model_options = list(discovery_results.keys())
    selected_model = st.selectbox("Select model for performance analysis:", model_options)

    if selected_model:
        result = discovery_results[selected_model]

        # Compute performance metrics
        perf_cache_key = f"{filter_key}::{selected_model}::performance"

        if perf_cache_key in st.session_state["performance_cache"]:
            activity_stats = st.session_state["performance_cache"][perf_cache_key]["activity_stats"]
            transition_stats = st.session_state["performance_cache"][perf_cache_key]["transition_stats"]
            bottlenecks = st.session_state["performance_cache"][perf_cache_key]["bottlenecks"]
            case_durations = st.session_state["performance_cache"][perf_cache_key]["case_durations"]
            case_stats = st.session_state["performance_cache"][perf_cache_key]["case_stats"]
        else:
            with st.spinner("Computing performance analytics..."):
                activity_stats = compute_activity_statistics(filtered_log)

                # Extract model transitions
                model_transitions = extract_model_transitions(result.net, result.initial_marking, result.final_marking)
                transition_stats = compute_transition_statistics(filtered_log, model_transitions, min_occurrences=3)
                bottlenecks = detect_bottlenecks(transition_stats, top_n=10)

                case_durations = compute_case_durations(filtered_log)
                case_stats = compute_case_statistics(case_durations)

                st.session_state["performance_cache"][perf_cache_key] = {
                    "activity_stats": activity_stats,
                    "transition_stats": transition_stats,
                    "bottlenecks": bottlenecks,
                    "case_durations": case_durations,
                    "case_stats": case_stats
                }

        # Display case statistics
        st.subheader("Case Duration Statistics")
        stat_cols = st.columns(5)

        with stat_cols[0]:
            st.metric("Total Cases", f"{case_stats.get('total_cases', 0):,}")
        with stat_cols[1]:
            median_days = case_stats.get('median_duration_s', 0) / 86400
            st.metric("Median Duration", f"{median_days:.4f} days")
        with stat_cols[2]:
            avg_days = case_stats.get('avg_duration_s', 0) / 86400
            st.metric("Avg Duration", f"{avg_days:.4f} days")
        with stat_cols[3]:
            p90_days = case_stats.get('p90_duration_s', 0) / 86400
            st.metric("P90 Duration", f"{p90_days:.4f} days")
        with stat_cols[4]:
            max_days = case_stats.get('max_duration_s', 0) / 86400
            st.metric("Max Duration", f"{max_days:.4f} days")

        # Process variance assessment
        std_dev = case_stats.get('std_duration_s', 0)
        median_s = case_stats.get('median_duration_s', 1)
        variance_assessment = assess_process_variance(std_dev, median_s)

        st.markdown(f"""
        **Process Consistency**: {get_quality_badge_html(variance_assessment[0], variance_assessment[1])} - {variance_assessment[2]}
        """, unsafe_allow_html=True)

        # Outlier assessment
        p90_s = case_stats.get('p90_duration_s', 0)
        outlier_assessment = assess_case_duration_outliers(p90_s, median_s)

        if outlier_assessment[1] == "red":
            st.warning(f"⚠️ **Outliers Detected**: {outlier_assessment[2]}")
        elif outlier_assessment[1] == "orange":
            st.info(f"ℹ️ {outlier_assessment[2]}")

        # Bottleneck analysis
        st.markdown("---")
        st.subheader("🔥 Top Bottlenecks")

        if not bottlenecks.empty:
            fig = create_bottleneck_chart(bottlenecks, top_n=10)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Bottleneck Details"):
                st.dataframe(bottlenecks, use_container_width=True, height=DATAFRAME_HEIGHT)
                st.download_button(
                    "Download Bottleneck Data",
                    bottlenecks.to_csv(index=False).encode(),
                    file_name="bottlenecks.csv",
                    mime="text/csv"
                )
        else:
            st.info("No bottlenecks detected.")

        # Activity statistics
        st.markdown("---")
        st.subheader("Activity Statistics")

        if not activity_stats.empty:
            # Convert to days for display
            display_stats = activity_stats.copy()
            duration_cols = [c for c in display_stats.columns if "_duration_s" in c]
            for col in duration_cols:
                new_col = col.replace("_s", "_days")
                display_stats[new_col] = (display_stats[col] / 86400).round(4)
                display_stats.drop(col, axis=1, inplace=True)

            st.dataframe(display_stats, use_container_width=True, height=DATAFRAME_HEIGHT)

            st.download_button(
                "Download Activity Statistics",
                activity_stats.to_csv(index=False).encode(),
                file_name="activity_statistics.csv",
                mime="text/csv"
            )
        else:
            st.info("No activity statistics available.")

        # Case duration distribution
        st.markdown("---")
        st.subheader("Case Duration Distribution")

        if not case_durations.empty:
            fig = create_case_duration_histogram(case_durations)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No case duration data available.")


# ===========================================================================
# TAB 4: VARIANT ANALYSIS
# ===========================================================================

with tab4:
    st.header("Variant Analysis")

    # Executive summary card
    with st.expander("📊 What Am I Looking At?", expanded=False):
        st.markdown("""
        **This tab analyzes process variants - unique paths through the process:**

        - **Variant**: A unique sequence of activities from start to finish
        - **Variant Coverage**: What percentage of cases follow common paths

        **Standardization Assessment:**
        - 🟢 **Excellent** (Top 10 variants cover ≥80%) → Highly standardized process
        - 🟡 **Good** (60-80% coverage) → Moderate standardization
        - 🔴 **Poor** (<60% coverage) → High variability, review compliance

        **What high variability means:**
        - Many unique paths through the process
        - Potential lack of standardization
        - May indicate process flexibility or lack of control

        **What to do:**
        1. Check top 10 variant coverage percentage
        2. Low coverage? Review why so many variants exist
        3. Focus conformance improvements on high-frequency variants
        """)

    # Configuration
    top_n_variants = st.slider("Number of top variants to analyze:", min_value=5, max_value=50, value=20, step=5)

    # Select model for variant analysis
    model_options = list(discovery_results.keys())
    selected_model = st.selectbox("Select model for variant conformance:", model_options, key="variant_model_select")

    if selected_model:
        result = discovery_results[selected_model]

        # Compute variant statistics
        variant_cache_key = f"{filter_key}::{selected_model}::variants::{top_n_variants}"

        if variant_cache_key in st.session_state["variant_cache"]:
            variant_stats = st.session_state["variant_cache"][variant_cache_key]["variant_stats"]
            variant_conformance = st.session_state["variant_cache"][variant_cache_key]["variant_conformance"]
            variant_coverage = st.session_state["variant_cache"][variant_cache_key]["variant_coverage"]
        else:
            with st.spinner("Analyzing variants..."):
                variant_stats = get_variant_statistics(filtered_log, top_n=top_n_variants)
                variant_conformance = compute_variant_conformance(
                    filtered_log,
                    result.net,
                    result.initial_marking,
                    result.final_marking,
                    top_n=top_n_variants,
                    sample_alignments=True,
                    max_alignment_samples=100
                )
                variant_coverage = compute_variant_coverage(variant_stats)

                st.session_state["variant_cache"][variant_cache_key] = {
                    "variant_stats": variant_stats,
                    "variant_conformance": variant_conformance,
                    "variant_coverage": variant_coverage
                }

        # Display variant frequency
        st.subheader("Variant Frequency Distribution")

        if not variant_stats.empty:
            fig = create_variant_frequency_chart(variant_stats, top_n=top_n_variants)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No variant data available.")

        # Coverage analysis
        st.markdown("---")
        st.subheader("Cumulative Variant Coverage")

        if not variant_coverage.empty:
            col1, col2 = st.columns([2, 1])

            with col1:
                fig = create_variant_coverage_chart(variant_coverage)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Calculate coverage milestones
                def find_coverage_n(df, target_pct):
                    try:
                        return int((df["cumulative_percentage"] >= target_pct).idxmax()) + 1
                    except:
                        return None

                n_50 = find_coverage_n(variant_coverage, 50)
                n_80 = find_coverage_n(variant_coverage, 80)
                n_90 = find_coverage_n(variant_coverage, 90)

                st.metric("Variants for 50% coverage", n_50 if n_50 else "N/A")
                st.metric("Variants for 80% coverage", n_80 if n_80 else "N/A")
                st.metric("Variants for 90% coverage", n_90 if n_90 else "N/A")

            # Coverage assessment
            st.markdown("---")
            top_10_coverage = variant_stats.head(10)["percentage"].sum() if not variant_stats.empty and "percentage" in variant_stats.columns else 0
            coverage_assessment = assess_variant_coverage(top_10_coverage, top_n=10)

            st.markdown(f"""
            **Process Standardization**: {get_quality_badge_html(coverage_assessment[0], coverage_assessment[1])} - {coverage_assessment[2]}
            """, unsafe_allow_html=True)

            # Variant count assessment
            num_variants = len(variant_stats) if not variant_stats.empty else 0
            num_cases = case_stats.get('total_cases', 0)
            variant_count_assessment = assess_variant_count(num_variants, num_cases)

            if variant_count_assessment[1] == "red":
                st.warning(f"⚠️ **High Variant Diversity**: {variant_count_assessment[2]}")
            elif variant_count_assessment[1] == "green":
                st.success(f"✅ {variant_count_assessment[2]}")

        # Variant conformance
        st.markdown("---")
        st.subheader("Per-Variant Conformance")

        if not variant_conformance.empty:
            # Format for display
            display_conf = variant_conformance.copy()

            # Truncate long variants
            if "variant" in display_conf.columns:
                display_conf["variant"] = display_conf["variant"].apply(
                    lambda x: x[:100] + "..." if len(str(x)) > 100 else x
                )

            st.dataframe(display_conf, use_container_width=True, height=DATAFRAME_HEIGHT)

            st.download_button(
                "Download Variant Conformance",
                variant_conformance.to_csv(index=False).encode(),
                file_name="variant_conformance.csv",
                mime="text/csv"
            )

            # Highlight non-conforming variants
            with st.expander("Non-Conforming Variants (Fitness < 0.8)"):
                if "align_fitness" in variant_conformance.columns:
                    non_conforming = variant_conformance[variant_conformance["align_fitness"] < 0.8]
                    if not non_conforming.empty:
                        st.dataframe(non_conforming, use_container_width=True, height=DATAFRAME_HEIGHT)
                        st.caption(f"{len(non_conforming)} variants with fitness < 0.8")
                    else:
                        st.success("All variants have fitness >= 0.8")
                else:
                    st.info("Fitness data not available.")
        else:
            st.info("No variant conformance data available.")


# ===========================================================================
# TAB 5: DFG VISUALIZATIONS
# ===========================================================================

with tab5:
    st.header("Directly-Follows Graph (DFG) Visualizations")

    # DFG Type Selection
    dfg_type = st.radio("DFG Type:", ["Frequency-Based", "Performance-Based"], horizontal=True)

    # Compute DFG
    dfg_cache_key = f"{filter_key}::{dfg_type}"

    if dfg_cache_key in st.session_state["dfg_cache"]:
        dfg = st.session_state["dfg_cache"][dfg_cache_key]["dfg"]
        start_activities = st.session_state["dfg_cache"][dfg_cache_key]["start_activities"]
        end_activities = st.session_state["dfg_cache"][dfg_cache_key]["end_activities"]
    else:
        with st.spinner(f"Discovering {dfg_type} DFG..."):
            if dfg_type == "Frequency-Based":
                dfg, start_activities, end_activities = discover_dfg_frequency(filtered_log)
            else:
                dfg, start_activities, end_activities = discover_dfg_performance(filtered_log)

            st.session_state["dfg_cache"][dfg_cache_key] = {
                "dfg": dfg,
                "start_activities": start_activities,
                "end_activities": end_activities
            }

    # DFG Statistics
    st.subheader("DFG Statistics")
    stats = get_dfg_statistics(dfg, start_activities, end_activities)

    stat_cols = st.columns(5)
    with stat_cols[0]:
        st.metric("Activities", stats["num_activities"])
    with stat_cols[1]:
        st.metric("Edges", stats["num_edges"])
    with stat_cols[2]:
        st.metric("Start Activities", stats["num_start_activities"])
    with stat_cols[3]:
        st.metric("End Activities", stats["num_end_activities"])
    with stat_cols[4]:
        if dfg_type == "Frequency-Based":
            st.metric("Total Transitions", f"{stats['total_value']:,}")
        else:
            st.metric("Total Time (h)", f"{stats['total_value']/3600:.1f}")

    # Filtering Options
    st.markdown("---")
    st.subheader("Filtering Options")

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        if dfg_type == "Frequency-Based":
            min_frequency = st.slider(
                "Minimum edge frequency:",
                min_value=1,
                max_value=max(list(dfg.values())) if dfg else 1,
                value=1
            )
        else:
            min_frequency = st.slider(
                "Minimum edge occurrences:",
                min_value=1,
                max_value=100,
                value=1
            )

    with filter_col2:
        percentage_filter = st.slider(
            "Keep top % of edges:",
            min_value=0,
            max_value=100,
            value=100,
            step=5
        )

    # Apply filters
    filtered_dfg, filtered_start, filtered_end = filter_dfg_by_frequency(
        dfg, start_activities, end_activities,
        min_frequency=min_frequency,
        percentage=100 - percentage_filter
    )

    # Display filtered statistics
    filtered_stats = get_dfg_statistics(filtered_dfg, filtered_start, filtered_end)
    st.caption(
        f"Filtered DFG: {filtered_stats['num_activities']} activities, "
        f"{filtered_stats['num_edges']} edges "
        f"({filtered_stats['num_edges']/stats['num_edges']*100:.1f}% of original)"
    )

    # Visualization
    st.markdown("---")
    st.subheader("DFG Visualization")

    if filtered_dfg:
        try:
            variant_name = "performance" if dfg_type == "Performance-Based" else "frequency"
            dfg_img = render_dfg_to_png(filtered_dfg, filtered_start, filtered_end, variant=variant_name)

            st.image(dfg_img, caption=f"{dfg_type} DFG")

            # Download button
            st.download_button(
                "Download DFG Image",
                data=dfg_img,
                file_name=f"dfg_{variant_name}.png",
                mime="image/png"
            )
        except Exception as e:
            st.error(f"❌ Could not render DFG visualization")
            with st.expander("Error Details"):
                st.code(str(e))
                st.caption(
                    "**Common fixes:**\n"
                    "- Ensure Graphviz is installed: `conda install -c conda-forge graphviz` or download from https://graphviz.org/\n"
                    "- Try relaxing filter criteria to include more edges\n"
                    "- Check that the log has valid transitions"
                )
            import traceback
            st.text(traceback.format_exc())
    else:
        st.warning("No edges in filtered DFG. Try relaxing the filter criteria.")

    # DFG Details Table
    with st.expander("DFG Edge Details"):
        if filtered_dfg:
            # Convert to DataFrame
            edge_data = []
            for (source, target), value in filtered_dfg.items():
                if dfg_type == "Frequency-Based":
                    display_value = value
                else:
                    # Convert to days with 4 decimals
                    days = value / 86400
                    display_value = f"{value:.4f}s ({days:.4f} days)"

                edge_data.append({
                    "Source": source,
                    "Target": target,
                    "Value": display_value
                })

            edge_df = pd.DataFrame(edge_data)
            edge_df = edge_df.sort_values("Value", ascending=False) if dfg_type == "Frequency-Based" else edge_df
            st.dataframe(edge_df, use_container_width=True, height=DATAFRAME_HEIGHT)

            # Download button
            st.download_button(
                "Download DFG Data",
                edge_df.to_csv(index=False).encode(),
                file_name=f"dfg_{variant_name}_edges.csv",
                mime="text/csv"
            )
        else:
            st.info("No edges to display.")

st.sidebar.markdown("---")
st.sidebar.caption("CRPM v2.0 - Comprehensive Process Mining Workbench")
