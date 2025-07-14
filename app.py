# app.py

import streamlit as st
import traceback
from datetime import datetime
from pathlib import Path

# 1) Try PM4Py imports, but keep Streamlit available even if they fail
try:
    from pm4py.objects.log.importer.xes import importer as xes_importer
    from pm4py.objects.log.obj import EventLog
    from pm4py.algo.filtering.log.timestamp import timestamp_filter
    from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
    from pm4py.visualization.heuristics_net import visualizer as hn_vis
    from pm4py.algo.discovery.heuristics.algorithm import Variants
except Exception as e:
    st.error(
        f"Failed to import PM4Py modules: {e}\n"
        "Make sure you’ve run: pip install pm4py[all] lxml graphviz"
    )
    st.stop()

# 2) App configuration
OUTPUT_DIR = Path(
    r"C:\Users\hugof\OneDrive - SPMS - Serviços Partilhados do Ministério da Saúde, EPE\DEP\Rastreios\RCCR\PM_mining\run_R_pm_phd\ARTIGO 3\AA_outputs"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Heuristics Miner")
st.sidebar.title("CRPM – Process Mining App")
st.title("Process Mining with Heuristics Miner")

# 3) Helper functions
def load_log(file_path: Path) -> EventLog | None:
    try:
        return xes_importer.apply(str(file_path))
    except Exception as exc:
        st.error(f"Could not load XES log: {exc}")
        return None

def first_event_names(log: EventLog):
    return sorted({trace[0]["concept:name"] for trace in log if trace})

def filter_by_first_event(log: EventLog, event: str):
    if not event:
        return log
    filtered = EventLog()
    for trace in log:
        if trace and trace[0]["concept:name"] == event:
            filtered.append(trace)
    return filtered

def filter_by_dates(log: EventLog, start, end):
    if not start and not end:
        return log
    start_dt = datetime.combine(start, datetime.min.time()) if start else None
    end_dt   = datetime.combine(end,   datetime.max.time()) if end   else None
    return timestamp_filter.apply(log, start_dt, end_dt)

# 4) Main UI + logic wrapped in its own try/except
try:
    default_logs_path = "./xes_logs"
    logs_path_str = st.sidebar.text_input("Folder containing .xes files", default_logs_path)
    LOGS_DIR = Path(logs_path_str)

    if not LOGS_DIR.exists():
        st.sidebar.error(f"Directory not found: {LOGS_DIR.resolve()}")
        st.stop()

    xes_files = sorted(LOGS_DIR.glob("*.xes"))
    if not xes_files:
        st.sidebar.error("No .xes files in this folder.")
        st.stop()

    file_choice = st.sidebar.selectbox("Choose XES log", xes_files)
    log = load_log(file_choice)
    if log is None:
        st.stop()

    # First‐event filter
    start_events  = first_event_names(log)
    start_filter  = st.sidebar.selectbox("Filter by first event", ["All"] + start_events)

    # Date filter (only if requested)
    if st.sidebar.checkbox("Apply date filter"):
        start_date = st.sidebar.date_input("Start date")
        end_date   = st.sidebar.date_input("End date")
    else:
        start_date = end_date = None

    # Run the mining
    if st.sidebar.button("Run analysis"):
        with st.spinner("Running Heuristics Miner..."):
            filtered = filter_by_first_event(log, None if start_filter == "All" else start_filter)
            filtered = filter_by_dates(filtered, start_date, end_date)

            # Note the current PM4Py API:
            hnet = heuristics_miner.apply(filtered, variant=Variants.CLASSIC)
            gviz = hn_vis.apply(hnet)

            out_path = OUTPUT_DIR / f"{file_choice.stem}.png"
            hn_vis.save(gviz, str(out_path))

        st.image(str(out_path), caption="Heuristics Net")
        with open(out_path, "rb") as f:
            st.download_button("Download Image", f, file_name=out_path.name)

except Exception:
    st.error("An unexpected error occurred:")
    st.text(traceback.format_exc())
    st.stop()
