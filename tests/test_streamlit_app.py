from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_app_navigation_renders_each_workspace_page() -> None:
    app = AppTest.from_file("app.py")
    app.run(timeout=45)

    pages = next(radio for radio in app.radio if radio.label == "Page").options
    for page in pages:
        page_selector = next(radio for radio in app.radio if radio.label == "Page")
        page_selector.set_value(page).run(timeout=45)
        assert not app.exception, f"{page} failed to render: {app.exception}"
