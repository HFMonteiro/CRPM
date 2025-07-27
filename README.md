# CRPM Streamlit App

This repository provides a Streamlit application for process mining using PM4PY. The app scans the `xes_logs` directory for available `.xes` logs and lets you mine a heuristics net from the selected file. A small example log (`running-example.xes`) is already included in this folder so you can try the app right away or replace it with your own logs.

## Setup

1. Create and activate a Python virtual environment (optional but recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install requirements (for a reproducible setup you may also install from the
   accompanying `requirements.lock` file):
   ```bash
   pip install -r requirements.txt
   # or for the exact versions used during development
   pip install -r requirements.lock
   ```

### Conda environment

Alternatively, you can create the environment with conda:

```bash
conda create -n pm_env python=3.10 -y
conda activate pm_env
pip install streamlit pm4py plotly pandas
conda install -c conda-forge cvxopt lxml -y
```

## Running the App

Execute the app locally using Streamlit:

```bash
streamlit run app.py
streamlit run pipeline_app.py  # full pipeline interface
```

The repository already contains `xes_logs/running-example.xes` as a small
sample. After starting the app, pick this log from the sidebar to view the
generated heuristics net immediately.

### Troubleshooting

If you encounter an error similar to:

```
Failed to import PM4Py modules: cannot import name 'etree' from 'lxml'
```

the `lxml` package might not be installed correctly. Install it manually with:

```bash
pip install lxml
```

or via conda:

```bash
conda install -c conda-forge lxml
```

After installation restart the app.

## Output Directory

The generated images are saved to an `outputs` folder located next to
`app.py` by default. Set the `CRPM_OUTPUT_DIR` environment variable or edit the
"Output directory" field in the sidebar to store the visualizations elsewhere.

### Updating dependency versions

The versions pinned in `requirements.txt` reflect combinations tested with this
project. To upgrade them:

```bash
pip install -U -r requirements.txt
pip freeze > requirements.lock
```

Commit both files so others can recreate the updated environment.

## Process Mining Pipeline

The notebook `CONFORMANCE_fullcode_may_2025.ipynb` was refactored into
reusable functions under `crpm.pipeline`. They cover CSV loading,
conversion to an event log, temporal splitting and model discovery using
both the Heuristics Miner and the Inductive Miner. Conformance metrics
such as alignments, token replay and precision can also be computed.

Basic usage from Python:

```python
from datetime import date
from pathlib import Path
from crpm.pipeline import (
    load_csv,
    csv_to_event_log,
    split_by_date,
    discover_heuristics_net,
    alignment_fitness,
)

df = load_csv(Path("my_data.csv"))
log = csv_to_event_log(df, "case_id", "activity_id", "timestamp")
train, test = split_by_date(log, date(2024, 1, 1))

_, net, im, fm = discover_heuristics_net(train)
fitness = alignment_fitness(test, net, im, fm)
```

All functions accept `pathlib.Path` objects for paths making them
cross‑platform and ready to be triggered from a Streamlit interface.

## License

This project is released under the [GNU GPL v3](LICENSE).
