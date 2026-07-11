from __future__ import annotations

import pandas as pd

from crpm.pages.common import render_html_ranked_table


def test_render_html_ranked_table_has_caption_and_scoped_headers(monkeypatch) -> None:
    import crpm.pages.common as common

    rendered: list[str] = []
    monkeypatch.setattr(common.st, "markdown", lambda value, **_kwargs: rendered.append(value))
    dataframe = pd.DataFrame({"Activity": ["Invitation"], "Cases": [12]})

    render_html_ranked_table(dataframe, title="Most frequent activities", label_column="Activity")

    assert len(rendered) == 1
    assert "<caption>Most frequent activities</caption>" in rendered[0]
    assert "<th scope='col'>Activity</th>" in rendered[0]
    assert "<th scope='col'>Cases</th>" in rendered[0]


def test_render_html_ranked_table_uses_internal_scroll_for_wide_dataframes(monkeypatch) -> None:
    import crpm.pages.common as common

    rendered: list[str] = []
    monkeypatch.setattr(common.st, "markdown", lambda value, **_kwargs: rendered.append(value))
    dataframe = pd.DataFrame([{f"Column {index}": index for index in range(8)}])

    render_html_ranked_table(dataframe, title="Wide table", label_column="Column 0")

    assert "crpm-ranked-table--wide" in rendered[0]
    assert "min-width:58.00rem;table-layout:auto" in rendered[0]


def test_render_html_ranked_table_treats_six_columns_as_wide(monkeypatch) -> None:
    import crpm.pages.common as common

    rendered: list[str] = []
    monkeypatch.setattr(common.st, "markdown", lambda value, **_kwargs: rendered.append(value))
    dataframe = pd.DataFrame([{f"Column {index}": index for index in range(6)}])

    render_html_ranked_table(dataframe, title="Operational detail", label_column="Column 1")

    assert "crpm-ranked-table--wide" in rendered[0]
    assert "min-width:52.00rem;table-layout:auto" in rendered[0]
