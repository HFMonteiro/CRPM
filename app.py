# app.py

import streamlit as st
import traceback
from pathlib import Path
import tempfile
import os
import pandas as pd
import base64

# 1) Try PM4Py imports, but keep Streamlit available even if they fail
try:
    from pm4py.visualization.heuristics_net import visualizer as hn_vis
    from pm4py.algo.discovery.heuristics.algorithm import Variants
except Exception as e:
    st.error(
        f"Failed to import PM4Py modules: {e}\n"
        "Make sure you’ve run: pip install pm4py[all] lxml graphviz"
    )
    st.stop()

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
from pm4py.objects.petri_net.importer.importer import apply as pnml_importer

# 2) App configuration
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
ENV_OUTPUT_DIR = Path(os.environ.get("CRPM_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

st.set_page_config(
    page_title="Heuristics Miner",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.sidebar.title("CRPM – Process Mining App")
st.title("Process Mining with Heuristics Miner")


def first_event_names(log):
    """Return sorted set of first event names in the log."""
    return sorted({trace[0]["concept:name"] for trace in log if trace})


# 4) Main UI + logic wrapped in its own try/except
try:
    # Source selection: XES (folder) or CSV (upload)
    source_type = st.sidebar.radio("Input source", ["XES", "CSV"], horizontal=True)

    output_dir_str = st.sidebar.text_input("Output directory", str(ENV_OUTPUT_DIR))
    OUTPUT_DIR = Path(output_dir_str)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Upload size guard (bytes) - keep aligned with your frontend limit
    MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB

    log = None
    file_choice = None

    if source_type == "XES":
        default_logs_path = "./xes_logs"
        logs_path_str = st.sidebar.text_input(
            "Folder containing .xes files",
            default_logs_path,
        )

        LOGS_DIR = Path(logs_path_str)

        if not LOGS_DIR.exists():
            st.sidebar.error(f"Directory not found: {LOGS_DIR.resolve()}")
            st.stop()

        xes_files = sorted(LOGS_DIR.glob("*.xes"))

        uploaded_file = st.sidebar.file_uploader("Upload XES log", type="xes")
        uploaded_path = None
        if uploaded_file is not None:
            # quick size check
            b = uploaded_file.getvalue()
            if len(b) > MAX_UPLOAD_BYTES:
                st.sidebar.error(f"Upload too large ({len(b)/(1024*1024):.1f} MB). Max allowed: {MAX_UPLOAD_BYTES/(1024*1024):.0f} MB.")
                st.stop()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xes") as tmp:
                tmp.write(b)
                uploaded_path = Path(tmp.name)
            xes_files = [uploaded_path] + xes_files

        if not xes_files:
            st.sidebar.info("Please upload a XES log to continue.")
            st.stop()

        def _fmt(p: Path):
            if uploaded_path is not None and p == uploaded_path:
                return f"{uploaded_file.name} (uploaded)"
            return p.name

        file_choice = st.sidebar.selectbox("Choose XES log", xes_files, format_func=_fmt)
        log = load_log(file_choice)
        if log is None:
            st.stop()
        input_name = file_choice.name

    else:
        csv_file = st.sidebar.file_uploader("Upload CSV log", type=["csv"])
        if csv_file is None:
            st.sidebar.info("Upload a CSV file to continue.")
            st.stop()

        # size check
        csv_bytes = csv_file.getvalue()
        if len(csv_bytes) > MAX_UPLOAD_BYTES:
            st.sidebar.error(f"CSV upload too large ({len(csv_bytes)/(1024*1024):.1f} MB). Max allowed: {MAX_UPLOAD_BYTES/(1024*1024):.0f} MB.")
            st.stop()

        df = pd.read_csv(csv_file)
        st.subheader("CSV preview")
        st.dataframe(df.head(50), use_container_width=True)

        cols = list(df.columns)
        st.markdown("Map CSV columns to event log fields:")
        case_col = st.selectbox("Case ID column", cols, index=0 if cols else None)
        activity_col = st.selectbox("Activity column", cols, index=1 if len(cols) > 1 else 0)
        timestamp_col = st.selectbox("Timestamp column", cols, index=2 if len(cols) > 2 else 0)

        log = csv_to_event_log(df, case_col, activity_col, timestamp_col)
        input_name = getattr(csv_file, "name", "uploaded.csv")

    # First‐event filter
    start_events = first_event_names(log)
    start_filter = st.sidebar.selectbox(
        "Filter by first event",
        ["All"] + start_events,
    )

    # Date filter (only if requested)
    if st.sidebar.checkbox("Apply date filter"):
        start_date = st.sidebar.date_input("Start date")
        end_date = st.sidebar.date_input("End date")
    else:
        start_date = end_date = None

    # Events table preview
    with st.expander("Preview events table", expanded=False):
        try:
            rows = []
            max_rows = 200
            count = 0
            for trace in log:
                case_id = None
                try:
                    case_id = trace.attributes.get("concept:name")
                except Exception:
                    case_id = None
                for ev in trace:
                    rows.append({
                        "case:concept:name": case_id,
                        "concept:name": ev.get("concept:name"),
                        "time:timestamp": ev.get("time:timestamp"),
                    })
                    count += 1
                    if count >= max_rows:
                        break
                if count >= max_rows:
                    break
            if rows:
                df_preview = pd.DataFrame(rows)
                st.dataframe(df_preview, use_container_width=True)
            else:
                st.caption("No events to preview.")
        except Exception:
            st.caption("Could not build preview table.")

    # Run the mining
    # Conformance model selector
    model_choice = st.sidebar.selectbox("Conformance model", ["heuristics", "inductive", "uploaded PNML"])
    pnml_file = None
    if model_choice == "uploaded PNML":
        pnml_file = st.sidebar.file_uploader("Upload PNML for conformance", type=["pnml", "xml"])
        if pnml_file is not None:
            pnml_bytes = pnml_file.getvalue()
            if len(pnml_bytes) > MAX_UPLOAD_BYTES:
                st.sidebar.error(f"PNML upload too large ({len(pnml_bytes)/(1024*1024):.1f} MB). Max allowed: {MAX_UPLOAD_BYTES/(1024*1024):.0f} MB.")
                st.stop()

    if st.sidebar.button("Run analysis"):
        with st.spinner("Running Heuristics Miner..."):
            filtered = filter_start_event(
                log,
                None if start_filter == "All" else start_filter,
            )
            filtered = filter_date_range(filtered, start_date, end_date)

            # Always compute heuristics net for visualization
            heu_net, heur_net_net, heur_net_im, heur_net_fm = run_heuristics_miner(
                filtered, variant=Variants.CLASSIC
            )
            gviz = hn_vis.apply(heu_net)

            # Decide which Petri net to use for conformance
            if model_choice == "heuristics":
                net, im, fm = heur_net_net, heur_net_im, heur_net_fm
            elif model_choice == "inductive":
                try:
                    net, im, fm = discover_petri_inductive(filtered)
                except Exception as e:
                    st.error(f"Inductive miner failed: {e}")
                    st.stop()
            else:  # uploaded PNML
                if pnml_file is None:
                    st.error("Please upload a PNML file for conformance.")
                    st.stop()
                try:
                    # write to tmp and import
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pnml") as tpn:
                        tpn.write(pnml_file.getvalue())
                        tpn_path = Path(tpn.name)
                    net, im, fm = pnml_importer(str(tpn_path))
                except Exception as e:
                    st.error(f"PNML import failed: {e}")
                    st.stop()

            # derive output base name from input_name (XES or CSV)
            base_stem = Path(input_name).stem if 'input_name' in locals() and input_name else "heuristics_net"
            out_path = OUTPUT_DIR / f"{base_stem}.png"
            hn_vis.save(gviz, str(out_path))

            align_res = compute_alignments(filtered, net, im, fm)
            token_res = compute_token_replay(filtered, net, im, fm)
            summary = summarize_metrics(align_res, token_res)

        st.session_state["heuristics_image"] = str(out_path)
        st.session_state["alignments"] = align_res
        st.session_state["token_replay"] = token_res
        st.session_state["summary"] = summary

        # Layout: graph boxed in the left/main area, conformance KPIs + table on the right
        try:
            def summary_to_df(summary_dict):
                groups = list(summary_dict.keys())
                metrics = set()
                for g in groups:
                    inner = summary_dict.get(g) or {}
                    metrics.update(inner.keys())
                metrics = sorted(metrics)
                data = {g: [summary_dict.get(g, {}).get(m) for m in metrics] for g in groups}
                df = pd.DataFrame(data, index=metrics)
                # Convert numeric-like values to numbers for nicer display
                for col in df.columns:
                    try:
                        df[col] = pd.to_numeric(df[col])
                    except (ValueError, TypeError):
                        pass
                return df

            df_summary = summary_to_df(summary)

            # Desktop-optimized layout: 2:1 ratio (graph : stats)
            left_col, right_col = st.columns([2, 1])

            # Boxed graph in the left (larger for desktop)
            with left_col:
                try:
                    img_bytes = open(out_path, "rb").read()
                    b64 = base64.b64encode(img_bytes).decode()
                    img_tag = f'<img src="data:image/png;base64,{b64}" style="width:100%; height:auto; display:block; margin-left:auto; margin-right:auto;" />'
                    st.markdown(
                        f'<div style="border:2px solid #555; padding:16px; border-radius:8px; background-color:#0a0a0a; min-height:600px; display:flex; align-items:center; justify-content:center;">{img_tag}</div>',
                        unsafe_allow_html=True,
                    )
                except Exception:
                    # fallback to st.image
                    st.image(str(out_path), caption="Heuristics Net", use_column_width=True)

            # KPIs and conformance table on the right
            with right_col:
                st.subheader("Conformance summary")

                # KPI cards for quick glance (pick some common metrics if present)
                try:
                    kpi_cols = st.columns(1)
                    def safe_get(g, k):
                        return summary.get(g, {}).get(k)

                    v1 = safe_get("alignment_fitness", "log_fitness")
                    v2 = safe_get("token_fitness", "log_fitness")
                    v3 = safe_get("alignment_fitness", "percentage_of_fitting_traces")

                    st.metric("Alignment log_fitness", f"{v1:.6f}" if isinstance(v1, (int, float)) else v1)
                    st.metric("Token log_fitness", f"{v2:.6f}" if isinstance(v2, (int, float)) else v2)
                    st.metric("% fitting traces", f"{v3}" if v3 is not None else "-")
                except Exception:
                    pass

                transpose = st.checkbox("Transpose table (groups x metrics)", value=False)
                display_df = df_summary.T if transpose else df_summary
                st.dataframe(display_df.round(6), use_container_width=True)

                try:
                    csv_bytes = display_df.to_csv().encode()
                    st.download_button("Download conformance CSV", csv_bytes, file_name="conformance_summary.csv", mime="text/csv")
                except Exception:
                    pass

                with st.expander("Raw JSON", expanded=False):
                    st.json(summary)
        except Exception:
            st.subheader("Conformance summary")
            st.json(summary)
        with open(out_path, "rb") as f:
            st.download_button("Download Image", f, file_name=out_path.name)

except Exception:
    st.error("An unexpected error occurred:")
    st.text(traceback.format_exc())
    st.stop()
