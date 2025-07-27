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

## Running Tests

The project uses `pytest` for automated tests. After installing the
requirements, simply run:

```bash
pytest
```

Currently no test files are included, so the command should report `no tests
ran` until you add your own.

## License

This project is released under the [GNU GPL v3](LICENSE).
