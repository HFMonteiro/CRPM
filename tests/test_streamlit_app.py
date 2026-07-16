from __future__ import annotations

from streamlit.testing.v1 import AppTest

from crpm.app_shell import ADVANCED_PAGES, WORKSPACE_PAGES


def test_app_navigation_renders_each_workspace_page() -> None:
    app = AppTest.from_file("app.py")
    app.run(timeout=45)

    for workspace, pages in WORKSPACE_PAGES.items():
        workspace_selector = next(radio for radio in app.radio if radio.label == "Workspace")
        workspace_selector.set_value(workspace).run(timeout=45)
        assert not app.exception, f"{workspace} failed to render: {app.exception}"

        for page in pages:
            if len(pages) == 1:
                break
            page_selector = next(radio for radio in app.radio if radio.label == "View")
            page_selector.set_value(page).run(timeout=45)
            assert not app.exception, f"{page} failed to render: {app.exception}"

        for page in ADVANCED_PAGES.get(workspace, ()):
            advanced_button = next(button for button in app.sidebar.button if button.label == page)
            advanced_button.click().run(timeout=45)
            assert not app.exception, f"{page} failed to render: {app.exception}"
