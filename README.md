# CRPM Streamlit App

**Robust, Codespaces-friendly process mining app for desktop browsers.**

**Key workflow:**
- For large XES files, copy them to `xes_logs/` (or any folder), click Refresh, and select from the dropdown. This bypasses browser/proxy upload limits (413 errors).
- For remote files, use the URL fetch option in the sidebar (downloads server-side, no proxy limit).
- The 'Browse files' button is available for convenience, but may fail with 413 if your proxy is strict (e.g., Codespaces, nginx).

**If you see '413 Request Entity Too Large':**
- Use the folder or URL fetch options instead of browser upload.
- This is a Codespaces/proxy limitation, not a bug in the app.

All analytics, layout, and export features remain. Desktop 16:9 layout, analytics tabs, and conformance model selector are preserved.

---

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

If your shell cannot find the `streamlit` command (common when it’s installed with `--user`), you can run it via Python, which bypasses PATH issues:

```bash
python -m streamlit run app.py
```

The repository already contains `xes_logs/running-example.xes` so you can start
right away. Launch the app and use the sidebar to:

1. **Choose the log folder** – by default `xes_logs` is used. For large files, copy them here using VS Code's file explorer or a terminal, then click Refresh files. You can also use the **Browse files** button (may hit 413) or the URL fetch option.
2. **Set the output directory** – either via the `CRPM_OUTPUT_DIR` environment
   variable or directly in the "Output directory" text box. Images and metrics
   will be written there when you run the miner.
3. **Select the log** to analyse. You may optionally filter by the first event
   or restrict the date range.
4. Click **Run analysis** to mine the heuristics net and compute conformance
   metrics. The discovered model is displayed in the main page together with a
   summary of the alignment and token-based fitness values. Use **Download
   Image** to save the visualization.
   Values close to `1.0` in these metrics indicate good replay fitness.

You can experiment with other Heuristics Miner variants by editing the
`variant` argument in `run_heuristics_miner` inside `crpm/conformance.py`.

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

#### Graphviz executables not found

If you see an error like:

```
pydotplus.graphviz.InvocationException: GraphViz's executables not found
```

install the Graphviz system package so PM4Py/pydotplus can find the `dot` executable:

```bash
sudo apt-get update -y && sudo apt-get install -y graphviz
```

Then restart the app and run the analysis again.

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
