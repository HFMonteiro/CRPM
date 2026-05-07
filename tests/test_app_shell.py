from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from crpm.app_runtime import LoadedLog, compute_analysis_signature
from crpm.app_shell import _render_analysis_controls
from crpm.app_state import get_crpm_state


class _DummySidebar:
    def __init__(self, *, button_result: bool = False) -> None:
        self.button_result = button_result
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
        return value

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
        return _DummyContext()

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
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def caption(self, *args, **kwargs):
        return None


def _dummy_streamlit(sidebar: _DummySidebar, session_state: dict) -> SimpleNamespace:
    return SimpleNamespace(
        sidebar=sidebar,
        session_state=session_state,
        caption=lambda *args, **kwargs: None,
        text_input=sidebar.text_input,
        checkbox=sidebar.checkbox,
        selectbox=sidebar.selectbox,
        date_input=sidebar.date_input,
        multiselect=sidebar.multiselect,
        number_input=sidebar.number_input,
    )


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
        "compute_log_stats",
        lambda *_args, **_kwargs: {"traces": 1, "events": 1, "start": datetime(2024, 1, 1), "end": datetime(2024, 1, 15)},
    )
    monkeypatch.setattr(app_shell, "first_event_names", lambda *_args, **_kwargs: ["Start"])

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
        "compute_log_stats",
        lambda *_args, **_kwargs: {"traces": 1, "events": 1, "start": datetime(2024, 1, 1), "end": datetime(2024, 1, 15)},
    )
    monkeypatch.setattr(app_shell, "first_event_names", lambda *_args, **_kwargs: ["Start"])
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
        "compute_log_stats",
        lambda *_args, **_kwargs: {"traces": 1, "events": 1, "start": datetime(2024, 1, 1), "end": datetime(2024, 1, 15)},
    )
    monkeypatch.setattr(app_shell, "first_event_names", lambda *_args, **_kwargs: ["Start"])

    _render_analysis_controls(state)

    assert "Needs rerun" in calls["warning"]
    assert "Run failed" in calls["error"]


def test_render_analysis_controls_places_run_button_before_advanced_and_log_stats(monkeypatch) -> None:
    import crpm.app_shell as app_shell

    session_state = {}
    state = get_crpm_state(session_state)
    state.config.selected_log_path = str(Path("examples") / "running-example.xes")
    sidebar = _DummySidebar(button_result=False)

    monkeypatch.setattr(app_shell, "st", _dummy_streamlit(sidebar, session_state))
    monkeypatch.setattr(app_shell, "resolve_xes_log", lambda *args, **kwargs: _loaded_log())
    monkeypatch.setattr(
        app_shell,
        "compute_log_stats",
        lambda *_args, **_kwargs: {"traces": 1, "events": 1, "start": datetime(2024, 1, 1), "end": datetime(2024, 1, 15)},
    )
    monkeypatch.setattr(app_shell, "first_event_names", lambda *_args, **_kwargs: ["Start"])

    _render_analysis_controls(state)

    run_index = sidebar.visible_order.index(("button", "Run analysis"))
    advanced_index = sidebar.visible_order.index(("expander", "Advanced setup"))
    log_stats_index = sidebar.visible_order.index(("markdown", "### Log Statistics"))
    assert run_index < advanced_index < log_stats_index


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


def test_render_header_renders_compact_shell_intro_for_non_conformance_pages(monkeypatch) -> None:
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
    )
    calls = {"markdown": [], "metrics": []}
    monkeypatch.setattr(
        app_shell,
        "st",
        SimpleNamespace(
            markdown=lambda text, **kwargs: calls["markdown"].append(text),
            columns=lambda n: [SimpleNamespace(metric=lambda *args, **kwargs: calls["metrics"].append(args)) for _ in range(n)],
            caption=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            toast=lambda *args, **kwargs: None,
        ),
    )
    monkeypatch.setattr(app_shell, "render_quiet_note", lambda text: None)

    app_shell._render_header(snapshot, page="Discovery")

    rendered = " ".join(calls["markdown"])
    assert "crpm-shell-hero--compact" in rendered
    assert "Current run context" in rendered
    assert "Screening Program Process Mining Workbench" not in rendered
    assert "running-example.xes" in rendered
    assert len(calls["metrics"]) == 2


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
    assert "crpm-author-badge" in rendered
    assert "crpm-fmup-badge" in rendered
    assert "hfmonteiro.com" in rendered
    assert app_shell.FMUP_HOME_URL in rendered
    assert app_shell.UP_HOME_URL in rendered
    assert 'rel="noopener noreferrer"' in rendered
    assert "data:image/svg+xml;base64" in rendered
