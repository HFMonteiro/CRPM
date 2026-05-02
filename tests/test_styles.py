from crpm.styles import get_custom_css


def test_alert_descendant_text_inherits_readable_colors() -> None:
    css = get_custom_css()
    assert ".stInfo div, .stInfo p, .stInfo span, .stInfo label, .stInfo li" in css
    assert ".stWarning div, .stWarning p, .stWarning span, .stWarning label, .stWarning li" in css
    assert ".stError div, .stError p, .stError span, .stError label, .stError li" in css
    assert '.stAlert [data-testid="stMarkdownContainer"]' in css


def test_widget_labels_have_explicit_contrast_rules() -> None:
    css = get_custom_css()
    assert '[data-testid="stWidgetLabel"] p' in css
    assert '[data-testid="stRadio"] label' in css
    assert '[data-testid="stCheckbox"] label' in css
    assert '[data-testid="stSlider"] [data-testid="stWidgetLabel"] p' in css


def test_sidebar_alerts_have_explicit_readable_contrast_rules() -> None:
    css = get_custom_css()
    assert '[data-testid="stSidebar"] .stWarning' in css
    assert '[data-testid="stSidebar"] .stWarning [data-testid="stMarkdownContainer"] p' in css
    assert '[data-testid="stSidebar"] .stInfo' in css
    assert '[data-testid="stSidebar"] .stInfo [data-testid="stMarkdownContainer"] p' in css


def test_conformance_note_and_workflow_board_styles_exist() -> None:
    css = get_custom_css()
    assert ".crpm-note" in css
    assert ".crpm-workflow-board" in css
    assert ".crpm-workflow-board svg" in css
    assert "width: 100%;" in css
    assert "height: auto;" in css
    assert ".crpm-empty-state" in css
    assert ".crpm-inline-empty" in css
    assert ".crpm-conformance-hero" in css
    assert ".crpm-conformance-stage-header" in css
    assert ".crpm-conformance-report-band" in css
    assert ".crpm-conformance-evidence-band" in css


def test_primary_button_and_inspector_styles_exist() -> None:
    css = get_custom_css()
    assert '.stButton button[kind="primary"]:focus' in css
    assert '[data-testid="stBaseButton-primary"] *' in css
    assert ".crpm-selection-card" in css
    assert ".crpm-detail-card" in css
    assert ".crpm-model-card-grid" in css
    assert ".crpm-ranked-table" in css
    assert ".crpm-rank-pill" in css
    assert ".crpm-table__metric-track" in css
    assert ".crpm-chip--conformant" in css


def test_conformance_compact_shell_styles_exist() -> None:
    css = get_custom_css()
    assert ".crpm-conformance-kpi-strip" in css
    assert ".crpm-conformance-kpi-strip--rail" in css
    assert "max-height: 360px;" in css
    assert ".crpm-workflow-board--horizontal" in css


def test_overview_and_bi_card_styles_exist() -> None:
    css = get_custom_css()
    assert ".crpm-dashboard-topbar" in css
    assert ".crpm-dashboard-bar-list" in css
    assert ".crpm-dashboard-card-stack" in css
    assert ".crpm-dashboard-section-title" in css
    assert ".crpm-overview-command-center" in css
    assert ".crpm-overview-map-frame" in css
    assert ".crpm-bi-card-grid" in css
    assert ".crpm-page-card-grid" in css
    assert ".crpm-reading-order-band" in css
    assert ".crpm-shell-hero--compact" in css
    assert ".crpm-shell-hero__meta" in css
    assert ".crpm-chip--watch" in css
    assert ".crpm-chip--deviation-heavy" in css
    assert ".crpm-header-badges" in css
    assert ".crpm-fmup-badge" in css


def test_dashboard_header_avoids_cockpit_clipping() -> None:
    css = get_custom_css()
    assert '[data-testid="stHeader"]' in css
    assert "position: relative !important;" in css
    assert "scroll-padding-top: 4.25rem;" in css
    assert ".crpm-dashboard-map-toolbar" in css
    assert "scroll-margin-top: 4.25rem;" in css
    assert "@media (max-width: 1180px)" in css
