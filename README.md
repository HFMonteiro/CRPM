# CRPM Streamlit App

This repository provides a Streamlit application for process mining using PM4PY. The app scans the `xes_logs` directory for available `.xes` logs and lets you mine a heuristics net from the selected file. Place your event logs in this folder before running the app.

## Setup

1. Create and activate a Python virtual environment (optional but recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install requirements:
   ```bash
   pip install -r requirements.txt
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

The generated images are saved to the folder defined by `OUTPUT_DIR` in
[app.py](app.py). By default this points to a local path. Set the `OUTPUT_DIR`
environment variable or edit the variable in the file to change where the
visualizations are written.

## License

This project is released under the [GNU GPL v3](LICENSE).
