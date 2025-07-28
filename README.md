# CRPM Streamlit App

This repository provides a Streamlit application for process mining using PM4PY. The app scans the `xes_logs` directory for available `.xes` logs and lets you mine a heuristics net from the selected file. A small example log (`running-example.xes`) is already included in this folder so you can try the app right away or replace it with your own logs.

## Setup

1. **Prerequisites**: Python 3.10 or higher and Git

2. **Clone the repository**:
   ```bash
   git clone https://github.com/HFMonteiro/CRPM.git
   cd CRPM
   ```

3. **Create and activate a Python virtual environment** (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install the package and dependencies**:
   ```bash
   # For end users
   pip install -r requirements.txt
   
   # For development (includes testing and linting tools)
   pip install -e ".[dev]"
   
   # For exact reproducible setup
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

The repository already contains `xes_logs/running-example.xes` so you can start
right away. Launch the app and use the sidebar to:

1. **Choose the log folder** – by default `xes_logs` is used. You can also
   drag-and-drop a log via the **Upload XES log** button which temporarily adds
   it to the list.
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


## Development

### Setting up the development environment

1. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Install pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### Running tests

```bash
# Run all tests
python -m unittest discover tests -v

# Run tests with coverage (if you have coverage installed)
python -m coverage run -m unittest discover tests
python -m coverage report
```

### Code quality checks

```bash
# Lint the code
flake8 .

# Format the code (if you have black installed)
black .

# Type checking (if you have mypy installed)
mypy crpm/
```

### Running the applications locally

```bash
# Basic heuristics miner app
streamlit run app.py

# Full pipeline interface
streamlit run pipeline_app.py
```

## Testing

The project includes unit tests for the core functionality. Tests are located in the `tests/` directory and can be run using Python's built-in unittest module or pytest.

## License

This project is released under the [GNU GPL v3](LICENSE).
