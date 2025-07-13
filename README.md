# CRPM Streamlit App

This repository provides a Streamlit application for process mining using PM4PY. The app scans the `xes_files/original` and `xes_files/simulated` directories for available `.xes` logs and lets you perform discovery and conformance checking algorithms.

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

Generated files are saved under the `outputs` directory by default. You can
customize the location by setting the `CRPM_OUTPUT_DIR` environment variable
before running the app.

## License

This project is released under the [GNU GPL v3](LICENSE).
