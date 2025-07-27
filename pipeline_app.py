import streamlit as st
from pathlib import Path
from datetime import date

from crpm import pipeline

st.set_page_config(page_title="CRPM Full Pipeline")
st.title("Process Mining Pipeline")

# Step 1 - CSV load
csv_path = st.text_input("Path to CSV file")
case_col = st.text_input("Case column", "case_id")
activity_col = st.text_input("Activity column", "activity_id")
timestamp_col = st.text_input("Timestamp column", "timestamp")

if st.button("Load CSV"):
    if not csv_path:
        st.error("Please provide the CSV path")
    else:
        df = pipeline.load_csv(Path(csv_path))
        st.session_state["df"] = df
        st.write(df.head())

# Step 2 - convert to event log
if "df" in st.session_state:
    if st.button("Convert to Event Log"):
        log = pipeline.csv_to_event_log(
            st.session_state["df"], case_col, activity_col, timestamp_col
        )
        st.session_state["log"] = log
        st.success(f"Log with {len(log)} traces created")

# Step 3 - split by date
if "log" in st.session_state:
    cutoff = st.date_input("Cutoff date", value=date(2024, 1, 1))
    if st.button("Split Log"):
        before, after = pipeline.split_by_date(st.session_state["log"], cutoff)
        st.session_state["train"] = before
        st.session_state["test"] = after
        st.write(f"Train traces: {len(before)} | Test traces: {len(after)}")

# Step 4 - model discovery
if "train" in st.session_state:
    algorithm = st.selectbox("Discovery algorithm", ["heuristics", "inductive"])
    if st.button("Discover Model"):
        if algorithm == "heuristics":
            _, net, im, fm = pipeline.discover_heuristics_net(st.session_state["train"])
        else:
            net, im, fm = pipeline.discover_petri_inductive(st.session_state["train"])
        st.session_state["model"] = (net, im, fm)
        st.success("Model discovered")

# Step 5 - conformance
if "model" in st.session_state and "test" in st.session_state:
    if st.button("Evaluate Conformance"):
        net, im, fm = st.session_state["model"]
        a_fitness = pipeline.alignment_fitness(st.session_state["test"], net, im, fm)
        t_fitness = pipeline.token_replay_fitness(st.session_state["test"], net, im, fm)
        prec = pipeline.precision(st.session_state["test"], net, im, fm)
        st.write({
            "alignment_fitness": a_fitness,
            "token_replay_fitness": t_fitness,
            "precision": prec,
        })
