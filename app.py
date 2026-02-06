import base64
import hashlib
import io
import os
import tempfile
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
import streamlit as st

# Ensure PM4Py dependencies are available before the UI proceeds.
try:
    from pm4py.visualization.heuristics_net import visualizer as hn_vis
except Exception as exc:  # pragma: no cover - handled at runtime
    st.error(
        f"Failed to import PM4Py modules: {exc}\n"
        "Make sure you've run: pip install pm4py[all] lxml graphviz"
    )
    st.stop()

from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.importer.importer import apply as pnml_importer

from crpm.conformance import (
    load_log,
    filter_start_event,
    filter_date_range,
    run_heuristics_miner,
    compute_alignments,
    compute_token_replay,
    summarize_metrics,
)
from crpm.pipeline import csv_to_event_log, discover_petri_inductive

# ---------------------------------------------------------------------------
# Streamlit configuration
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
ENV_OUTPUT_DIR = Path(os.environ.get("CRPM_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

st.set_page_config(
    page_title="Heuristics Miner",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.sidebar.title("CRPM - Process Mining App")
st.title("Process Mining with Heuristics Miner")


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def init_session_caches() -> None:
    """Ensure cache dictionaries exist in session state."""
    for key in (
        "log_cache",
        "dataframe_cache",
        "filtered_cache",
        "model_cache",
        "conformance_cache",
    ):
        st.session_state.setdefault(key, {})


def make_file_signature(path: Path) -> str:
    """Build a stable signature for an on-disk file."""
    try:
        stat = path.stat()
    except OSError:
        return str(path.resolve())
    return f"{path.resolve()}::{stat.st_size}::{stat.st_mtime_ns}"


def make_uploaded_signature(raw: bytes, label: str) -> str:
    """Hash uploaded file content for caching."""
    digest = hashlib.sha256(raw).hexdigest()
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

    return "::".join(
        [
            log_signature,
            first_event or "*",
            _fmt(start_dt),
            _fmt(end_dt),
        ]
    )


def compute_run_key(
    filtered_key: str,
    model_choice: str,
    pnml_signature: Optional[str],
) -> str:
    """Key representing a full conformance run configuration."""
    return "::".join(
        [
            filtered_key,
            model_choice,
            pnml_signature or "-",
        ]
    )


def render_heuristics_png(heu_net) -> bytes:
    """Render heuristics net to PNG bytes."""
    gviz = hn_vis.apply(heu_net)
    try:
        return gviz.pipe(format="png")  # type: ignore[attr-defined]
    except Exception:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp_path = Path(tmp.name)
        try:
            hn_vis.save(gviz, str(tmp_path))
            return tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)


def first_event_names(log: EventLog) -> list[str]:
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
# Main UI / logic
# ---------------------------------------------------------------------------

init_session_caches()

try:
    source_type = st.sidebar.radio("Input source", ["XES", "CSV"], horizontal=True)

    output_dir_str = st.sidebar.text_input("Output directory", str(ENV_OUTPUT_DIR))
    OUTPUT_DIR = Path(output_dir_str)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB

    log: EventLog
    log_signature: str
    input_name: str

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

    else:
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

        st.subheader("CSV preview")
        st.dataframe(df.head(50), use_container_width=True)

        cols = list(df.columns)
        if not cols:
            st.sidebar.error("Uploaded CSV has no columns.")
            st.stop()

        st.markdown("Map CSV columns to event log fields:")
        case_col = st.selectbox("Case ID column", cols, index=0 if cols else None)
        activity_col = st.selectbox("Activity column", cols, index=1 if len(cols) > 1 else 0)
        timestamp_col = st.selectbox("Timestamp column", cols, index=2 if len(cols) > 2 else 0)

        # Basic validation before conversion
        selected_cols = {case_col, activity_col, timestamp_col}
        if len(selected_cols) < 3:
            st.sidebar.error("Please choose three distinct columns for case, activity, and timestamp.")
            st.stop()

        if df.empty:
            st.sidebar.error("Uploaded CSV is empty.")
            st.stop()

        parsed_timestamps = pd.to_datetime(df[timestamp_col], errors="coerce")
        invalid_ts = parsed_timestamps.isna().sum()
        if invalid_ts:
            st.sidebar.error(
                f"Timestamp column '{timestamp_col}' contains {invalid_ts} unparsable value(s)."
            )
            st.stop()

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

    # -----------------------------------------------------------------------
    # Filters and preview
    # -----------------------------------------------------------------------

    start_events = first_event_names(log)
    start_filter = st.sidebar.selectbox(
        "Filter by first event",
        ["All"] + start_events,
    )

    if st.sidebar.checkbox("Apply date filter"):
        start_date = st.sidebar.date_input("Start date")
        end_date = st.sidebar.date_input("End date")
    else:
        start_date = end_date = None

    log_stats = compute_log_stats(log)
    stats_parts = [
        f"{log_stats['traces']:,} traces",
        f"{log_stats['events']:,} events",
    ]
    if log_stats["start"] and log_stats["end"]:
        stats_parts.append(
            f"{log_stats['start']:%Y-%m-%d} → {log_stats['end']:%Y-%m-%d}"
        )
    st.info(" · ".join(stats_parts))

    with st.expander("Preview events table", expanded=False):
        try:
            rows = []
            max_rows = 200
            count = 0
            for trace in log:
                case_id = trace.attributes.get("concept:name") if hasattr(trace, "attributes") else None
                for event in trace:
                    rows.append(
                        {
                            "case:concept:name": case_id,
                            "concept:name": event.get("concept:name"),
                            "time:timestamp": event.get("time:timestamp"),
                        }
                    )
                    count += 1
                    if count >= max_rows:
                        break
                if count >= max_rows:
                    break
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.caption("No events to preview.")
        except Exception:
            st.caption("Could not build preview table.")

    # -----------------------------------------------------------------------
    # Model selection
    # -----------------------------------------------------------------------

    model_choice = st.sidebar.selectbox("Conformance model", ["heuristics", "inductive", "uploaded PNML"])
    pnml_file = None
    pnml_signature = None
    if model_choice == "uploaded PNML":
        pnml_file = st.sidebar.file_uploader("Upload PNML for conformance", type=["pnml", "xml"])
        if pnml_file is not None:
            pnml_bytes = pnml_file.getvalue()
            if len(pnml_bytes) > MAX_UPLOAD_BYTES:
                st.sidebar.error(
                    f"PNML upload too large ({len(pnml_bytes)/(1024*1024):.1f} MB). "
                    f"Max allowed: {MAX_UPLOAD_BYTES/(1024*1024):.0f} MB."
                )
                st.stop()
            pnml_signature = make_uploaded_signature(pnml_bytes, "pnml")

    # -----------------------------------------------------------------------
    # Run analysis button
    # -----------------------------------------------------------------------

    if st.sidebar.button("Run analysis"):
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
            st.session_state["conformance_cached"] = False
            st.stop()

        model_cache: Dict[str, dict] = st.session_state["model_cache"]
        heuristics_key = f"heuristics::{filter_key}"
        if heuristics_key in model_cache:
            heuristics_data = model_cache[heuristics_key]
        else:
            with st.spinner("Running heuristics miner..."):
                heu_net, heur_net_net, heur_net_im, heur_net_fm = run_heuristics_miner(filtered_log)
            image_bytes = render_heuristics_png(heu_net)
            heuristics_data = {
                "heu_net": heu_net,
                "petri": (heur_net_net, heur_net_im, heur_net_fm),
                "image_bytes": image_bytes,
            }
            model_cache[heuristics_key] = heuristics_data

        filtered_events = sum(len(trace) for trace in filtered_log)
        filter_desc = []
        if selected_first:
            filter_desc.append(f"first event = '{selected_first}'")
        if start_date or end_date:
            date_parts = []
            if start_date:
                date_parts.append(f"from {start_date:%Y-%m-%d}")
            if end_date:
                date_parts.append(f"until {end_date:%Y-%m-%d}")
            filter_desc.append(" ".join(date_parts))
        filter_summary = " · ".join(filter_desc) if filter_desc else "no additional filters"
        st.session_state["last_filter_summary"] = (
            f"Subset: {len(filtered_log):,} traces · {filtered_events:,} events ({filter_summary})"
        )

        conformance_net: Tuple[object, object, object]
        if model_choice == "heuristics":
            conformance_net = heuristics_data["petri"]
        elif model_choice == "inductive":
            inductive_key = f"inductive::{filter_key}"
            if inductive_key in model_cache:
                conformance_net = model_cache[inductive_key]["petri"]
            else:
                with st.spinner("Running inductive miner..."):
                    ind_net, ind_im, ind_fm = discover_petri_inductive(filtered_log)
                model_cache[inductive_key] = {"petri": (ind_net, ind_im, ind_fm)}
                conformance_net = (ind_net, ind_im, ind_fm)
        else:
            if pnml_file is None or pnml_signature is None:
                st.error("Please upload a PNML file for conformance.")
                st.stop()
            pnml_key = f"pnml::{pnml_signature}"
            if pnml_key in model_cache:
                conformance_net = model_cache[pnml_key]["petri"]
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pnml") as tmp:
                    tmp.write(pnml_file.getvalue())
                    pnml_path = Path(tmp.name)
                try:
                    with st.spinner("Loading PNML..."):
                        net_u, im_u, fm_u = pnml_importer(str(pnml_path))
                finally:
                    pnml_path.unlink(missing_ok=True)
                model_cache[pnml_key] = {"petri": (net_u, im_u, fm_u)}
                conformance_net = (net_u, im_u, fm_u)

        run_key = compute_run_key(filter_key, model_choice, pnml_signature)
        conf_cache: Dict[str, dict] = st.session_state["conformance_cache"]
        if run_key in conf_cache:
            run_data = conf_cache[run_key]
            cached = True
        else:
            net_c, im_c, fm_c = conformance_net
            with st.spinner("Computing alignments and token replay..."):
                align_res = compute_alignments(filtered_log, net_c, im_c, fm_c)
                token_res = compute_token_replay(filtered_log, net_c, im_c, fm_c)
                summary = summarize_metrics(align_res, token_res)
            run_data = {
                "alignments": align_res,
                "token": token_res,
                "summary": summary,
            }
            conf_cache[run_key] = run_data
            cached = False

        st.session_state.update(
            {
                "last_run_key": run_key,
                "last_summary": run_data["summary"],
                "last_alignments": run_data["alignments"],
                "last_token": run_data["token"],
                "heuristics_image_bytes": heuristics_data["image_bytes"],
                "heuristics_image_name": f"{Path(input_name).stem}_heuristics.png",
                "conformance_cached": cached,
            }
        )

    # -----------------------------------------------------------------------
    # Results presentation
    # -----------------------------------------------------------------------

    if "heuristics_image_bytes" in st.session_state:
        if st.session_state.get("conformance_cached"):
            st.toast("Loaded cached results for this configuration.", icon="✅")

        if st.session_state.get("last_filter_summary"):
            st.caption(st.session_state["last_filter_summary"])

        def summary_to_df(summary_dict: dict) -> pd.DataFrame:
            groups = list(summary_dict.keys())
            metrics = set()
            for group in groups:
                inner = summary_dict.get(group) or {}
                metrics.update(inner.keys())
            metrics = sorted(metrics)
            data = {
                group: [summary_dict.get(group, {}).get(metric) for metric in metrics]
                for group in groups
            }
            table = pd.DataFrame(data, index=metrics)
            for column in table.columns:
                try:
                    table[column] = pd.to_numeric(table[column])
                except (ValueError, TypeError):
                    continue
            return table

        summary = st.session_state.get("last_summary", {})
        df_summary = summary_to_df(summary)

        left_col, right_col = st.columns([2, 1])

        with left_col:
            try:
                img_bytes = st.session_state["heuristics_image_bytes"]
                b64 = base64.b64encode(img_bytes).decode()
                img_html = (
                    '<img src="data:image/png;base64,'
                    f"{b64}"
                    '" style="width:100%; height:auto; display:block; margin-left:auto; margin-right:auto;" />'
                )
                st.markdown(
                    '<div style="border:2px solid #555; padding:16px; border-radius:8px; '
                    'background-color:#0a0a0a; min-height:600px; display:flex; '
                    'align-items:center; justify-content:center;">'
                    f"{img_html}</div>",
                    unsafe_allow_html=True,
                )
            except Exception:
                st.image(
                    st.session_state["heuristics_image_bytes"],
                    caption="Heuristics Net",
                    use_column_width=True,
                )

        with right_col:
            st.subheader("Conformance summary")

            summary_metrics = [
                ("Alignment log_fitness", "alignment_fitness", "log_fitness", "Average fitness across alignment results."),
                ("Token log_fitness", "token_fitness", "log_fitness", "Average fitness from token replay."),
                ("% fitting traces", "alignment_fitness", "percentage_of_fitting_traces", "Percentage of traces that perfectly fit the model."),
            ]
            metric_cols = st.columns(len(summary_metrics))
            for col, (label, group, metric, help_text) in zip(metric_cols, summary_metrics):
                value = summary.get(group, {}).get(metric)
                display_value = f"{value:.6f}" if isinstance(value, (int, float)) else value
                col.metric(label, display_value if value is not None else "-")
                col.caption(help_text)

            transpose = st.checkbox("Transpose table (groups x metrics)", value=False)
            display_df = df_summary.T if transpose else df_summary
            st.dataframe(display_df.round(6), use_container_width=True)

            try:
                csv_bytes = display_df.to_csv().encode()
                st.download_button(
                    "Download conformance CSV",
                    csv_bytes,
                    file_name="conformance_summary.csv",
                    mime="text/csv",
                )
            except Exception:
                pass

            with st.expander("Advanced diagnostics", expanded=False):
                alignments = st.session_state.get("last_alignments", {}).get("aligned_traces")
                if isinstance(alignments, list) and alignments:
                    align_rows = []
                    for idx, entry in enumerate(alignments[:50]):
                        align_rows.append(
                            {
                                "trace_index": idx,
                                "fitness": entry.get("fitness"),
                                "cost": entry.get("cost"),
                                "is_fit": entry.get("is_fit"),
                            }
                        )
                    st.write("Alignments (first 50 traces)")
                    st.dataframe(pd.DataFrame(align_rows).round(6), use_container_width=True)
                    if len(alignments) > 50:
                        st.caption(f"Showing 50 of {len(alignments):,} alignment records.")
                tokens = st.session_state.get("last_token", {}).get("token_results")
                if isinstance(tokens, list) and tokens:
                    token_rows = []
                    for idx, entry in enumerate(tokens[:50]):
                        token_rows.append(
                            {
                                "trace_index": idx,
                                "fitness": entry.get("trace_fitness"),
                                "consumed": entry.get("consumed_tokens"),
                                "produced": entry.get("produced_tokens"),
                                "remaining": entry.get("remaining_tokens"),
                                "missing": entry.get("missing_tokens"),
                            }
                        )
                    st.write("Token replay (first 50 traces)")
                    st.dataframe(pd.DataFrame(token_rows).round(6), use_container_width=True)
                    if len(tokens) > 50:
                        st.caption(f"Showing 50 of {len(tokens):,} token replay records.")

            with st.expander("Raw JSON", expanded=False):
                st.json(summary)

            st.download_button(
                "Download Heuristics Net Image",
                data=st.session_state["heuristics_image_bytes"],
                file_name=st.session_state.get("heuristics_image_name", "heuristics.png"),
                mime="image/png",
            )

except Exception:  # pragma: no cover - defensive
    st.error("An unexpected error occurred:")
    st.text(traceback.format_exc())
    st.stop()
