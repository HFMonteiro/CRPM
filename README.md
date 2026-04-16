# CRPM

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

CRPM is a process mining workbench for colorectal cancer screening pathways, built with [PM4Py](https://pm4py.fit.fraunhofer.de/) and [Streamlit](https://streamlit.io/). It is designed for research and operational monitoring teams who need discovery, model comparison, conformance analysis, DFG views, variant analysis, and timing-focused process diagnostics in one local application.

Developed in the context of PhD research at the **Faculty of Medicine, University of Porto (FMUP)**. Author: [Hugo Monteiro](https://hfmonteiro.com).

> **Legal notice** - For research and operational monitoring support only. Not a substitute for clinical judgment or institutional decision-making.

## Screenshots

![CRPM Overview](docs/screenshots/overview.png)

![CRPM Conformance Analytics](docs/screenshots/conformance-board.png)

![CRPM Operational Flow](docs/screenshots/operational-flow.png)

## Quick Start

```bash
git clone https://github.com/HFMonteiro/CRPM.git
cd CRPM

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

pip install .
python -m crpm.preflight
streamlit run app.py
```

`app.py` is the supported entrypoint.

## What CRPM Includes

- `Overview` for executive summary, run posture, and reading order
- `Discovery` and `Model Comparison` for Petri net discovery and quality tradeoffs
- `Operational Flow`, `DFG Visualizations`, and `Process Performance` for pathway movement, bottlenecks, and timing
- `Variant Analysis` for dominant and rare trace structure
- `Conformance Analytics` for token-based diagnostics, SVG workflow boards, and interactive workflow exploration
- local XES and CSV ingestion through the Streamlit shell

## Sample Data

The public sample bundle lives in `examples/`:

- `running-example.xes` - small didactic baseline log
- `screening_conformance_demo.xes` - main synthetic CRC screening demo log
- `screening_conformance_demo.csv` - event-level CSV companion for onboarding and validation
- `idealized_event_log.xes` and `idealized_petri_net.pnml` - idealized reference artefacts for conformance-oriented checks

The bundled `screening_conformance_demo.*` files are **synthetic** and intentionally shaped to expose dominant and rare pathways, deviations, PRE/POST drift, and timing bottlenecks.

## Requirements

- Python `3.10+`
- [Graphviz](https://graphviz.org/download/) available on `PATH` for DFG and Petri net rendering

```bash
# Ubuntu / Debian
sudo apt-get install -y graphviz

# macOS
brew install graphviz
```

On Windows, install Graphviz from the official installer and add `dot` to `PATH`.

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check crpm tests
```

## Citation

```bibtex
@software{monteiro2026crpm,
  author    = {Monteiro, Hugo F.},
  title     = {{CRPM}: Colorectal Cancer Screening Process Mining Workbench},
  year      = {2026},
  url       = {https://github.com/HFMonteiro/CRPM},
  license   = {GPL-3.0}
}
```

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
