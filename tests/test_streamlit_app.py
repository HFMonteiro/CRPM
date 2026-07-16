from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_app_navigation_renders_each_workspace_page() -> None:
    app = AppTest.from_file("app.py")
    app.run(timeout=45)

    workspace_pages = {
        "Explore": ("Overview", "Discovery", "DFG Visualizations", "Variant Analysis"),
        "Conformance": ("Conformance Analytics",),
        "Performance": ("Operational Flow", "Process Performance"),
        "Models": ("Model Comparison",),
    }
    for workspace, pages in workspace_pages.items():
        workspace_selector = next(radio for radio in app.radio if radio.label == "Workspace")
        workspace_selector.set_value(workspace).run(timeout=45)
        assert not app.exception, f"{workspace} failed to render: {app.exception}"

        if len(pages) == 1:
            continue
        for page in pages:
            page_selector = next(radio for radio in app.radio if radio.label == "View")
            page_selector.set_value(page).run(timeout=45)
            assert not app.exception, f"{page} failed to render: {app.exception}"
