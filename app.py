import os
from datetime import datetime
import streamlit as st

try:
    from pm4py.objects.log.importer.xes import importer as xes_importer
    from pm4py.objects.log.obj import EventLog
    from pm4py.filtering.log.timestamp import timestamp_filter
    from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
    from pm4py.visualization.heuristics_net import visualizer as hn_vis
except Exception as e:
    st.error(f"Failed to import PM4Py modules: {e}")
    st.stop()

LOG_DIR = os.environ.get("LOG_DIR", os.path.join('.', 'xes_logs'))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join('.', 'outputs'))
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def list_xes_files():
    return [f for f in os.listdir(LOG_DIR) if f.lower().endswith('.xes')]


def load_log(filename):
    try:
        return xes_importer.apply(os.path.join(LOG_DIR, filename))
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
    path = os.path.join(OUTPUT_DIR, filename)
    hn_vis.save(gviz, path)
    return path


st.set_page_config(page_title="Heuristics Miner")
st.title("Process Mining with Heuristics Miner")

files = list_xes_files()
if not files:
    st.warning(f"No .xes files found in {LOG_DIR}")
    st.stop()

selected_file = st.selectbox("Choose log file", files)
log = load_log(selected_file)
if log is None:
    st.stop()

start_events = first_event_names(log)
start_filter = st.selectbox("Filter by first event", ["All"] + start_events)
start_date = st.date_input("Start date", value=None)
end_date = st.date_input("End date", value=None)

if st.button("Run Heuristics Miner"):
    with st.spinner("Running Heuristics Miner..."):
        filtered = filter_by_first_event(log, start_filter if start_filter != "All" else None)
        filtered = filter_by_dates(filtered, start_date, end_date)
        hnet = mine_heuristics_net(filtered)
        img_path = visualize_and_save(hnet, f"{os.path.splitext(selected_file)[0]}.png")
    st.image(img_path, caption="Heuristics Net")
    with open(img_path, "rb") as f:
        st.download_button("Download Image", f, file_name=os.path.basename(img_path))
