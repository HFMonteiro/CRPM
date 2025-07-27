# app.py

import streamlit as st
import traceback
from pathlib import Path
import tempfile
import os

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

# 2) App configuration
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
ENV_OUTPUT_DIR = Path(os.environ.get("CRPM_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

st.set_page_config(page_title="Heuristics Miner")
st.sidebar.title("CRPM – Process Mining App")
st.title("Process Mining with Heuristics Miner")


def first_event_names(log):
    """Return sorted set of first event names in the log."""
    return sorted({trace[0]["concept:name"] for trace in log if trace})


# 4) Main UI + logic wrapped in its own try/except
try:
    default_logs_path = "./xes_logs"
    logs_path_str = st.sidebar.text_input(
        "Folder containing .xes files",
        default_logs_path,
    )

    output_dir_str = st.sidebar.text_input("Output directory", str(ENV_OUTPUT_DIR))
    OUTPUT_DIR = Path(output_dir_str)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    LOGS_DIR = Path(logs_path_str)

    if not LOGS_DIR.exists():
        st.sidebar.error(f"Directory not found: {LOGS_DIR.resolve()}")
        st.stop()

    xes_files = sorted(LOGS_DIR.glob("*.xes"))

    uploaded_file = st.sidebar.file_uploader("Upload XES log", type="xes")
    uploaded_path = None
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xes") as tmp:
            tmp.write(uploaded_file.getvalue())
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

    # Run the mining
    if st.sidebar.button("Run analysis"):
        with st.spinner("Running Heuristics Miner..."):
            filtered = filter_start_event(
                log,
                None if start_filter == "All" else start_filter,
            )
            filtered = filter_date_range(filtered, start_date, end_date)

            heu_net, net, im, fm = run_heuristics_miner(
                filtered, variant=Variants.CLASSIC
            )
            gviz = hn_vis.apply(heu_net)

            out_path = OUTPUT_DIR / f"{file_choice.stem}.png"
            hn_vis.save(gviz, str(out_path))

            align_res = compute_alignments(filtered, net, im, fm)
            token_res = compute_token_replay(filtered, net, im, fm)
            summary = summarize_metrics(align_res, token_res)

        st.session_state["heuristics_image"] = str(out_path)
        st.session_state["alignments"] = align_res
        st.session_state["token_replay"] = token_res
        st.session_state["summary"] = summary

        st.image(str(out_path), caption="Heuristics Net")
        st.write("Conformance summary", summary)
        with open(out_path, "rb") as f:
            st.download_button("Download Image", f, file_name=out_path.name)

except Exception:
    st.error("An unexpected error occurred:")
    st.text(traceback.format_exc())
    st.stop()
