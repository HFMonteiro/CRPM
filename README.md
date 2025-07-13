# CRPM Streamlit App

This repository provides a Streamlit application for process mining using PM4PY. The app scans the `xes_files/original` and `xes_files/simulated` directories for available `.xes` logs and lets you perform discovery and conformance checking algorithms. Place your event logs in one of these folders before running the app.

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

## Running the App

Execute the app locally using Streamlit:

```bash
streamlit run app.py
```

## Output Directory

The generated images are saved to the folder defined by `OUTPUT_DIR` in
[app.py](app.py). By default this points to a local path. Set the `OUTPUT_DIR`
environment variable or edit the variable in the file to change where the
visualizations are written.

## License

This project is released under the [GNU GPL v3](LICENSE).
