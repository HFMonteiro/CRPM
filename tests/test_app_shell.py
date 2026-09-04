from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from crpm.app_runtime import LoadedLog, compute_analysis_signature
from crpm.app_shell import (
    ADVANCED_PAGES,
    WORKSPACE_PAGES,
    _default_xes_index,
    _render_analysis_controls,
    _render_workspace_navigation,
)
from crpm.app_state import get_crpm_state


def test_default_xes_index_prefers_full_screening_demo_for_fresh_session() -> None:
    options = [
        "examples/idealized_event_log.xes",
        "examples/screening_conformance_demo.xes",
    ]

    assert _default_xes_index(options, None) == 1


def test_default_xes_index_preserves_existing_selection() -> None:
    options = [
        "examples/idealized_event_log.xes",
        "examples/screening_conformance_demo.xes",
    ]

    assert _default_xes_index(options, options[0]) == 0


class _DummySidebar:
    def __init__(self, *, button_result: bool = False, checkbox_values: dict[str, bool] | None = None) -> None:
        self.button_result = button_result
        self.checkbox_values = checkbox_values or {}
        self.info_messages = []
        self.visible_order = []

    def markdown(self, *args, **kwargs):
        self.visible_order.append(("markdown", args[0] if args else ""))
        return None

    def success(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        self.info_messages.append(args[0] if args else "")
        return None

    def error(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def caption(self, *args, **kwargs):
        self.visible_order.append(("caption", args[0] if args else ""))
        return None

    def radio(self, label, options, index=0, key=None, **kwargs):
        return options[index]

    def text_input(self, label, value="", key=None, **kwargs):
        return value

    def file_uploader(self, *args, **kwargs):
        return None

    def selectbox(self, label, options, index=0, key=None, format_func=None, **kwargs):
        return options[index]

    def checkbox(self, label, value=False, key=None, **kwargs):
        self.visible_order.append(("checkbox", label))
        return self.checkbox_values.get(key, value)

    def date_input(self, label, value=None, key=None, **kwargs):
        return value

    def multiselect(self, label, options, default=None, key=None, **kwargs):
        return list(default or [])

    def number_input(self, label, min_value=None, max_value=None, value=0, step=1, key=None, **kwargs):
        return value

    def button(self, label, type="secondary", use_container_width=False, key=None, **kwargs):
        self.visible_order.append(("button", label))
        return self.button_result

    def expander(self, *args, **kwargs):
        self.visible_order.append(("expander", args[0] if args else ""))
        return _DummyContext(self)

    def empty(self):
        index = len(self.visible_order)
        self.visible_order.append(("empty", ""))
        return _DummySidebarSlot(self, index)


class _DummySidebarSlot:
    def __init__(self, sidebar: _DummySidebar, index: int) -> None:
        self.sidebar = sidebar
        self.index = index

    def button(self, label, type="secondary", use_container_width=False, key=None, **kwargs):
        self.sidebar.visible_order[self.index] = ("button", label)
        return self.sidebar.button_result


class _DummyContext:
    def __init__(self, sidebar: _DummySidebar | None = None) -> None:
        self.sidebar = sidebar

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def caption(self, *args, **kwargs):
        if self.sidebar is not None:
            return self.sidebar.caption(*args, **kwargs)
        return None

    def button(self, *args, **kwargs):
        if self.sidebar is not None:
            return self.sidebar.button(*args, **kwargs)
        return False

    def markdown(self, *args, **kwargs):
        if self.sidebar is not None:
            return self.sidebar.markdown(*args, **kwargs)
        return None

    def radio(self, *args, **kwargs):
        return self.sidebar.radio(*args, **kwargs)

    def text_input(self, *args, **kwargs):
        return self.sidebar.text_input(*args, **kwargs)

    def file_uploader(self, *args, **kwargs):
        return self.sidebar.file_uploader(*args, **kwargs)

    def selectbox(self, *args, **kwargs):
        return self.sidebar.selectbox(*args, **kwargs)

    def checkbox(self, *args, **kwargs):
        return self.sidebar.checkbox(*args, **kwargs)

    def date_input(self, *args, **kwargs):
        return self.sidebar.date_input(*args, **kwargs)

    def multiselect(self, *args, **kwargs):
        return self.sidebar.multiselect(*args, **kwargs)

    def number_input(self, *args, **kwargs):
        return self.sidebar.number_input(*args, **kwargs)


def _dummy_streamlit(sidebar: _DummySidebar, session_state: dict) -> SimpleNamespace:
    return SimpleNamespace(
        sidebar=sidebar,
        session_state=session_state,
        caption=lambda *args, **kwargs: None,
        markdown=lambda *args, **kwargs: None,
        radio=lambda label, options, **kwargs: options[0],
        text_input=sidebar.text_input,
        checkbox=sidebar.checkbox,
        selectbox=sidebar.selectbox,
        date_input=sidebar.date_input,
        multiselect=sidebar.multiselect,
        number_input=sidebar.number_input,
    )


def test_workspace_navigation_keeps_advanced_surfaces_secondary(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    sidebar = _DummySidebar()
    session_state = {"crpm_preview_page": "DFG Visualizations"}
    monkeypatch.setattr(app_shell, "st", _dummy_streamlit(sidebar, session_state))

    page = _render_workspace_navigation()

    assert set(WORKSPACE_PAGES["Explore"]).isdisjoint(ADVANCED_PAGES["Explore"])
    assert page == "DFG Visualizations"
    assert ("expander", "Advanced surfaces") in sidebar.visible_order


def _loaded_log() -> LoadedLog:
    return LoadedLog(
        log=[[{"concept:name": "Start", "time:timestamp": datetime(2024, 1, 1)}]],
        input_name="running-example.xes",
        log_signature="xes::sample",
    )


def test_render_analysis_controls_invalidates_stale_results(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    session_state = {}
    state = get_crpm_state(session_state)
    state.config.selected_log_path = str(Path("examples") / "running-example.xes")
    state.results.analysis_complete = True
    state.results.filtered_log = [[{"concept:name": "A"}]]
    state.results.discovery_results = {"Model": object()}
    state.results.comparison_df = pd.DataFrame([{"model_name": "Model"}])
    state.results.last_analysis_signature = "stale-signature"

    monkeypatch.setattr(app_shell, "st", _dummy_streamlit(_DummySidebar(button_result=False), session_state))
    monkeypatch.setattr(app_shell, "resolve_xes_log", lambda *args, **kwargs: _loaded_log())
    monkeypatch.setattr(
        app_shell,
        "get_log_profile",
        lambda *_args, **_kwargs: {
            "stats": {"traces": 1, "events": 1, "start": datetime(2024, 1, 1), "end": datetime(2024, 1, 15)},
            "first_events": ["Start"],
        },
    )

    _render_analysis_controls(state)

    assert state.results.analysis_complete is False
    assert state.results.filtered_log is None
    assert state.results.discovery_results == {}
    assert "changed" in (state.results.config_change_message or "").lower()
    assert "click run analysis" in (state.results.config_change_message or "").lower()


def test_render_analysis_controls_failure_clears_previous_results(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    session_state = {}
    state = get_crpm_state(session_state)
    state.config.selected_log_path = str(Path("examples") / "running-example.xes")
    state.results.analysis_complete = True
    state.results.filtered_log = [[{"concept:name": "A"}]]
    state.results.discovery_results = {"Model": object()}
    state.results.comparison_df = pd.DataFrame([{"model_name": "Model"}])
    state.results.last_analysis_signature = compute_analysis_signature(
        log_signature="xes::sample",
        start_filter="All",
        date_filter_mode="case",
        start_date=None,
        end_date=None,
        selected_algorithms=state.config.selected_algorithms,
        enable_train_test=False,
        random_seed=42,
        followup_days=None,
    )

    monkeypatch.setattr(app_shell, "st", _dummy_streamlit(_DummySidebar(button_result=True), session_state))
    monkeypatch.setattr(app_shell, "resolve_xes_log", lambda *args, **kwargs: _loaded_log())
    monkeypatch.setattr(
        app_shell,
        "get_log_profile",
        lambda *_args, **_kwargs: {
            "stats": {"traces": 1, "events": 1, "start": datetime(2024, 1, 1), "end": datetime(2024, 1, 15)},
            "first_events": ["Start"],
        },
    )
    monkeypatch.setattr(app_shell, "run_discovery_comparison_pipeline", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    _render_analysis_controls(state)

    assert state.results.analysis_complete is False
    assert state.results.filtered_log is None
    assert state.results.discovery_results == {}
    assert state.results.comparison_df.empty
    assert "could not be completed" in (state.results.filter_error_message or "").lower()


def test_render_analysis_controls_shows_sidebar_messages(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    session_state = {}
    state = get_crpm_state(session_state)
    state.config.selected_log_path = str(Path("examples") / "running-example.xes")
    state.results.config_change_message = "Needs rerun"
    state.results.filter_error_message = "Run failed"
    sidebar = _DummySidebar(button_result=False)
    calls = {"warning": [], "error": []}
    sidebar.warning = lambda message, *args, **kwargs: calls["warning"].append(message)
    sidebar.error = lambda message, *args, **kwargs: calls["error"].append(message)

    monkeypatch.setattr(app_shell, "st", _dummy_streamlit(sidebar, session_state))
    monkeypatch.setattr(app_shell, "resolve_xes_log", lambda *args, **kwargs: _loaded_log())
    monkeypatch.setattr(
        app_shell,
        "get_log_profile",
        lambda *_args, **_kwargs: {
            "stats": {"traces": 1, "events": 1, "start": datetime(2024, 1, 1), "end": datetime(2024, 1, 15)},
            "first_events": ["Start"],
        },
    )

    _render_analysis_controls(state)

    assert "Needs rerun" in calls["warning"]
    assert "Run failed" in calls["error"]


def test_render_analysis_controls_places_run_button_before_data_drawer_and_log_summary(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    session_state = {}
    state = get_crpm_state(session_state)
    state.config.selected_log_path = str(Path("examples") / "running-example.xes")
    sidebar = _DummySidebar(button_result=False)

    monkeypatch.setattr(app_shell, "st", _dummy_streamlit(sidebar, session_state))
    monkeypatch.setattr(app_shell, "resolve_xes_log", lambda *args, **kwargs: _loaded_log())
    monkeypatch.setattr(
        app_shell,
        "get_log_profile",
        lambda *_args, **_kwargs: {
            "stats": {"traces": 1, "events": 1, "start": datetime(2024, 1, 1), "end": datetime(2024, 1, 15)},
            "first_events": ["Start"],
        },
    )

    _render_analysis_controls(state)

    run_index = sidebar.visible_order.index(("button", "Run analysis"))
    drawer_index = sidebar.visible_order.index(("expander", "Data & run"))
    advanced_index = sidebar.visible_order.index(("checkbox", "Advanced setup"))
    log_stats_index = sidebar.visible_order.index(("markdown", "#### Log summary"))
    assert run_index < drawer_index < advanced_index < log_stats_index


def test_render_analysis_controls_keeps_advanced_settings_inline(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    session_state = {}
    state = get_crpm_state(session_state)
    state.config.selected_log_path = str(Path("examples") / "running-example.xes")
    sidebar = _DummySidebar(
        checkbox_values={
            "crpm_show_advanced_setup": True,
            "crpm_discovery_algorithm_0": True,
            "crpm_discovery_algorithm_3": True,
        }
    )

    monkeypatch.setattr(app_shell, "st", _dummy_streamlit(sidebar, session_state))
    monkeypatch.setattr(app_shell, "resolve_xes_log", lambda *args, **kwargs: _loaded_log())
    monkeypatch.setattr(
        app_shell,
        "get_log_profile",
        lambda *_args, **_kwargs: {
            "stats": {"traces": 1, "events": 1, "start": datetime(2024, 1, 1), "end": datetime(2024, 1, 15)},
            "first_events": ["Start"],
        },
    )

    _render_analysis_controls(state)

    assert ("checkbox", "Apply date filter") in sidebar.visible_order
    assert ("checkbox", "Heuristics classic") in sidebar.visible_order
    assert ("checkbox", "Inductive IMf") in sidebar.visible_order
    assert state.config.selected_algorithms == ["Heuristics (Classic)", "Inductive (IMf)"]


def test_page_change_scroll_reset_is_only_emitted_on_page_change(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    calls: list[dict[str, object]] = []
    session_state = {"_crpm_last_rendered_page": "Overview"}
    monkeypatch.setattr(app_shell, "st", SimpleNamespace(session_state=session_state))
    monkeypatch.setattr(app_shell.components, "html", lambda html, **kwargs: calls.append({"html": html, **kwargs}))

    app_shell._reset_page_scroll_on_change("Overview")

    assert calls == []
    assert session_state["_crpm_last_rendered_page"] == "Overview"

    app_shell._reset_page_scroll_on_change("DFG Visualizations")

    assert len(calls) == 1
    assert "scrollTo" in str(calls[0]["html"])
    assert "[data-testid='stMain']" in str(calls[0]["html"])
    assert ".stMain" in str(calls[0]["html"])
    assert "section.stMain" in str(calls[0]["html"])
    assert "scrollRestoration" in str(calls[0]["html"])
    assert "[120, 360, 900, 1400, 2200, 3600]" in str(calls[0]["html"])
    assert "setInterval" in str(calls[0]["html"]) and "clearInterval" in str(calls[0]["html"])
    assert calls[0]["height"] == 0
    assert calls[0]["width"] == 0
    assert session_state["_crpm_last_rendered_page"] == "DFG Visualizations"


def test_render_header_prompts_rerun_with_note_and_toast(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    snapshot = SimpleNamespace(
        case_count=1,
        event_count=2,
        model_count=3,
        comparison_df=pd.DataFrame([{"model_name": "Model"}]),
        input_name="running-example.xes",
        active_followup_label=None,
        config_change_message="Settings changed",
        filter_error_message=None,
    )
    calls = {"notes": [], "toast": [], "captions": []}
    monkeypatch.setattr(
        app_shell,
        "st",
        SimpleNamespace(
            markdown=lambda *args, **kwargs: None,
            columns=lambda n: [SimpleNamespace(metric=lambda *args, **kwargs: None) for _ in range(n)],
            caption=lambda text, **kwargs: calls["captions"].append(text),
            error=lambda *args, **kwargs: None,
            toast=lambda text, **kwargs: calls["toast"].append(text),
        ),
    )
    monkeypatch.setattr(app_shell, "render_quiet_note", lambda text: calls["notes"].append(text))

    app_shell._render_header(snapshot, page="Overview")

    assert calls["notes"]
    assert calls["toast"]


def test_render_header_does_not_duplicate_page_cockpit_context(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    snapshot = SimpleNamespace(
        case_count=11,
        event_count=22,
        model_count=3,
        comparison_df=pd.DataFrame([{"model_name": "Model"}]),
        input_name="running-example.xes",
        active_followup_label="Full available follow-up",
        analysis_complete=True,
        config_change_message=None,
        filter_error_message=None,
    )
    calls = {"markdown": []}
    monkeypatch.setattr(
        app_shell,
        "st",
        SimpleNamespace(
            markdown=lambda text, **kwargs: calls["markdown"].append(text),
            columns=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Run context should not render global metric columns")),
            caption=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            toast=lambda *args, **kwargs: None,
        ),
    )
    monkeypatch.setattr(app_shell, "render_quiet_note", lambda text: None)

    app_shell._render_header(snapshot, page="Discovery")

    assert calls["markdown"] == []


def test_dfg_header_does_not_duplicate_page_cockpit_context(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    snapshot = SimpleNamespace(
        case_count=11,
        event_count=22,
        model_count=3,
        comparison_df=pd.DataFrame([{"model_name": "Model"}]),
        input_name="running-example.xes",
        active_followup_label="Full available follow-up",
        config_change_message=None,
        filter_error_message=None,
        analysis_complete=True,
    )
    calls = {"markdown": []}
    monkeypatch.setattr(
        app_shell,
        "st",
        SimpleNamespace(
            markdown=lambda text, **kwargs: calls["markdown"].append(text),
            columns=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("DFG header should not render metric columns")),
            caption=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            toast=lambda *args, **kwargs: None,
        ),
    )
    monkeypatch.setattr(app_shell, "render_quiet_note", lambda text: None)

    app_shell._render_header(snapshot, page="DFG Visualizations")

    assert calls["markdown"] == []


def test_render_header_skips_shell_hero_on_conformance_page(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    snapshot = SimpleNamespace(
        case_count=1,
        event_count=2,
        model_count=3,
        comparison_df=pd.DataFrame([{"model_name": "Model"}]),
        input_name="running-example.xes",
        active_followup_label=None,
        config_change_message=None,
        filter_error_message=None,
    )
    calls = {"markdown": [], "notes": [], "toast": []}
    monkeypatch.setattr(
        app_shell,
        "st",
        SimpleNamespace(
            markdown=lambda text, **kwargs: calls["markdown"].append(text),
            columns=lambda n: [SimpleNamespace(metric=lambda *args, **kwargs: None) for _ in range(n)],
            caption=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            toast=lambda text, **kwargs: calls["toast"].append(text),
        ),
    )
    monkeypatch.setattr(app_shell, "render_quiet_note", lambda text: calls["notes"].append(text))

    app_shell._render_header(snapshot, page="Conformance Analytics")

    assert calls["markdown"] == []
    assert calls["notes"] == []
    assert calls["toast"] == []


def test_render_header_brand_includes_author_site_badge(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    calls = {"markdown": []}
    monkeypatch.setattr(app_shell, "st", SimpleNamespace(markdown=lambda text, **kwargs: calls["markdown"].append(text)))

    app_shell._render_header_brand()

    rendered = " ".join(calls["markdown"])
    assert "crpm-header-badges" in rendered
    assert 'data-qa="global-brand-strip"' in rendered
    assert 'aria-label="CRPM institutional links"' in rendered
    assert "crpm-author-badge" in rendered
    assert "crpm-build-badge" in rendered
    assert f"Build {app_shell.__version__}" in rendered
    assert "crpm-fmup-badge" in rendered
    assert "hfmonteiro.com" in rendered
    assert app_shell.FMUP_HOME_URL in rendered
    assert app_shell.UP_HOME_URL in rendered
    assert 'rel="noopener noreferrer"' in rendered
    assert "data:image/svg+xml;base64" in rendered


def test_render_footer_is_single_compact_provenance_signature(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    calls = {"markdown": []}
    monkeypatch.setattr(
        app_shell,
        "st",
        SimpleNamespace(sidebar=SimpleNamespace(markdown=lambda text, **kwargs: calls["markdown"].append(text))),
    )

    app_shell._render_footer()

    rendered = " ".join(calls["markdown"])
    assert rendered.count('data-crpm-footer="sidebar"') == 1
    assert "crpm-sidebar-provenance" in rendered
    assert "PhD work" in rendered
    assert app_shell.AUTHOR_WEBSITE in rendered
    assert "crpm-footer__logo" not in rendered
    assert app_shell.FMUP_BADGE_SRC not in rendered
