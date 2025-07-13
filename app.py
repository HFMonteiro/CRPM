import os
from datetime import datetime

import streamlit as st
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.obj import EventLog
from pm4py.algo.discovery.alpha import algorithm as alpha_miner
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.filtering.log.attributes import attributes_filter
from pm4py.filtering.log.timestamp import timestamp_filter
from pm4py.visualization.petri_net import visualizer as pn_vis
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay

# Directories containing XES logs
LOG_DIRS = [
    os.path.join('.', 'xes_files', 'original'),
    os.path.join('.', 'xes_files', 'simulated'),
]

# Output directory
OUTPUT_DIR = r"C:\Users\hugof\OneDrive - SPMS - Serviços Partilhados do Ministério da Saúde, EPE\DEP\Rastreios\RCCR\PM_mining\run_R_pm_phd\ARTIGO 3\AA_outputs"


def ensure_output_dir() -> None:
    """Create the output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


@st.cache_data(show_spinner=False)
def scan_xes_files(dir_mtimes):
    """Return a dictionary mapping display names to file paths."""
    files = {}
    for d in LOG_DIRS:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if fname.lower().endswith('.xes'):
                path = os.path.join(d, fname)
                files[fname] = path
    return files


@st.cache_data(show_spinner=False)
def load_log(path, mtime):
    """Load an XES event log."""
    try:
        log = xes_importer.apply(path)
        return log
    except Exception as exc:
        st.error(f"Failed to load log: {exc}")
        return None


def filter_log(log, activities, start, end):
    """Apply filters to the log if provided."""
    if activities:
        log = attributes_filter.apply_events(log, activities, parameters={
            attributes_filter.Parameters.ATTRIBUTE_KEY: "concept:name",
        })
    if start or end:
        start_dt = datetime.combine(start, datetime.min.time()) if start else None
        end_dt = datetime.combine(end, datetime.max.time()) if end else None
        log = timestamp_filter.apply(log, start_dt, end_dt)
    return log


@st.cache_data(show_spinner=False, hash_funcs={EventLog: lambda l: id(l)})
def discover_model(log, method, noise_threshold=0.0):
    """Discover a Petri net from the log using the selected method."""
    if method == "Inductive Miner":
        net, im, fm = inductive_miner.apply(log, parameters={"noise_threshold": noise_threshold})
    else:
        net, im, fm = alpha_miner.apply(log)
    return net, im, fm


def visualize_petri_net(net, im, fm, name):
    """Save and display the Petri net visualization."""
    gv = pn_vis.apply(net, im, fm)
    ensure_output_dir()
    out_path = os.path.join(OUTPUT_DIR, f"{name}.png")
    pn_vis.save(gv, out_path)
    st.image(out_path, caption=f"{name} Petri net")


def check_conformance(log, net, im, fm):
    """Run token-based replay and show fitness."""
    replayed_traces = token_replay.apply(log, net, im, fm)
    fitness = sum(t["trace_fitness"] for t in replayed_traces) / len(replayed_traces)
    st.write(f"Token-based replay fitness: {fitness:.3f}")


# ---------------------------- Streamlit UI ----------------------------

st.set_page_config(page_title="CRPM Process Mining")
st.title("CRPM Process Mining App")

dir_mtimes = tuple(os.path.getmtime(d) if os.path.isdir(d) else 0 for d in LOG_DIRS)
files = scan_xes_files(dir_mtimes)

if not files:
    st.warning("No .xes files found in the configured directories.")
    st.stop()

selected_file = st.sidebar.selectbox("Select XES log", list(files.keys()))
algorithm = st.sidebar.selectbox("Discovery algorithm", ["Inductive Miner", "Alpha Miner"])

noise = 0.0
if algorithm == "Inductive Miner":
    noise = st.sidebar.slider("Noise threshold", 0.0, 1.0, 0.0, 0.05)

log_path = files[selected_file]
log_mtime = os.path.getmtime(log_path)
log = load_log(log_path, log_mtime)
if log is None:
    st.stop()

# Activity filter options
activities = sorted({ev["concept:name"] for trace in log for ev in trace})
selected_acts = st.sidebar.multiselect("Filter activities", activities)

start_date = st.sidebar.date_input("Start date", value=None)
end_date = st.sidebar.date_input("End date", value=None)

filtered_log = filter_log(log, selected_acts, start_date, end_date)

if st.sidebar.button("Run Discovery"):
    with st.spinner("Running discovery algorithm..."):
        net, im, fm = discover_model(filtered_log, algorithm, noise)
    visualize_petri_net(net, im, fm, "discovered_model")
    check_conformance(filtered_log, net, im, fm)
