from datetime import datetime
import streamlit as st
from pathlib import Path
import traceback

try:
    from pm4py.objects.log.importer.xes import importer as xes_importer
    from pm4py.objects.log.obj import EventLog
    from pm4py.filtering.log.timestamp import timestamp_filter
    from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
    from pm4py.visualization.heuristics_net import visualizer as hn_vis
except Exception as e:
    msg = (
        f"Failed to import PM4Py modules: {e}.\n"
        "Ensure that the `lxml` package is installed correctly. "
        "On Windows try `pip install lxml` or `conda install -c conda-forge lxml`."
    )
    st.error(msg)
    st.stop()

OUTPUT_DIR = Path(
    r"C:\Users\hugof\OneDrive - SPMS - Serviços Partilhados do Ministério da Saúde, EPE\DEP\Rastreios\RCCR\PM_mining\run_R_pm_phd\ARTIGO 3\AA_outputs"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_log(file_path: Path):
    try:
        return xes_importer.apply(str(file_path))
    except Exception as exc:
        st.error(f"Could not load XES log: {exc}")
        return None


def first_event_names(log: EventLog):
    return sorted({trace[0]['concept:name'] for trace in log if trace})


def filter_by_first_event(log: EventLog, event: str):
    if not event:
        return log
    filtered = EventLog()
    for trace in log:
        if trace and trace[0]['concept:name'] == event:
            filtered.append(trace)
    return filtered


def filter_by_dates(log: EventLog, start, end):
    if not start and not end:
        return log
    start_dt = datetime.combine(start, datetime.min.time()) if start else None
    end_dt = datetime.combine(end, datetime.max.time()) if end else None
    return timestamp_filter.apply(log, start_dt, end_dt)


def mine_heuristics_net(log: EventLog):
    return heuristics_miner.apply_heu(log)


def visualize_and_save(hnet, filename):
    gviz = hn_vis.apply(hnet)
    path = OUTPUT_DIR / filename
    hn_vis.save(gviz, str(path))
    return path


st.set_page_config(page_title="Heuristics Miner")
st.sidebar.title("CRPM – Process Mining App")
st.title("Process Mining with Heuristics Miner")

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

selected_file = file_choice
log = load_log(selected_file)
if log is None:
    st.stop()

start_events = first_event_names(log)
start_filter = st.selectbox("Filter by first event", ["All"] + start_events)
start_date = st.date_input("Start date", value=None)
end_date = st.date_input("End date", value=None)

run_btn = st.sidebar.button("Run analysis")

if run_btn:
    with st.spinner("Running Heuristics Miner..."):
        filtered = filter_by_first_event(log, start_filter if start_filter != "All" else None)
        filtered = filter_by_dates(filtered, start_date, end_date)
        hnet = mine_heuristics_net(filtered)
        img_path = visualize_and_save(hnet, f"{selected_file.stem}.png")
    st.image(img_path, caption="Heuristics Net")
    with open(img_path, "rb") as f:
        st.download_button("Download Image", f, file_name=img_path.name)
