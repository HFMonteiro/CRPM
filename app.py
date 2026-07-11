"""Canonical Streamlit entrypoint for the CRPM screening workbench."""

from __future__ import annotations

import streamlit as st

from crpm.runtime_compat import install_pm4py_import_guard

install_pm4py_import_guard()

from crpm.preflight import format_preflight_messages, validate_runtime_environment


def main() -> None:
    """Run the app only after the runtime preflight succeeds."""
    report = validate_runtime_environment()
    if not report.ok:
        st.set_page_config(page_title="CRPM - Dependency Check", layout="wide")
        st.error("CRPM cannot start until the runtime preflight passes.")
        for line in format_preflight_messages(report):
            st.markdown(line)
        st.info(
            'Install the package with `pip install .` for runtime use, including the interactive workflow dependency, or `pip install -e ".[dev]"` for development, then restart the app.'
        )
        st.stop()

    from crpm.app_shell import render_app

    render_app()


if __name__ == "__main__":
    main()
